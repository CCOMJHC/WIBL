# WebSocket consumers for real-time delivery of data
import os
import json
from abc import ABC, abstractmethod
from channels.generic.websocket import AsyncWebsocketConsumer
import httpx



class FileConsumer(ABC, AsyncWebsocketConsumer):
    """
        Abstract class for file consumer
        Created to reuse code.

    """
    async def connect(self):
        # Get user session
        self.session_key = self.scope['session'].session_key
        print(f"{self.channel_name}.connect: session_key: {self.session_key}")
        await self.channel_layer.group_add(self.session_key, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.session_key, self.channel_name)

    # Implements the AsyncWebsocketConsumer's method, while making it abstract
    @abstractmethod
    async def receive(self, text_data, **kwargs):
        pass

    async def send_message(self, event):
        print("send_message called...")
        message = event["message"]
        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))

class WiblFileDetailConsumer(FileConsumer):
    async def send_wibl_details(self, file_id: str):
        HEADERS = ["fileid", "processtime", "updatetime", "notifytime", "logger", "platform", "size"
            , "observations", "soundings", "starttime", "endtime", "status", "messages"]
        print("send_wibl_details called")
        wibl_file_data = {"fileid": "",
                          "processtime": "",
                          "updatetime": "",
                          "notifytime": "",
                          "logger": "",
                          "platform": "",
                          "size": "",
                          "observations": "",
                          "soundings": "",
                          "starttime": "",
                          "endtime": "",
                          "status": "",
                          "messages": ""}

        # Make call to WIBL manager
        manager_url: str = os.environ.get('MANAGEMENT_URL', "http://manager:5000")
        wibl_url: str = f"{manager_url}/wibl/{file_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(wibl_url)
        if response.status_code != 200:
            mesg = f"Received status code {response.status_code} when querying manager."
            print(mesg)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': mesg
            }))

        wf_json = response.json()

        print(f"Got response from manager: {wf_json}")
        for heading in HEADERS:
            wibl_file_data[heading] = wf_json[heading]

        print("sending to websocket...")
        await self.send(text_data=json.dumps({
            'type': 'wibl',
            'event': 'list-wibl-details',
            'message': wibl_file_data
        }))

    # Receive message from WebSocket
    async def receive(self, text_data, **kwargs):
        message = json.loads(text_data)

        print(f"WiblFileDetailConsumer.receive: Got message: {message}")

        if 'type' not in message:
            # TODO: Properly handle error
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f"Missing type indicator in message: {message}"
            }))
            return

        match message['type']:
            case 'list-wibl-details':
                print(f"WiblFileDetailConsumer.receive: calling send_wibl_details()...")
                await self.send_wibl_details(message['file_id'])
            case _:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f"Unknown type '{message['type']}' in message: {message}"
                }))

class WiblFileConsumer(FileConsumer):

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
                "updatetime": wf['updatetime'],
                "notifytime": wf['notifytime'],
                "logger": wf['logger'],
                "platform": wf['platform'],
                "size": wf['size'],
                "observations": wf['observations'],
                "soundings": wf['soundings'],
                "starttime": wf['starttime'],
                "endtime": wf['endtime'],
                "status": wf['status'],
                "messages": wf['messages']
            })
        print("sending to websocket...")
        await self.send(text_data=json.dumps({
            'type': 'wibl',
            'event': 'list-wibl-files',
            'message': wibl_files_data
        }))

    async def delete_wibl_files(self, file_ids):
        print("delete_wibl_files called!")

        manager_url: str = os.environ.get('MANAGEMENT_URL', 'http://manager:5000')
        successful_deletes = []

        for file_id in file_ids:
            print(file_id)
            wibl_url: str = f"{manager_url}/wibl/{file_id}"
            async with httpx.AsyncClient() as client:
                response = await client.delete(wibl_url)
            if response.status_code != 200:
                mesg = f"Received status code {response.status_code} when querying manager."
                print(mesg)
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': mesg
                }))
            else:
                print(f"Successfully deleted {file_id}")
                successful_deletes.append(file_id)

        await self.send(text_data=json.dumps({
            'type': 'wibl',
            'event': 'delete-wibl-files',
            'message': successful_deletes
        }))

    # Receive message from WebSocket
    async def receive(self, text_data, **kwargs):
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
            case 'delete-wibl-files':
                print(f"WiblFileDetailConsumer.receive: calling deleter_wibl_files()...")
                await self.delete_wibl_files(message['file_ids'])
            case _:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f"Unknown type '{message['type']}' in message: {message}"
                }))
