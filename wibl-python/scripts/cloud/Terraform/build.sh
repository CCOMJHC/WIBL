#!/bin/bash

WIBL_BUILD_LOCATION=$(git rev-parse --show-toplevel)/wibl-python/awsbuild
ACCOUNT_NUMBER=$(aws sts get-caller-identity --query Account --output text)
terraform init && terraform apply -var="wibl_build_path=${WIBL_BUILD_LOCATION}" -var="account_number=${ACCOUNT_NUMBER}"
