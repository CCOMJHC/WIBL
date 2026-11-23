#!/bin/bash

# IMPORTANT: This file and all other scripts other than "build-lambda.sh" are apart of the deprecated scripting
# build approach. The intended build method is to use Terraform. Follow the instructions in the README.md located in the
# Terraform folder.

# This script sets up the SNS topic necessary for the WIBL code to run in AWS.

source configuration-parameters.sh

# Create topics
echo $'\e[31mCreating SNS topics...\e[0m'

TOPIC=${TOPIC_NAME_CONVERSION}
echo $'\e[31m'"Topic for files needing conversion: ${TOPIC}..." $'\e[0m'
aws --region ${AWS_REGION} sns create-topic --name ${TOPIC} \
  | tee "${WIBL_BUILD_LOCATION}/create_sns_${TOPIC}.json"

TOPIC=${TOPIC_NAME_VALIDATION}
echo $'\e[31m'"Topic for files needing validation: ${TOPIC}..." $'\e[0m'
aws --region ${AWS_REGION} sns create-topic --name ${TOPIC} \
  | tee "${WIBL_BUILD_LOCATION}/create_sns_${TOPIC}.json"

TOPIC=${TOPIC_NAME_SUBMISSION}
echo $'\e[31m'"Topic for files needing submission: ${TOPIC}..." $'\e[0m'
aws --region ${AWS_REGION} sns create-topic --name ${TOPIC} \
  | tee "${WIBL_BUILD_LOCATION}/create_sns_${TOPIC}.json"

TOPIC=${TOPIC_NAME_SUBMITTED}
echo $'\e[31m'"Topic for files successfully submitted: ${TOPIC}..." $'\e[0m'
aws --region ${AWS_REGION} sns create-topic --name ${TOPIC} \
  | tee "${WIBL_BUILD_LOCATION}/create_sns_${TOPIC}.json"

exit 0
