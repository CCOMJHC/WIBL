#!/usr/bin/env bash
set -eu -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

source ${CONTENT_ROOT}/scripts/cloud/Terraform/aws/tf-aws-init.sh

echo "Building WIBL upload-server binary..."
source ${CONTENT_ROOT}/scripts/cloud/Terraform/aws/build-server.bash

echo "Create WIBL upload-server certificate..."
rm -rf ${CERTS_DEST} && mkdir ${CERTS_DEST}
OUT_DIR=${CERTS_DEST} ${CONTENT_ROOT}/scripts/cert-gen.sh

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
  -var "wibl_upload_server_crt_path=${CERTS_DEST}/server.crt" \
  -var "wibl_upload_server_key_path=${CERTS_DEST}/server.key" \
  -var "wibl_upload_ca_crt_path=${CERTS_DEST}/ca.crt" \
  -auto-approve
popd
