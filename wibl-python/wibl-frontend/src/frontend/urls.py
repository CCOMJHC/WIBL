from django.urls import path, include
from . import views
from viewflow.urls import Site, Application
from frontend import Dashboard

urlpatterns = [
    path("", views.index, name="index"),
    path("heartbeat", views.heartbeat, name="heartbeat"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("logout", views.logout, name="logout"),
    path('downloadFile/<str:fileid>', views.downloadFile, name="downloadFile"),
    path('saveGeojsonFile/<str:fileid>', views.saveGeojsonFile, name="saveGeojsonFile"),
    path('check/<str:fileid>', views.checkFileAvail, name="checkFileAvail")
]
