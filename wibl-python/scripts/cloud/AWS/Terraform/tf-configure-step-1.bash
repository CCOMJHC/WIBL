#!/usr/bin/env bash
set -eu -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

PROVIDER_PREFIX='default'
export PROVIDER_PREFIX

envsubst < ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/terraform.tfvars.proto > ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/terraform.tfvars

touch ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/default_auth.txt