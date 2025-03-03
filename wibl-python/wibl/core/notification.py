# notification.py
#
# Generate a simple interface to allow notifications to be handled for a variety
# of different cloud systems (at least in theory).
#
# Copyright 2023 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
# Hydrographic Center, University of New Hampshire.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from abc import ABC, abstractmethod

import boto3
import botocore.exceptions as awsexe
import json

from wibl.core.datasource import DataItem

class Notifier(ABC):
    @abstractmethod
    def notify(self, item: DataItem) -> str:
        pass

    def generate_message(self, item: DataItem) -> str:
        message = { "bucket": item.dest_store, "filename": item.dest_key, "size": item.dest_size }
        return json.dumps(message)

class SNSNotifier(Notifier):
    def __init__(self, arn: str) -> None:
        self.arn = arn
    
    def notify(self, item: DataItem, *, verbose: bool = False) -> str:
        sns = boto3.client('sns')
        try:
            if verbose:
                print(f"Publishing item {item} to topic {self.arn}...")
            result = sns.publish(TopicArn=self.arn, Message=self.generate_message(item))
            if verbose:
                print(f"Done publishing item {item} to topic {self.arn}.")
            msgid = result['MessageId']
        except awsexe.ClientError as error:
            print(f'error: notification failed: AWS SNS responded {error}.')
            msgid = None
        return msgid

class LocalNotifier(Notifier):
    def __init__(self, resource: str) -> None:
        self.resource = resource

    def notify(self, item: DataItem) -> str:
        print(f'Local notification for resource {self.resource}, message {self.generate_message(item)}.')
        return self.resource
