#!/usr/bin/env bash
set -eux -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

source ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/tf-aws-init.sh

ACCOUNT_REGION_BUCKET_NAME="${TF_STATE_BUCKET}-${AWS_ACCOUNT_NUMBER}-${AWS_REGION}-an"

echo "Creating terraform state bucket ${TF_STATE_BUCKET} in AWS region ${AWS_REGION}..."
set +e
if [ "${AWS_REGION}" == 'us-east-1' ]; then
  ${AWS_CLI} s3api create-bucket \
    --bucket "${ACCOUNT_REGION_BUCKET_NAME}" \
    --region "${AWS_REGION}" \
    --request-headers '{"x-amz-bucket-namespace": "'"${AWS_ACCOUNT_NUMBER}"'"}' \
    --output json | tee ${AWS_TF_ROOT}/create-terraform-state-bucket.json
  CREATE_RC=${PIPESTATUS[0]}
else
  ${AWS_CLI} s3api create-bucket \
    --bucket "${ACCOUNT_REGION_BUCKET_NAME}" \
    --region "${AWS_REGION}" \
    --create-bucket-configuration LocationConstraint="${AWS_REGION}" \
    --bucket-namespace "account-regional"  \
    --output json | tee ${AWS_TF_ROOT}/create-terraform-state-bucket.json
  CREATE_RC=${PIPESTATUS[0]}
fi
set -e

if [ "${CREATE_RC}" -ne 0 ]; then
  echo "create-bucket exited with status ${CREATE_RC}; checking if bucket already exists..."
  if ${AWS_CLI} s3api head-bucket --bucket "${ACCOUNT_REGION_BUCKET_NAME}" 2>/dev/null; then
    echo "Bucket ${ACCOUNT_REGION_BUCKET_NAME} already exists and is owned by you."
  else
    echo "Bucket creation failed for a reason other than 'already exists'." >&2
    exit "${CREATE_RC}"
  fi
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

