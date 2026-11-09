# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "boto3",
# ]
# ///
import json
import os
import sys
from pathlib import Path

import boto3

from botocore.exceptions import ClientError


# Configuration
REGION = os.environ.get("WIBL_AWS_REGION", "us-east-2")
BUCKET_NAME = os.environ.get("WIBL_INCOMING_BUCKET_NAME", "default-incoming-bucket")
LAMBDA_NAME = os.environ.get("WIBL_CONVERSION_START_LAMBDA_NAME", "default-wibl-conversion-start-lambda")

TEST_KEY = "test_file.wibl"
TEST_FILE_PATH = (Path(__file__).parent / TEST_KEY).absolute()


def main():
    s3_client = boto3.client("s3", region_name=REGION)
    lambda_client = boto3.client("lambda", region_name=REGION)

    try:
        s3_client.upload_file(str(TEST_FILE_PATH), BUCKET_NAME, TEST_KEY)
    except ClientError as e:
        sys.exit(f"S3 upload failed: {e}")

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

    if response["StatusCode"] != 200:
        sys.exit(f"Failed to invoke lambda {LAMBDA_NAME}, status code was: {response["StatusCode"]}")

    return 0


if __name__ == '__main__':
    main()
