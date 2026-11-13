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
  docker compose -f "${SCRIPT_DIR}/docker-compose.yaml" down -v
}
trap cleanup EXIT

## Clean-up from possibly failed previous runs
cleanup

## Create some data using `datasim`
wibl datasim -f /tmp/test-wibl.bin -d 3600 -s -b

## Create some data using `datasim` (use buffer constructor for logger file)
wibl datasim -f /tmp/test-wibl-buffer-constr.bin -d 3600 -s -b --use-buffer-constructor

## Parse binary file into text output using `parsewibl`
wibl parsewibl /tmp/test-wibl.bin

## Add platform metadata to WIBL file using `editwibl`
wibl editwibl -m tests/data/b12_v3_metadata_example.json /tmp/test-wibl.bin /tmp/test-wibl-inject.bin

## Convert binary WIBL file into GeoJSON using `procwibl`
wibl procwibl -c tests/data/configure.local.json /tmp/test-wibl-inject.bin /tmp/test-wibl-inject.geojson

## Validate GeoJSON
wibl validate -c tests/data/configure.local.json /tmp/test-wibl-inject.geojson

# Test uploadwibl locally using localstack to emulate S3
## Start garage
docker compose -f "${SCRIPT_DIR}/docker-compose.yaml" up -d --wait

## Initialize garage cluster for local S3
GARAGE="docker compose -f ${SCRIPT_DIR}/docker-compose.yaml exec -T wibl-test-uploadwibl-garage /garage"
### Assign the single node to a cluster layout (required before the S3 API is usable)
NODE_ID=$(${GARAGE} node id -q | cut -d '@' -f 1)
${GARAGE} layout assign -z dc1 -c 1G "${NODE_ID}"
${GARAGE} layout apply --version 1

### Create bucket
export BUCKET_NAME=wibl-test-uploadwibl
export AWS_SCHEME=http
export AWS_ENDPOINT=127.0.0.1:24566
export S3_ENDPOINT_URL="${AWS_SCHEME}://${AWS_ENDPOINT}"
export AWS_REGION='us-east-1'
export AWS_ACCESS_KEY_ID="GK$(openssl rand -hex 16)"
export AWS_SECRET_ACCESS_KEY="$(openssl rand -hex 32)"
export WIBL_TEST=1
${GARAGE} key import --yes -n wibl-test-key "${AWS_ACCESS_KEY_ID}" "${AWS_SECRET_ACCESS_KEY}"
${GARAGE} bucket create "${BUCKET_NAME}"
${GARAGE} bucket allow --read --write --owner "${BUCKET_NAME}" --key wibl-test-key

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

echo "Integration tests successful."
exit 0
