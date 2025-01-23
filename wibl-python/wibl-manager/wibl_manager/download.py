from flask_restful import Resource
from flask import Response
import boto3

s3_client = boto3.client('s3',
                                 endpoint_url="http://localstack:4566",
                                 use_ssl=False,
                                 aws_access_key_id='test',
                                 aws_secret_access_key='test')

class Download(Resource):
    def get(self, fileid):
        def create_stream():
            s3_file = s3_client.get_object(Bucket='wibl-test', Key=fileid)
            for chunk in s3_file['Body'].iter_chunks(1024):
                yield chunk

        return Response(
            create_stream(),
            content_type='application/octet-stream',
            headers = {'Content-Disposition': f'attachment; filename="{fileid}"'}
        )





