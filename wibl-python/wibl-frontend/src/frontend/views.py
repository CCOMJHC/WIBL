from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpRequest

from wiblfe.celery import app as celery

def get_user_or_session_id(request: HttpRequest) -> str:
    if request.user.is_authenticated:
        return request.user.id
    else:
        return request.session.session_key

@login_required
def index(request: HttpRequest):
    user_or_session_id = get_user_or_session_id(request)
    print(f"user_or_session_id: {user_or_session_id}")
    #celery.send_task('get-wibl-files')
    context = {
        'message': 'Hello, world!!!'
    }
    return render(request, 'frontend/index.html', context)
