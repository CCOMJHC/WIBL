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

# TODO: Deal with coors problems
# Access to script at 'https://gt-static-files-bucket.s3.amazonaws.com/js/IndexEventManager.js' from origin 'https://d3hrtmap6pzjrj.cloudfront.net' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.Understand this error
# IndexEventManager.js:1  Failed to load resource: net::ERR_FAILEDUnderstand this error
# (index):1 Access to script at 'https://gt-static-files-bucket.s3.amazonaws.com/js/WIBLDetailTable.js' from origin 'https://d3hrtmap6pzjrj.cloudfront.net' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.Understand this error
# WIBLDetailTable.js:1  Failed to load resource: net::ERR_FAILEDUnderstand this error
# (index):1 Access to script at 'https://gt-static-files-bucket.s3.amazonaws.com/js/GeojsonFileTable.js' from origin 'https://d3hrtmap6pzjrj.cloudfront.net' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.Understand this error
# GeojsonFileTable.js:1  Failed to load resource: net::ERR_FAILEDUnderstand this error
# (index):1 Access to script at 'https://gt-static-files-bucket.s3.amazonaws.com/js/WIBLFileTable.js' from origin 'https://d3hrtmap6pzjrj.cloudfront.net' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.Understand this error
# WIBLFileTable.js:1  Failed to load resource: net::ERR_FAILEDUnderstand this error
# (index):1 Access to script at 'https://gt-static-files-bucket.s3.amazonaws.com/js/GeojsonDetailTable.js' from origin 'https://d3hrtmap6pzjrj.cloudfront.net' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.Understand this error
# GeojsonDetailTable.js:1  Failed to load resource: net::ERR_FAILEDUnderstand this error
# (index):1 Uncaught TypeError: Failed to resolve module specifier "js/WIBLFileTable.js". Relative references must start with either "/", "./", or "../".

def test_lambda():
    lambda_url = ("https://chpgjbsgvszkj2o4bi3u5ugkyu0ltrvk.lambda-url.us-east-2.on.aws/")

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
