# Routes for WebSockets
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/wibl/table', consumers.WiblFileConsumer.as_asgi()),
    path('ws/wibl/detail', consumers.WiblFileDetailConsumer.as_asgi()),
    path('ws/geojson/table', consumers.GeojsonFileConsumer.as_asgi()),
    path('ws/geojson/detail', consumers.GeojsonFileDetailConsumer.as_asgi())
]
