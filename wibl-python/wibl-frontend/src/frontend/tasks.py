import time
import uuid

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@shared_task(name='get-wibl-files')
def get_wibl_files(session_key: str):
    print("get_wibl_files called!")
    time.sleep(2)
    # TODO: Make call to WIBL manager
    wibl_files_data = {
        'files': [
            {
                'filename': f"{str(uuid.uuid4())}.wibl",
                'size': 5.4, 'observations': 10232, 'logger': 'UNHJHC-wibl-1',
                'startTime': '2023-01-23T13:45:08.231', 'status': 1,
                'messages': 'wibl file test message 1'
            }
        ]
    }
    channel_layer = get_channel_layer()
    print("sending to websocket...")
    async_to_sync(channel_layer.group_send)(
        session_key,
        {
            'type': 'wibl_message',
            'message': wibl_files_data
        }
    )
