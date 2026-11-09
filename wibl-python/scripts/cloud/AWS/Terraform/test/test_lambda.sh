#!/usr/bin/env bash
set -eu -o pipefail

export AWS_PROFILE='default'

TEST_HOME=$(realpath "$(dirname $0)")
TF_HOME=$(realpath "$(dirname $0)/..")

export WIBL_AWS_REGION=$(terraform -chdir=${TF_HOME} output -raw wibl_aws_region)
echo "Using WIBL_AWS_REGION: ${WIBL_AWS_REGION}"
export WIBL_INCOMING_BUCKET_NAME=$(terraform -chdir=${TF_HOME} output -raw incoming_bucket_name)
echo "Using WIBL_INCOMING_BUCKET_NAME: ${WIBL_INCOMING_BUCKET_NAME}"
export WIBL_CONVERSION_START_LAMBDA_NAME=$(terraform -chdir=${TF_HOME} output -raw conversion_start_lambda_name)
echo "Using WIBL_CONVERSION_START_LAMBDA_NAME: ${WIBL_CONVERSION_START_LAMBDA_NAME}"

python ${TEST_HOME}/lambda_test.py
