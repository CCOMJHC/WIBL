import os

import pytest

import requests
from requests.exceptions import ConnectionError

import boto3

from wibl import config_logger_service


logger = config_logger_service()


def is_responsive(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True
    except ConnectionError:
        return False


@pytest.fixture(scope="session")
def localstack_url(docker_ip, docker_services):
    """Ensure that HTTP service is up and responsive."""

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("localstack", 4566)
    url = "http://{}:{}".format(docker_ip, port)
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_responsive(url)
    )

    os.environ['S3_HOST'] = docker_ip
    os.environ['S3_PORT'] = str(port)
    os.environ['FSSPEC_S3_ENDPOINT_URL'] = url
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['AWS_ACCESS_KEY_ID'] = 'CHANGEME'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'CHANGEME'

    return url


@pytest.fixture(scope="session")
def s3_local_rsrc(localstack_url):
    return boto3.resource('s3', endpoint_url=localstack_url, region_name='us-east-1')
