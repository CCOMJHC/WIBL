from django.shortcuts import render
from django.http import HttpResponse

from wiblfe.celery import app as celery

# Create your views here.
def index(request):
    celery.send_task('get-wibl-files')
    context = {
        'message': 'Hello, world!!!'
    }
    return render(request, 'frontend/index.html', context)
