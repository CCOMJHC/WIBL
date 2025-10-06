#!/usr/bin/env bash
set -eu -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

source ${CONTENT_ROOT}/scripts/cloud/Terraform/aws/tf-aws-init.sh

echo "Creating WIBL upload-server AWS deployment via terraform..."
pushd ${AWS_TF_ROOT}
echo "Running terraform init..."
terraform init

echo "Running terraform apply..."
terraform apply -auto-approve
popd
