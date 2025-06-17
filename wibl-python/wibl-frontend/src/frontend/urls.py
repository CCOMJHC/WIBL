from django.urls import path, include

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("logout", views.logout, name="logout"),
    path('downloadFile/<str:fileid>', views.downloadFile, name="downloadFile"),
    path('saveGeojsonFile/<str:fileid>', views.saveGeojsonFile, name="saveGeojsonFile"),
    path('django_plotly_dash/', include('django_plotly_dash.urls'))
]
