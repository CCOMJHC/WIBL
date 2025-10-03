#!/bin/bash

awslocal s3api create-bucket --create-bucket-configuration LocationConstraint=us-east-2 --bucket 'unhjhc-wibl-incoming'
awslocal sns create-topic --name 'unhjhc-wibl-conversion'
