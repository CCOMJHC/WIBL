#!/usr/bin/env bash
set -eu -o pipefail

SCRIPT_DIR=$(realpath "$(dirname $0)")

# Test wibl command line tool

## Define clean-up function
function cleanup () {
  rm -f /tmp/test-wibl.bin
  rm -f /tmp/test-wibl-buffer-constr.bin
  rm -f /tmp/test-wibl-inject.bin
  rm -f /tmp/test-wibl-inject.geojson
  docker compose -f "${SCRIPT_DIR}/docker-compose.yaml" down
}
trap cleanup EXIT

## Clean-up from possibly failed previous runs
cleanup

## Create some data using `datasim`
wibl datasim -f /tmp/test-wibl.bin -d 3600 -s -b || exit $?

## Create some data using `datasim` (use buffer constructor for logger file)
wibl datasim -f /tmp/test-wibl-buffer-constr.bin -d 3600 -s -b --use-buffer-constructor || exit $?

## Parse binary file into text output using `parsewibl`
wibl parsewibl /tmp/test-wibl.bin || exit $?

## Add platform metadata to WIBL file using `editwibl`
wibl editwibl -m tests/data/b12_v3_metadata_example.json /tmp/test-wibl.bin /tmp/test-wibl-inject.bin || exit $?

## Convert binary WIBL file into GeoJSON using `procwibl`
wibl procwibl -c tests/data/configure.local.json /tmp/test-wibl-inject.bin /tmp/test-wibl-inject.geojson || exit $?

## Test uploadwibl locally using localstack to emulate S3
### Start localstack
docker compose -f "${SCRIPT_DIR}/docker-compose.yaml" up -d --wait

### Create bucket
export BUCKET_NAME=wibl-test-uploadwibl
export AWS_SCHEME=http
export AWS_ENDPOINT=127.0.0.1:24566
export S3_ENDPOINT_URL="${AWS_SCHEME}://${AWS_ENDPOINT}"
export AWS_REGION='us-east-1'
export AWS_ACCESS_KEY_ID='test'
export AWS_SECRET_ACCESS_KEY='test'
aws --endpoint ${S3_ENDPOINT_URL} \
  --region ${AWS_REGION} \
  s3api create-bucket --bucket ${BUCKET_NAME}

### Run upload wibl
wibl uploadwibl -b ${BUCKET_NAME} -s vessel-name /tmp/test-wibl-inject.bin

num_objects=$(aws --endpoint ${S3_ENDPOINT_URL} \
  --region ${AWS_REGION} \
  s3api list-objects --bucket ${BUCKET_NAME} | jq '.Contents | length')
expect=1
if [[ $num_objects -ne $expect ]]; then
    echo "Expected there to be ${expect} objects in bucket ${BUCKET_NAME} but there were ${num_objects}."
    exit 1
fi

exit 0
