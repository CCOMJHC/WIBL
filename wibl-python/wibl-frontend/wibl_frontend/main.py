import os

from flask import Blueprint, render_template
from flask_login import login_required, current_user

import requests


MANAGEMENT_URL = os.getenv('MANAGEMENT_URL', None)
MANAGEMENT_HEARTBEAT = os.getenv('MANAGEMENT_HEARTBEAT_PATH', '/heartbeat')
HEARTBEAT_URL = f"{MANAGEMENT_URL}{MANAGEMENT_HEARTBEAT}"

main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/heartbeat')
def heartbeat():
    # Make sure we can talk to the management interface via its heartbeat
    r = requests.get(HEARTBEAT_URL)
    if r.status_code != 200:
        return f"Unable to reach management heartbeat {HEARTBEAT_URL}, response was: {r.status_code}", 500
    return '', 200


@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)
