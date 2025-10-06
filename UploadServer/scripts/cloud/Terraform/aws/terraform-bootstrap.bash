#!/usr/bin/env bash
set -eu -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

source ${CONTENT_ROOT}/scripts/cloud/Terraform/aws/tf-aws-init.sh

echo "Creating terraform state bucket ${TF_STATE_BUCKET} in AWS region ${TF_REGION}..."
if [ "${TF_REGION}" == 'us-east-1' ]; then
  ${AWS_CLI} s3api create-bucket \
    --bucket "${TF_STATE_BUCKET}" \
    --region "${TF_REGION}" \
    --output json | tee ${AWS_TF_ROOT}/create-terraform-state-bucket.json
else
  ${AWS_CLI} s3api create-bucket \
    --bucket "${TF_STATE_BUCKET}" \
    --region "${TF_REGION}" \
    --create-bucket-configuration LocationConstraint="${TF_REGION}" \
    --output json | tee ${AWS_TF_ROOT}/create-terraform-state-bucket.json
fi

echo "Enabling bucket versioning in terraform state bucket ${TF_STATE_BUCKET}..."
${AWS_CLI} s3api put-bucket-versioning \
  --bucket "${TF_STATE_BUCKET}" \
  --versioning-configuration Status=Enabled \
  --output json | tee ${AWS_TF_ROOT}/enable-terraform-state-bucket-versioning.json

echo "Done."
