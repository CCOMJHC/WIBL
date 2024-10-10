import os
import time
import uuid

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import requests

@shared_task(name='get-wibl-files')
def get_wibl_files(session_key: str):
    print("get_wibl_files called!")
    time.sleep(2)

    wibl_files = []
    wibl_files_data = {'files': wibl_files}

    # TODO: Make call to WIBL manager
    manager_url: str = os.environ.get('MANAGEMENT_URL', 'http://manager:5000')
    wibl_url: str = f"{manager_url}/wibl/all"
    response = requests.get(wibl_url)
    if response.status_code != 200:
        # TODO: Setup logging and log this
        return False
    # TODO: Try...except
    wf_json = response.json()
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
    channel_layer = get_channel_layer()
    print("sending to websocket...")
    async_to_sync(channel_layer.group_send)(
        session_key,
        {
            'type': 'wibl_message',
            'message': wibl_files_data
        }
    )
