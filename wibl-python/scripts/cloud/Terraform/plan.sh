#!/bin/bash

WIBL_BUILD_LOCATION=$(git rev-parse --show-toplevel)/wibl-python/awsbuild
ACCOUNT_NUMBER=$(aws sts get-caller-identity --query Account --output text)
SRC=$(git rev-parse --show-toplevel)/wibl-python
terraform init & terraform plan -var="wibl_build_path=${WIBL_BUILD_LOCATION}" -var="src_path=${SRC}" -var="account_number=${ACCOUNT_NUMBER}"