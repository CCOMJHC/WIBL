import time

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@shared_task(name='get-wibl-files')
def get_wibl_files():
    print("get_wibl_files called!")
    time.sleep(2)
    # TODO: Make call to WIBL manager
    wibl_files_data = {
        'files': [
            {
                'filename': 'DA0F544F-EB54-45C4-9318-A5AEE23C23F0.wibl',
                'size': 5.4, 'observations': 10232, 'logger': 'UNHJHC-wibl-1',
                'startTime': '2023-01-23T13:45:08.231', 'status': 1,
                'messages': 'wibl file test message 1'
            }
        ]
    }
    channel_layer = get_channel_layer()
    print("sending to websocket...")
    async_to_sync(channel_layer.group_send)(
        'wibl',
        {
            'type': 'wibl_message',
            'message': wibl_files_data
        }
    )
