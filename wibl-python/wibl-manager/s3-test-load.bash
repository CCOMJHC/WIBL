#!/bin/bash

aws --endpoint-url 'http://localstack:4566' s3api create-bucket --bucket 'wibl-test'

touch test_file.txt

dd if=/dev/urandom of='test_file.txt' bs=1000 count=10

aws --endpoint-url 'http://localstack:4566' s3api put-object --bucket 'wibl-test' \
                  --key 'test_file.txt' --body '/opt/code/localstack/test_file.txt'