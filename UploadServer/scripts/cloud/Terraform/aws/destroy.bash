#!/usr/bin/env bash
set -eu -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

source ${CONTENT_ROOT}/scripts/cloud/Terraform/aws/tf-aws-init.sh

pushd ${AWS_TF_ROOT}
echo "Deleting WIBL upload-server AWS deployment via terraform..."
terraform apply \
  -var "wibl_upload_binary_path=${WIBL_UPLOAD_BINARY_PATH}" \
  -var "wibl_upload_config_path=${WIBL_UPLOAD_CONFIG_PATH}" \
  -destroy -auto-approve
popd
