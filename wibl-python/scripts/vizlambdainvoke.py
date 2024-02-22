import json

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

config = Config(
    region_name = 'us-east-2'
)
client = boto3.client('lambda', config=config)

DRY_RUN = False
fn_name = 'unhjhc-wibl-visualization'
payload = {
    "body": {
        "observer_name": "Test observer",
        "dest_key": "test_map_42a",
        "source_keys": [
            "D57112C4-6F5C-4398-A920-B3D51A6AEAFB.json"
        ]
  }
}
if DRY_RUN:
    invok_type = 'DryRun'
else:
    invok_type = 'RequestResponse'
try:
    response = client.invoke(
        FunctionName=fn_name,
        Payload=json.dumps(payload),
        InvocationType=invok_type,
        LogType="Tail",
    )
    if DRY_RUN:
        resp_dict = {'statusCode': response['StatusCode']}
    else:
        resp_dict = json.load(response['Payload'])
    print(f"Response from calling {fn_name} was: {resp_dict}")
    print(f"Status code from calling {fn_name} was: {response['StatusCode']}")
except ClientError as e:
    print(f"Error invoking function {fn_name}: {str(e)}")
    raise e
