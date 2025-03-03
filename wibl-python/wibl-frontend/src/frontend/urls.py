from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("logout", views.logout, name="logout"),
    path('downloadWiblFile/<str:fileid>', views.downloadWiblFile, name="downloadWiblFile")
]
