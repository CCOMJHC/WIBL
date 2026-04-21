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
TEST_FILE_PATH = "./test_file.wibl"
TEST_KEY = "test_file.wibl"

@pytest.fixture(scope="module")
def s3_client():
    return boto3.client("s3", region_name=REGION)


@pytest.fixture(scope="module")
def lambda_client():
    return boto3.client("lambda", region_name=REGION)

def test_upload(s3_client):
    try:
        s3_client.upload_file(TEST_FILE_PATH, BUCKET_NAME, TEST_KEY)
    except ClientError as e:
        pytest.fail(f"S3 upload failed: {e}")

def test_lambda(lambda_client):

    event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json",
        },
        "requestContext": {
            "http": {
                "method": "POST",
                "path": "/",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest"
            }
        },
        "body": "{\"object\": \"test_file.wibl\"}",
        "isBase64Encoded": False
    }

    response = lambda_client.invoke(FunctionName=LAMBDA_NAME, InvocationType="RequestResponse", Payload=json.dumps(event))

    response_payload = json.loads(response["Payload"].read())

    print("Lambda returned:", response_payload)

    assert response["StatusCode"] == 200
