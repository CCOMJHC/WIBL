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
    path('django_plotly_dash/', include('django_plotly_dash.urls'))
]
