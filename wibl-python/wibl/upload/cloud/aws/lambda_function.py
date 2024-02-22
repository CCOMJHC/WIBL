import json

import wibl.core.config as conf
from wibl.upload.cloud.aws import get_config_file
from wibl.core import getenv
from wibl.core.datasource import DataItem
import wibl.core.datasource as ds
import wibl.core.notification as nt


def lambda_handler(event, context):
    try:
        # The configuration file for the algorithm should be in the same directory as the lambda function file,
        # and has a "well known" name.  We could attempt to something smarter here, but this is probably enough
        # for now.
        config = conf.read_config(get_config_file())
    except conf.BadConfiguration as e:
        return {
            'statusCode': 400,
            'body': 'Bad configuration'
        }

    controller = ds.AWSController(config)
    notifier = nt.SNSNotifier(getenv('NOTIFICATION_ARN'))

    if 'body' not in event:
        return {
            'statusCode': 400,
            'body': 'Body not found in event.'
        }
    body: dict = json.loads(event['body'])

    s3_object = body['object']

    # Make sure object exists in incoming bucket
    s3_bucket = getenv('INCOMING_BUCKET')
    # Use the same values for source and destination store and key so that we can use the cloud controller
    # (which reads from the source attributes) and the notifier (which reads from the destination attributes)
    data_item: DataItem = DataItem(source_store=s3_bucket,
                                   source_key=s3_object,
                                   source_size=None,
                                   localname=None,
                                   dest_store=s3_bucket,
                                   dest_key=s3_object,
                                   dest_size=None)
    exists, size = controller.exists(data_item)
    if not exists:
        return {
            'statusCode': 404,
            'body': 'Object not found'
        }
    if config['verbose']:
        print(f"Data item {str(data_item)} exists.")
    # Update data item with object size so that we can send a notification
    data_item.source_size = size
    data_item.dest_size = size

    # Send notification to SNS to trigger conversion
    if config['verbose']:
        print(f"Notifying for data item {str(data_item)}...")
    notifier.notify(data_item)
    if config['verbose']:
        print(f"Notification for data item {str(data_item)} complete.")

    return {
        'statusCode': 200,
        'body': f"content-length: {size}"
    }
