from http.client import HTTPResponse

from celery.bin.base import JSON_ARRAY
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpRequest, StreamingHttpResponse, HttpResponse, JsonResponse
from django.urls import reverse

from wiblfe.celery import app as celery

import os
import requests

@login_required
def downloadView(request: HttpRequest, fileid):
    download_url = request.build_absolute_uri(reverse('downloadWiblFile', args=[fileid]))
    return JsonResponse({'download_url': download_url})

@login_required
def downloadWiblFile(request, fileid):
    manager_url: str = os.environ.get('MANAGEMENT_URL', "http://manager:5000")
    full_url = f"{manager_url}/wibl/download/{fileid}"
    with requests.get(full_url, stream=True) as response:
        response_stream = StreamingHttpResponse(response.iter_content(1024),
                                                content_type='application/octet-stream')
        response_stream['Content-Disposition'] = f'attachment; filename="{fileid}"'
        return response_stream

@login_required
def index(request: HttpRequest):
    print(f"session key: {request.session.session_key}")
    # Note: We don't need to call this task here as the client will ask for data it needs
    # via the websocket, but this is how we would call a long-running task that sends data
    # back to the client via the websocket...
    # celery.send_task('get-wibl-files', (request.session.session_key,))
    context = {
        'wsURL': f"ws://{request.get_host()}/ws/"
    }
    return render(request, 'frontend/index.html', context)

@login_required
def logout(request: HttpRequest):
    logout(request)
