from http.client import HTTPResponse

from celery.bin.base import JSON_ARRAY
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpRequest, StreamingHttpResponse, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.core.cache import cache
from django.conf import settings
import httpx
from os import environ
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

MAP_NAME = environ['MAP_NAME']
REGION = environ['AWS_REGION']

_ws_scheme: str | None = None
def get_ws_scheme() -> str:
    global _ws_scheme
    if _ws_scheme is None:
        _ws_scheme = settings.WEB_SOCKET_SCHEME
    return _ws_scheme

@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
async def downloadFile(request, fileid):
    manager_url: str = environ.get('MANAGEMENT_URL', "http://manager:5000")
    extension = fileid.split(".")[-1]

    download_url = f"{manager_url}/{extension}/download/{fileid}"
    print(f"{download_url}")

    try:
        # Create an async iterable function
        async def create_stream():
            client = httpx.AsyncClient()
            async with client.stream('GET', download_url) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

        # Stream the function to the user
        return StreamingHttpResponse(create_stream(),
                                     content_type='application/octet-stream',
                                     headers={"Content-Disposition": f'attachment; filename="{fileid}"'})
    except Exception as e:
        # TODO: Create consistent frontend error logging
        return JsonResponse({'error': str(e)}, status=500)

@login_required
async def rawGeojsonFile(request, fileid):
    manager_url: str = environ.get('MANAGEMENT_URL', "http://manager:5000")
    full_url = f"{manager_url}/geojson/raw/{fileid}"

    client = httpx.AsyncClient()
    response = await client.get(full_url)
    if response.status_code == 200:
        return JsonResponse({'geojson': response.json()}, status=200)
    else:
        return JsonResponse({}, status=404)

@login_required
async def checkFileAvail(request, fileid):
    manager_url: str = environ.get('MANAGEMENT_URL', "http://manager:5000")
    extension = fileid.split(".")[-1]

    test_url = f"{manager_url}/{extension}/check/{fileid}"

    client = httpx.AsyncClient()
    response = await client.get(test_url)
    if response.status_code != 200:
        return HttpResponse(status=404)
    else:
        return HttpResponse(status=200)


@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def index(request: HttpRequest):
    print(f"session key: {request.session.session_key}")
    # Note: We don't need to call this task here as the client will ask for data it needs
    # via the websocket, but this is how we would call a long-running task that sends data
    # back to the client via the websocket...
    # celery.send_task('get-wibl-files', (request.session.session_key,))
    context = {
        "wsURL": f"{get_ws_scheme()}{request.get_host()}/ws/"
    }
    return render(request, 'index.html', context)


@login_required
def logout(request: HttpRequest):
    logout(request)

def heartbeat(request):
    return HttpResponse(status=200)

# TODO: Check to make sure map is displaying correct for client.

def mapTileProxy(request, x, y, z):
    cache_key = f"map_tile_{z}_{x}_{y}"
    cached = cache.get(cache_key)

    if cached:
        return HttpResponse(cached, content_type='image/png')

    session = boto3.Session()
    credentials = session.get_credentials()

    if credentials is None:
        print("ERROR: No credentials found")
        return HttpResponse("No credentials", status=500)

    frozen = credentials.get_frozen_credentials()
    print(f"Access key: {frozen.access_key[:5]}...")
    print(f"Token present: {frozen.token is not None}")

    url = f"https://maps.geo.{REGION}.amazonaws.com/maps/v0/maps/{MAP_NAME}/tiles/{z}/{x}/{y}"

    # Create and sign the request using botocore
    aws_request = AWSRequest(method='GET', url=url)
    SigV4Auth(credentials, 'geo', REGION).add_auth(aws_request)

    # Forward the signed request to AWS
    response = requests.get(url, headers=dict(aws_request.headers))

    cache.set(cache_key, response.content, timeout=60 * 60 * 24)  # 24 hours
    return HttpResponse(
        response.content,
        content_type=response.headers.get('Content-Type', 'image/png')
    )