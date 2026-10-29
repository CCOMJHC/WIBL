#!/usr/bin/env bash
set -eu -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

PROVIDER_PREFIX='default'
export PROVIDER_PREFIX

WIBL_AWS_REGION='us-east-2'
export WIBL_AWS_REGION

envsubst < ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/terraform.tfvars.proto > ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/terraform.tfvars
envsubst < ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/main.tf.proto > ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/main.tf


touch ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/default_auth.txt