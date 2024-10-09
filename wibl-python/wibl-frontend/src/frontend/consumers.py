# WebSocket consumers for real-time delivery of data
import json

from channels.generic.websocket import AsyncWebsocketConsumer

class WiblFileConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get user session
        self.session_key = self.scope['session'].session_key
        print(f"WiblFileConsumer.connect: session_key: {self.session_key}")
        await self.channel_layer.group_add(self.session_key, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.session_key, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        await self.send(text_data=json.dumps({
            'message': message
        }))

    # Receive message from celery task?
    async def wibl_message(self, event):
        print("wibl_message called...")
        message = event["message"]
        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
