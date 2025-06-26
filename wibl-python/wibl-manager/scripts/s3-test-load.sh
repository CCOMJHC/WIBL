#!/bin/bash

awslocal s3api create-bucket --bucket 'wibl-test'

awslocal s3api create-bucket --bucket 'geojson-test'

awslocal s3api put-object --bucket 'geojson-test' \
                  --key '047EEFC3-7EEC-4FFD-816F-B6DB15E52297.geojson' --body '/opt/code/localstack/047EEFC3-7EEC-4FFD-816F-B6DB15E52297.geojson'