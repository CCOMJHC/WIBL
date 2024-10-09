from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpRequest

from wiblfe.celery import app as celery


@login_required
def index(request: HttpRequest):
    print(f"session key: {request.session.session_key}")
    celery.send_task('get-wibl-files', (request.session.session_key,))
    context = {
        'message': 'Hello, world!!!'
    }
    return render(request, 'frontend/index.html', context)
