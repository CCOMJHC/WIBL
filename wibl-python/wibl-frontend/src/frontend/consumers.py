# WebSocket consumers for real-time delivery of data
import os
import json

from channels.generic.websocket import AsyncWebsocketConsumer

import httpx



class WiblFileConsumer(AsyncWebsocketConsumer):
    async def send_list_wibl_files(self):
        print("send_list_wibl_files called!")

        wibl_files = []
        wibl_files_data = {'files': wibl_files}

        # Make call to WIBL manager
        manager_url: str = os.environ.get('MANAGEMENT_URL', 'http://manager:5000')
        wibl_url: str = f"{manager_url}/wibl/all"
        async with httpx.AsyncClient() as client:
            response = await client.get(wibl_url)
        if response.status_code != 200:
            # TODO: Properly handle error and log
            mesg = f"Received status code {response.status_code} when querying manager."
            print(mesg)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': mesg
            }))

        # TODO: Try...except
        wf_json = response.json()

        print(f"Got response from manager: {wf_json}")

        for wf in wf_json:
            wibl_files.append({
                "fileid": wf['fileid'],
                "processtime": wf['processtime'],
                # TODO: Fill in other fields
                # "updatetime": "2024-10-10T19:55:53.748479+00:00",
                # "notifytime": "Unknown",
                # "logger": "UNHJHC-wibl-1",
                # "platform": "USCGC Healy",
                # "size": 1.0,
                # "observations": 100232,
                # "soundings": 8023,
                # "starttime": "2023-01-23T12:34:45.142",
                # "endtime": "2023-01-24T01:45:23.012",
                # "status": 0,
                # "messages": ""
            })
        print("sending to websocket...")
        await self.send(text_data=json.dumps({
            'type': 'wibl',
            'event': 'list-wibl-files',
            'message': wibl_files_data
        }))

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
        message = json.loads(text_data)

        print(f"WiblFileConsumer.receive: Got message: {message}")

        if 'type' not in message:
            # TODO: Properly handle error
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f"Missing type indicator in message: {message}"
            }))
            return

        match message['type']:
            case 'list-wibl-files':
                print(f"WiblFileConsumer.receive: calling send_list_wibl_files()...")
                await self.send_list_wibl_files()
            case _:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f"Unknown type '{message['type']}' in message: {message}"
                }))

    # Receive message from celery task?
    async def wibl_message(self, event):
        print("wibl_message called...")
        message = event["message"]
        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
