#!/bin/bash

aws s3api create-bucket --create-bucket-configuration LocationConstraint=us-east-2 --bucket 'unhjhc-wibl-incoming'
aws sns create-topic --name 'unhjhc-wibl-conversion'
