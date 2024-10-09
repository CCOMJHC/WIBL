# WebSocket consumers for real-time delivery of data
import json

from channels.generic.websocket import AsyncWebsocketConsumer

class WiblFileConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("wibl", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("wibl", self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        await self.channel_layer.group_send(
            "wibl", {"type": "wibl_message", "message": message}
        )

    # Receive message from celery task?
    async def wibl_message(self, event):
        message = event["message"]
        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
