import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import logging
import time
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


class ReconnectingConsumerMixin:

    PING_INTERVAL = getattr(settings, 'WEBSOCKET_PING_INTERVAL', 30)
    PONG_TIMEOUT = getattr(settings, 'WEBSOCKET_PONG_TIMEOUT', 10)
    MAX_PENDING_ALERTS = getattr(settings, 'WEBSOCKET_MAX_PENDING_ALERTS', 500)
    PENDING_TTL_SECONDS = getattr(settings, 'WEBSOCKET_PENDING_TTL', 3600)

    _pending_sessions = {}

    async def _cleanup_expired_sessions(self):
        now = time.time()
        expired = [
            cid for cid, sess in self._pending_sessions.items()
            if now - sess['last_seen'] > self.PENDING_TTL_SECONDS
        ]
        for cid in expired:
            del self._pending_sessions[cid]

    def _track_session(self, client_id: str):
        if client_id not in self._pending_sessions:
            self._pending_sessions[client_id] = {
                'alerts': [],
                'last_seen': time.time(),
                'reconnect_count': 0
            }
        self._pending_sessions[client_id]['last_seen'] = time.time()
        return self._pending_sessions[client_id]

    def _queue_pending_alert(self, client_id: str, alert_data: dict):
        if client_id in self._pending_sessions:
            sess = self._pending_sessions[client_id]
            sess['alerts'].append({
                'data': alert_data,
                'queued_at': time.time()
            })
            if len(sess['alerts']) > self.MAX_PENDING_ALERTS:
                sess['alerts'] = sess['alerts'][-self.MAX_PENDING_ALERTS:]

    def _drain_pending_alerts(self, client_id: str):
        if client_id in self._pending_sessions:
            sess = self._pending_sessions[client_id]
            sess['reconnect_count'] += 1
            alerts = sess['alerts'][:]
            sess['alerts'] = []
            return alerts
        return []


class AlertConsumer(AsyncWebsocketConsumer, ReconnectingConsumerMixin):
    async def connect(self):
        query_string = self.scope.get('query_string', b'').decode()
        self.client_id = None
        for kv in query_string.split('&'):
            if kv.startswith('client_id='):
                self.client_id = kv.split('=', 1)[1]
                break

        if not self.client_id:
            import uuid
            self.client_id = 'ws_' + uuid.uuid4().hex[:12]

        self.room_group_name = 'alerts'
        self.pong_received = True
        self.ping_task = None
        self.is_connected = False

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        sess = self._track_session(self.client_id)

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'data': {
                'client_id': self.client_id,
                'server_time': datetime.now().isoformat(),
                'reconnect_count': sess['reconnect_count'],
                'pending_alerts_count': len(sess['alerts'])
            }
        }))

        pending = self._drain_pending_alerts(self.client_id)
        for alert in pending:
            try:
                await self.send(text_data=json.dumps({
                    'type': 'alert',
                    'data': alert['data'],
                    'pending': True,
                    'queued_at': datetime.fromtimestamp(alert['queued_at']).isoformat()
                }))
            except Exception as e:
                logger.warning(f"发送暂存告警失败: {e}")

        self.is_connected = True

        self.ping_task = asyncio.create_task(self._heartbeat_loop())

    async def disconnect(self, close_code):
        self.is_connected = False
        if self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        if hasattr(self, 'client_id'):
            sess = self._pending_sessions.get(self.client_id)
            if sess and len(sess['alerts']) == 0:
                pass

    async def _heartbeat_loop(self):
        while self.is_connected:
            try:
                await self.send(text_data=json.dumps({
                    'type': 'ping',
                    'data': {'timestamp': time.time()}
                }))
                self.pong_received = False

                await asyncio.sleep(self.PONG_TIMEOUT)
                if not self.pong_received:
                    logger.warning(
                        f"客户端 {self.client_id} 心跳超时 ({self.PONG_TIMEOUT}s)，可能断线"
                    )
                    if self.client_id in self._pending_sessions:
                        self._pending_sessions[self.client_id]['last_seen'] = time.time()

                await asyncio.sleep(self.PING_INTERVAL - self.PONG_TIMEOUT)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳任务异常: {e}")
                await asyncio.sleep(5)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')

            if msg_type == 'pong':
                self.pong_received = True
                if hasattr(self, 'client_id'):
                    self._track_session(self.client_id)
                return

            if msg_type == 'reconnect_request':
                old_client_id = data.get('old_client_id')
                if old_client_id and old_client_id in self._pending_sessions:
                    if old_client_id != self.client_id:
                        pending = self._drain_pending_alerts(old_client_id)
                        for alert in pending:
                            self._queue_pending_alert(self.client_id, alert['data'])
                        del self._pending_sessions[old_client_id]
                return

        except json.JSONDecodeError:
            logger.warning(f"无效的 WebSocket 消息: {text_data[:100]}")

    async def send_alert(self, event):
        alert_data = event['data']

        if not self.is_connected or not self.pong_received:
            if hasattr(self, 'client_id'):
                self._queue_pending_alert(self.client_id, alert_data)
            return

        try:
            await self.send(text_data=json.dumps({
                'type': 'alert',
                'data': alert_data
            }))
        except Exception as e:
            logger.warning(f"WebSocket 发送告警失败，暂存: {e}")
            if hasattr(self, 'client_id'):
                self._queue_pending_alert(self.client_id, alert_data)


class SpectrumConsumer(AsyncWebsocketConsumer, ReconnectingConsumerMixin):
    async def connect(self):
        self.artifact_id = self.scope['url_route']['kwargs']['artifact_id']

        query_string = self.scope.get('query_string', b'').decode()
        self.client_id = None
        for kv in query_string.split('&'):
            if kv.startswith('client_id='):
                self.client_id = kv.split('=', 1)[1]
                break
        if not self.client_id:
            import uuid
            self.client_id = 'spec_' + uuid.uuid4().hex[:12]

        self.room_group_name = f'spectrum_{self.artifact_id}'
        self.pong_received = True
        self.ping_task = None
        self.is_connected = False

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        sess = self._track_session(self.client_id)

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'data': {
                'artifact_id': self.artifact_id,
                'client_id': self.client_id,
                'server_time': datetime.now().isoformat(),
                'reconnect_count': sess['reconnect_count']
            }
        }))

        self.is_connected = True
        self.ping_task = asyncio.create_task(self._heartbeat_loop())

    async def disconnect(self, close_code):
        self.is_connected = False
        if self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def _heartbeat_loop(self):
        while self.is_connected:
            try:
                await self.send(text_data=json.dumps({
                    'type': 'ping',
                    'data': {'timestamp': time.time()}
                }))
                self.pong_received = False
                await asyncio.sleep(self.PONG_TIMEOUT)
                if not self.pong_received:
                    logger.warning(
                        f"光谱客户端 {self.client_id} 心跳超时"
                    )
                await asyncio.sleep(self.PING_INTERVAL - self.PONG_TIMEOUT)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"光谱心跳异常: {e}")
                await asyncio.sleep(5)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'pong':
                self.pong_received = True
                if hasattr(self, 'client_id'):
                    self._track_session(self.client_id)
        except json.JSONDecodeError:
            pass

    async def send_spectrum(self, event):
        spectrum_data = event['data']

        if not self.is_connected or not self.pong_received:
            return

        try:
            await self.send(text_data=json.dumps({
                'type': 'spectrum_update',
                'data': spectrum_data
            }))
        except Exception as e:
            logger.warning(f"WebSocket 光谱更新失败: {e}")
