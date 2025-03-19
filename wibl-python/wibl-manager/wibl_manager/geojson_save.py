from flask_restful import Resource
from flask import Response, jsonify
import boto3
import json
import wibl_manager.app_globals as globals

# Creates local client for testing, will eventually be a global configuration
s3_client = boto3.client('s3',
                         endpoint_url="http://localstack:4566",
                         use_ssl=False,
                         aws_access_key_id='test',
                         aws_secret_access_key='test')

# Api gateway with only get functionality
class GeoJSONSave(Resource):
    def get(self, fileid):
        try:
            s3_file = s3_client.get_object(Bucket=globals.S3_BUCKET_NAME, Key=fileid)
            file_content = s3_file['Body'].read().decode('utf-8')
            json_content = json.loads(file_content)
            return jsonify(json_content)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
