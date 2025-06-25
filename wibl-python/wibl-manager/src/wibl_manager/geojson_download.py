from flask_restful import Resource, abort
from flask import Response
import boto3
import botocore
from src import wibl_manager as globals

# Creates local client for testing, will eventually be a global configuration
s3_client = boto3.client('s3',
                         endpoint_url="http://localstack:4566",
                         use_ssl=False,
                         aws_access_key_id='test',
                         aws_secret_access_key='test')

# Api gateway with only get functionality
class GeoJSONDownload(Resource):
    def get(self, fileid):
        try:
            s3_file = s3_client.get_object(Bucket=globals.S3_GEOJSON_BUCKET_NAME, Key=fileid)
        except botocore.exceptions.ClientError:
            print(f"File {fileid} does not exist.")
            abort(404, description=f"File {fileid} does not exist in the bucket {globals.S3_GEOJSON_BUCKET_NAME}")

        # Define iterable to be returned
        def create_stream():
            for chunk in s3_file['Body'].iter_chunks(1024):
                yield chunk

        return Response(create_stream(),
                        headers={'Content-Disposition': f'attachment; filename="{fileid}"'},
                        mimetype="application/octet-stream")
