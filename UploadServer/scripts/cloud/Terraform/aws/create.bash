#!/usr/bin/env bash
set -eu -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

source ${CONTENT_ROOT}/scripts/cloud/Terraform/aws/tf-aws-init.sh

echo "Building WIBL upload-server binary..."
source ${CONTENT_ROOT}/scripts/cloud/Terraform/aws/build-server.bash

echo "Create WIBL upload-server certificate path..."
rm -rf ${CERTS_DEST} && mkdir ${CERTS_DEST}

echo "Creating WIBL upload-server AWS configuration..."
envsubst < "${WIBL_UPLOAD_CONFIG_PROTO}" > "${WIBL_UPLOAD_CONFIG_PATH}"

echo "Creating WIBL upload-server AWS deployment via terraform..."
pushd ${AWS_TF_ROOT}
echo "Running terraform init..."
terraform init

echo "Running terraform apply..."
terraform apply \
  -var "wibl_upload_binary_path=${WIBL_UPLOAD_BINARY_PATH}" \
  -var "wibl_upload_config_path=${WIBL_UPLOAD_CONFIG_PATH}" \
  -var "wibl_certs_path=${CERTS_DEST}" \
  -auto-approve
popd
