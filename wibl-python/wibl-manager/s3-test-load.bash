#!/bin/bash

aws --endpoint-url 'http://localstack:4566' s3api create-bucket --bucket 'wibl-test'

aws --endpoint-url 'http://localstack:4566' s3api put-object --bucket 'wibl-test' \
                  --key '047EEFC3-7EEC-4FFD-816F-B6DB15E52297.geojson' --body '/opt/code/localstack/047EEFC3-7EEC-4FFD-816F-B6DB15E52297.geojson'