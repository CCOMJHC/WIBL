#!/bin/bash

WIBL_BUILD_LOCATION=$(git rev-parse --show-toplevel)/wibl-python/awsbuild
ACCOUNT_NUMBER=$(aws sts get-caller-identity --query Account --output text)
SRC_PATH=$(git rev-parse --show-toplevel)/wibl-python
TF_LOG=DEBUG
terraform init && terraform apply -var="src_path=${SRC_PATH}" -var="wibl_build_path=${WIBL_BUILD_LOCATION}" -var="account_number=${ACCOUNT_NUMBER}"
