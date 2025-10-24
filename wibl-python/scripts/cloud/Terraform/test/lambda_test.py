import boto3
import json
import os
import pytest
from botocore.exceptions import ClientError
import requests
# Configuration
REGION = "us-east-2"
BUCKET_NAME = "incoming-bucket-gt-test-1"
LAMBDA_NAME = "gt-conversion-start-lambda"
TEST_FILE_PATH = "./test-algo-dedup.wibl"
TEST_KEY = "test-algo-dedup.wibl"

test_event_json = {
  "version": "2.0",
  "routeKey": "$default",
  "rawPath": "/",
  "rawQueryString": "",
  "headers": {
    "content-type": "application/json",
    "accept": "*/*",
    "host": "jqkkgh4zfk3v5jnyomv5koryym0syblr.lambda-url.us-east-1.on.aws",
    "user-agent": "python-requests/2.x",
    "x-amzn-trace-id": "Root=1-abc123..."
  },
  "requestContext": {
    "http": {
      "method": "POST",
      "path": "/"
    }
  },
  "body": "{\"object\": \"test-algo-dedup.wibl\"}",
  "isBase64Encoded": False
}

@pytest.fixture(scope="module")
def s3_client():
    return boto3.client("s3", region_name=REGION)


@pytest.fixture(scope="module")
def lambda_client():
    return boto3.client("lambda", region_name=REGION)


def test_lambda():
    lambda_url = "https://jqkkgh4zfk3v5jnyomv5koryym0syblr.lambda-url.us-east-1.on.aws/"

    payload = {
        "object": "test-algo-dedup.wibl"
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(lambda_url, headers=headers, data=json.dumps(payload))

    print("Status Code:", response.status_code)
    print("Response Body:", response.text)

    assert response.status_code == 200

def test_upload(s3_client):
    try:
        s3_client.upload_file(TEST_FILE_PATH, BUCKET_NAME, TEST_KEY)
    except ClientError as e:
        pytest.fail(f"S3 upload failed: {e}")
