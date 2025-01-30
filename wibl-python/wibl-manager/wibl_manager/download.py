from flask_restful import Resource
from flask import Response
import boto3

# Creates local client for testing, will eventually be a global configuration
s3_client = boto3.client('s3',
                         endpoint_url="http://localstack:4566",
                         use_ssl=False,
                         aws_access_key_id='test',
                         aws_secret_access_key='test')

# Api gateway with only get functionality
class Download(Resource):
    def get(self, fileid):

        # Define iterable to be returned
        def create_stream():
            # Currently only configured to search a test bucket
            s3_file = s3_client.get_object(Bucket='wibl-test', Key=fileid)
            for chunk in s3_file['Body'].iter_chunks(1024):
                print(f"Chunk Size: {len(chunk)}")
                yield chunk

        return Response(create_stream(),
                        headers={'Content-Disposition': f'attachment; filename="{fileid}"'},
                        mimetype="application/octet-stream")
