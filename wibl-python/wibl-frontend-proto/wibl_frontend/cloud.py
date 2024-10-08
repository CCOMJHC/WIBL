import os
from typing import List
import json


INCOMING_BUCKET = os.getenv('INCOMING_BUCKET')
STAGING_BUCKET = os.getenv('STAGING_BUCKET')
VIZ_BUCKET = os.getenv('VIZ_BUCKET')


class MakeSoundingVizualizationException(Exception):
    pass


def make_sounding_viz_aws(**kwargs) -> dict:
    import boto3
    client = boto3.client('lambda')
    fn_name = os.getenv('VIZ_LAMBDA')
    if fn_name is None:
        raise ValueError(f"VIZ_LAMBDA environment variable is None")
    if kwargs['dry_run']:
        invok_type = 'DryRun'
    else:
        invok_type = 'RequestResponse'
    payload = {
        "body": {
            "observer_name": kwargs['observer_name'],
            "dest_key": kwargs['output_name'],
            "source_keys": kwargs['input_names']
        }
    }
    try:
        response = client.invoke(
            FunctionName=fn_name,
            Payload=json.dumps(payload),
            InvocationType=invok_type,
            LogType="Tail",
        )
        if kwargs['dry_run']:
            return {'statusCode': response['StatusCode']}
        else:
            return json.load(response['Payload'])
    except ClientError as e:
        raise MakeSoundingVizualizationException(str(e))


def make_sounding_viz(*, observer_name: str, output_name: str, input_names: List[str],
                      cloud: str = 'AWS', dry_run: bool = False) -> dict:
    """

    :param observer_name:
    :param output_name:
    :param input_names:
    :param cloud:
    :param dry_run:
    :return: If ``dry_run`` is False: Dict of form: {'statusCode': 200,
                                                     'body': {'mesg': 'Successfully uploaded map named test_map_42a.pdf.',
                                                              'upload_url': 's3://unhjhc-wibl-viz/test_map_42a.pdf'}
                                                    }
             If ``dry_run`` is True: Dict of form: {'statusCode': 204}
    """
    if cloud == 'AWS':
        return make_sounding_viz_aws(observer_name=observer_name,
                                     output_name=output_name,
                                     input_names=input_names,
                                     dry_run=dry_run)
    raise ValueError(f"Unknown cloud '{cloud}'")


def check_s3_bucket_access(bucket_name: str) -> bool:
    import boto3
    s3 = boto3.client('s3')
    try:
        r = s3.head_bucket(Bucket=bucket_name)
    except TypeError:
        return False
    if r['ResponseMetadata']['HTTPStatusCode'] != 200:
        return False
    return True


def cloud_health_check_aws() -> bool:
    """
    Ensure frontend can access viz lambda and S3 buckets identified by the following environment variables:
        VIZ_LAMBDA, INCOMING_BUCKET, STAGING_BUCKET, VIZ_BUCKET
    :return:
    """
    success = True

    result = make_sounding_viz_aws(observer_name='healthcheck',
                                   output_name='healthcheck',
                                   input_names='healthcheck',
                                   dry_run=True)
    if result['statusCode'] != 204:
        print(f"Unable to invoke VIZ_LAMBDA named {VIZ_LAMBDA}.")
        success = False
    if not check_s3_bucket_access(INCOMING_BUCKET):
        print(f"Unable to access INCOMING_BUCKET named {INCOMING_BUCKET}.")
        success = False
    if not check_s3_bucket_access(STAGING_BUCKET):
        print(f"Unable to access STAGING_BUCKET named {STAGING_BUCKET}.")
        success = False
    if not check_s3_bucket_access(INCOMING_BUCKET):
        print(f"Unable to access VIZ_BUCKET named {VIZ_BUCKET}.")
        success = False

    return success


def cloud_health_check(*, cloud: str = 'AWS'):
    if cloud == 'AWS':
        return cloud_health_check_aws()