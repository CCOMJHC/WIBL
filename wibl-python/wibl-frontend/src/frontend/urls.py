from django.urls import path, include
from frontend import Dashboard
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("heartbeat", views.heartbeat, name="heartbeat"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("logout", views.logout, name="logout"),
    path('downloadFile/<str:fileid>', views.downloadFile, name="downloadFile"),
    path('saveGeojsonFile/<str:fileid>', views.rawGeojsonFile, name="saveGeojsonFile"),
    path('check/<str:fileid>', views.checkFileAvail, name="checkFileAvail"),
    path('django_plotly_dash/', include('django_plotly_dash.urls')),
    path('mapTile/<int:z>/<int:x>/<int:y>/', views.mapTileProxy, name='mapTileProxy'),
    path('mapStyle/', views.map_style_proxy),
    path('mapSprites/<str:filename>', views.map_sprites_proxy),
    path('mapGlyphs/<str:fontstack>/<str:range>', views.map_glyphs_proxy)
]
