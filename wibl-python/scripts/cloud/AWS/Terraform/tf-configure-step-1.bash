#!/usr/bin/env bash
set -eu -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

PROVIDER_PREFIX='unhjhctest'
export PROVIDER_PREFIX

WIBL_AWS_REGION='us-east-1'
export WIBL_AWS_REGION

envsubst < ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/terraform.tfvars.proto > ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/terraform.tfvars
envsubst < ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/main.tf.proto > ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/main.tf

touch ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/default_auth.txt

echo "Successfully created terraform.tfvars and main.tf."
