#!/usr/bin/env bash
set -eux -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

source ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/tf-aws-init.sh

ACCOUNT_REGION_BUCKET_NAME="${TF_STATE_BUCKET}-${AWS_ACCOUNT_NUMBER}-${AWS_REGION}-an"

echo "Creating terraform state bucket ${TF_STATE_BUCKET} in AWS region ${AWS_REGION}..."
if [ "${AWS_REGION}" == 'us-east-1' ]; then
  ${AWS_CLI} s3api create-bucket \
    --bucket "${ACCOUNT_REGION_BUCKET_NAME}" \
    --region "${AWS_REGION}" \
    --request-headers '{"x-amz-bucket-namespace": "'"${AWS_ACCOUNT_NUMBER}"'"}' \
    --output json | tee ${AWS_TF_ROOT}/create-terraform-state-bucket.json
else
  ${AWS_CLI} s3api create-bucket \
    --bucket "${ACCOUNT_REGION_BUCKET_NAME}" \
    --region "${AWS_REGION}" \
    --create-bucket-configuration LocationConstraint="${AWS_REGION}" \
    --bucket-namespace "account-regional"  \
    --output json | tee ${AWS_TF_ROOT}/create-terraform-state-bucket.json
fi

echo "Enabling bucket versioning in terraform state bucket ${TF_STATE_BUCKET}..."
${AWS_CLI} s3api put-bucket-versioning \
  --bucket "${ACCOUNT_REGION_BUCKET_NAME}" \
  --versioning-configuration Status=Enabled \
  --output json | tee ${AWS_TF_ROOT}/enable-terraform-state-bucket-versioning.json

cat > backend.hcl << EOF
bucket = "${ACCOUNT_REGION_BUCKET_NAME}"
region = "${AWS_REGION}"
key    = "terraform/state/wibl-processing-server-deploy.tfstate"
EOF

echo "Done."

