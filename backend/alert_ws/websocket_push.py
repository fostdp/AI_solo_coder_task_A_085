import datetime
import json
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class WebSocketPush:

    def __init__(self):
        self.channel_layer = None

    def _get_channel_layer(self):
        if self.channel_layer is None:
            try:
                self.channel_layer = get_channel_layer()
            except Exception as e:
                logger.warning(f"获取Channel Layer失败: {e}")
        return self.channel_layer

    def broadcast_alert(self, alert_data: dict) -> bool:
        channel_layer = self._get_channel_layer()
        if not channel_layer:
            logger.warning("Channel Layer不可用，跳过WebSocket告警")
            return False

        try:
            alert_copy = dict(alert_data)
            if '_id' in alert_copy:
                alert_copy['_id'] = str(alert_copy['_id'])

            if 'timestamp' in alert_copy and isinstance(alert_copy['timestamp'], datetime.datetime):
                alert_copy['timestamp'] = alert_copy['timestamp'].isoformat()

            async_to_sync(channel_layer.group_send)(
                'alerts',
                {
                    'type': 'send_alert',
                    'data': alert_copy
                }
            )

            logger.info(f"WebSocket告警广播成功: {alert_data.get('artifact_id')}")
            return True

        except Exception as e:
            logger.error(f"WebSocket告警广播失败: {e}")
            return False

    def send_spectrum_update(self, artifact_id: str, spectrum_data: dict) -> bool:
        channel_layer = self._get_channel_layer()
        if not channel_layer:
            return False

        try:
            spec_copy = dict(spectrum_data)
            if '_id' in spec_copy:
                spec_copy['_id'] = str(spec_copy['_id'])

            if 'timestamp' in spec_copy and isinstance(spec_copy['timestamp'], datetime.datetime):
                spec_copy['timestamp'] = spec_copy['timestamp'].isoformat()

            group_name = f'spectrum_{artifact_id}'

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'send_spectrum',
                    'data': spec_copy
                }
            )

            return True

        except Exception as e:
            logger.error(f"WebSocket光谱更新失败: {e}")
            return False

    def broadcast_stats_update(self, stats_data: dict) -> bool:
        channel_layer = self._get_channel_layer()
        if not channel_layer:
            return False

        try:
            async_to_sync(channel_layer.group_send)(
                'alerts',
                {
                    'type': 'send_alert',
                    'data': {
                        'type': 'stats_update',
                        'stats': stats_data
                    }
                }
            )

            return True

        except Exception as e:
            logger.error(f"WebSocket统计更新失败: {e}")
            return False
