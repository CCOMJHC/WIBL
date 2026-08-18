#!/bin/bash
#
# IMPORTANT: This file and all other scripts other than "build-lambda.sh" are apart of the deprecated scripting
# build approach. The intended build method is to use Terraform. Follow the instructions in the README.md located in the
# Terraform folder.

# This sets up AWS S3 buckets for the incoming WIBL data, and for the staging location
# for intermediate files before they get sent to DCDB.

source configuration-parameters.sh

echo $'\e[31m' Creating incoming data bucket as ${INCOMING_BUCKET} in region ${AWS_REGION}... $'\e[0m'
aws s3api create-bucket \
    --bucket ${INCOMING_BUCKET} \
    --region ${AWS_REGION} \
    --create-bucket-configuration LocationConstraint=${AWS_REGION} \
    | tee "${WIBL_BUILD_LOCATION}/create_lambda_${INCOMING_BUCKET}.json"

echo $'\e[31m' Creating staging data bucket as ${STAGING_BUCKET} in region ${AWS_REGION} ... $'\e[0m'
aws s3api create-bucket \
    --bucket ${STAGING_BUCKET} \
    --region ${AWS_REGION} \
    --create-bucket-configuration LocationConstraint=${AWS_REGION} \
    | tee "${WIBL_BUILD_LOCATION}/create_lambda_${STAGING_BUCKET}.json"

echo $'\e[31m' Creating staging data bucket as ${VIZ_BUCKET} in region ${AWS_REGION} ... $'\e[0m'
aws s3api create-bucket \
    --bucket ${VIZ_BUCKET} \
    --region ${AWS_REGION} \
    --create-bucket-configuration LocationConstraint=${AWS_REGION} \
    | tee "${WIBL_BUILD_LOCATION}/create_lambda_${VIZ_BUCKET}.json"
