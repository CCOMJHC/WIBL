import os

from flask import Blueprint, render_template
from flask_login import login_required, current_user

import requests

from wibl_frontend.cloud import cloud_health_check


MANAGEMENT_URL = os.getenv('MANAGEMENT_URL', None)
MANAGEMENT_HEARTBEAT = os.getenv('MANAGEMENT_HEARTBEAT_PATH', '/heartbeat')
HEARTBEAT_URL = f"{MANAGEMENT_URL}{MANAGEMENT_HEARTBEAT}"
CLOUD_HEALTH_CHECK_OK: bool = False

main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/heartbeat')
def heartbeat():
    global CLOUD_HEALTH_CHECK_OK
    # Make sure we can talk to the management interface via its heartbeat
    r = requests.get(HEARTBEAT_URL)
    if r.status_code != 200:
        return f"Unable to reach management heartbeat {HEARTBEAT_URL}, response was: {r.status_code}", 500
    if not CLOUD_HEALTH_CHECK_OK:
        # Make sure we have access to the necessary cloud resources (lambdas/functions, buckets/object stores).
        # Use the global CLOUD_HEALTH_CHECK_OK to make sure we stop doing this check once it succeeds as the policies
        # controlling access are unlikely to change, and we don't want to incur undue cloud costs for doing this
        # check each time the service health check is run.
        if not cloud_health_check():
            return f"Unable to access required cloud resources", 500
        CLOUD_HEALTH_CHECK_OK = True
    return 'Manager and cloud resource access OK', 200


@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)
