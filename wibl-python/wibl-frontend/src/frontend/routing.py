# Routes for WebSockets
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/wibl/', consumers.WiblFileConsumer.as_asgi()),
]
