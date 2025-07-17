from fastapi.responses import StreamingResponse
from fastapi import APIRouter, HTTPException
import boto3
from botocore.exceptions import ClientError
from jinja2.bccache import Bucket

from src.wibl_manager.app_globals import S3_WIBL_BUCKET_NAME, S3_GEOJSON_BUCKET_NAME
from src.wibl_manager import ReturnCodes
import json

# TODO: Configure the boto client from environment variables
# Creates local client for testing, will eventually be a global configuration
s3_client = boto3.client('s3',
                         endpoint_url="http://localstack:4566",
                         use_ssl=False,
                         aws_access_key_id='test',
                         aws_secret_access_key='test')

DownloadRouter = APIRouter()

class Download:
    @staticmethod
    @DownloadRouter.get("/{extension}/check/{fileid}")
    def check_file(extension, fileid):
        if extension == "geojson":
            bucket = S3_GEOJSON_BUCKET_NAME
        elif extension == "wibl":
            bucket = S3_WIBL_BUCKET_NAME
        else:
            print(f"Invalid extension {extension}")
            raise HTTPException(status_code=ReturnCodes.FAILED.value,
                                detail=f"Invalid extension {extension}")
        try:
            s3_client.get_object(Bucket=bucket, Key=fileid)
            return
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "NoSuchKey":
                print(f"File {fileid} does not exist (NoSuchKey).")
                raise HTTPException(status_code=ReturnCodes.FILE_NOT_FOUND.value,
                                    detail=f"File {fileid} does not exist in the bucket {bucket}")
            else:
                raise HTTPException(status_code=ReturnCodes.FAILED.value,
                                    detail=f"S3 error: {code}")
        except:
            raise HTTPException(status_code=ReturnCodes.FAILED.value,
                                detail=f"AWS Error")


    @staticmethod
    @DownloadRouter.get("/wibl/download/{fileid}")
    def wibl_download(fileid):
        s3_file = s3_client.get_object(Bucket=S3_WIBL_BUCKET_NAME, Key=fileid)

        # Define iterable to be returned
        def create_stream():
            for chunk in s3_file['Body'].iter_chunks(1024):
                yield chunk

        return StreamingResponse(create_stream(), headers={'Content-Disposition': f'attachment; filename="{fileid}"'})

    @staticmethod
    @DownloadRouter.get("/geojson/download/{fileid}")
    def geojson_download(fileid):

        s3_file = s3_client.get_object(Bucket=S3_GEOJSON_BUCKET_NAME, Key=fileid)

        # Define iterable to be returned
        def create_stream():
            for chunk in s3_file['Body'].iter_chunks(1024):
                yield chunk

        return StreamingResponse(create_stream(), headers={'Content-Disposition': f'attachment; filename="{fileid}"'})

    @staticmethod
    @DownloadRouter.get("/geojson/save/{fileid}")
    def geojson_save(fileid):
        try:
            s3_file = s3_client.get_object(Bucket=S3_GEOJSON_BUCKET_NAME, Key=fileid)
            file_content = s3_file['Body'].read().decode('utf-8')
            json_content = json.loads(file_content)
            return json_content
        except ClientError:
            print(f"Could not find file {fileid} in bucket {S3_GEOJSON_BUCKET_NAME}")
            raise HTTPException(status_code=ReturnCodes.FILE_NOT_FOUND.value,
                                detail=f"File {fileid} does not exist in the bucket {S3_GEOJSON_BUCKET_NAME}")
