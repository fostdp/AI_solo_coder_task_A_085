import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import asyncio


class AlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'alerts'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        pass
    
    async def send_alert(self, event):
        alert_data = event['data']
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'data': alert_data
        }))


class SpectrumConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.artifact_id = self.scope['url_route']['kwargs']['artifact_id']
        self.room_group_name = f'spectrum_{self.artifact_id}'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        pass
    
    async def send_spectrum(self, event):
        spectrum_data = event['data']
        await self.send(text_data=json.dumps({
            'type': 'spectrum_update',
            'data': spectrum_data
        }))
