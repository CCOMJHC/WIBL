#!/bin/bash

aws --endpoint-url 'http://localstack:4566' s3api create-bucket --bucket 'wibl-test'

touch test_file.txt

dd if=/dev/urandom of='98C4ED55-190C-40B5-99DF-CC77E1531D1A.wibl' bs=1000 count=10

aws --endpoint-url 'http://localstack:4566' s3api put-object --bucket 'wibl-test' \
                  --key '98C4ED55-190C-40B5-99DF-CC77E1531D1A.wibl' --body '/opt/code/localstack/98C4ED55-190C-40B5-99DF-CC77E1531D1A.wibl'