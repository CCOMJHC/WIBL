from http.client import HTTPResponse

from celery.bin.base import JSON_ARRAY
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpRequest, StreamingHttpResponse, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.cache import cache_control

from wiblfe.celery import app as celery

import httpx
import os

@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
async def downloadFile(request, fileid):
    manager_url: str = os.environ.get('MANAGEMENT_URL', "http://manager:5000")
    extension = fileid.split(".")[-1]

    if extension == "wibl":
        full_url = f"{manager_url}/wibl/download/{fileid}"
    else:
        full_url = f"{manager_url}/geojson/download/{fileid}"
    print(f"{full_url}")
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream('GET', full_url) as response:
                async def return_error():
                    error_body = await response.aread()
                    return JsonResponse(
                        {"error": f"Manager Error, {response.status_code}: {error_body.decode()}"},
                        status=response.status_code
                    )

                # Create an async iterable function
                async def create_stream():
                        async for chunk in response.aiter_bytes():
                            yield chunk

                # If there is an error, return the json
                if response.status_code >= 400:
                    return await return_error()

                # Stream the function to the user
                return StreamingHttpResponse(create_stream(),
                                             content_type='application/octet-stream',
                                             headers={"Content-Disposition": f'attachment; filename="{fileid}"'})

    except Exception as e:
        # TODO: Create consistent frontend error logging
        return JsonResponse({'error': str(e)}, status=500)

@login_required
async def saveGeojsonFile(request, fileid):
    manager_url: str = os.environ.get('MANAGEMENT_URL', "http://manager:5000")
    full_url = f"{manager_url}/geojson/save/{fileid}"

    client = httpx.AsyncClient()
    response = await client.get(full_url)
    if response.status_code == 200:
        return JsonResponse({'geojson': response.json()}, status=200)
    else:
        return JsonResponse({}, status=404)


async def saveGeojsonFile(request, fileid):
    manager_url: str = os.environ.get('MANAGEMENT_URL', "http://manager:5000")
    full_url = f"{manager_url}/geojson/save/{fileid}"

    client = httpx.AsyncClient()
    response = await client.get(full_url)
    if response.status_code == 200:
        return JsonResponse({'geojson': response.json()})
    else:
        return {'error': 'Failed to get geojson'}


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
