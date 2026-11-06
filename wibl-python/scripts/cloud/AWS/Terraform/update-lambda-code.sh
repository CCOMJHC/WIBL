#!/bin/bash
set -eu -o pipefail


CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

source ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/tf-aws-init.sh
source ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/configuration-parameters.sh


# Rebuild lambda package for upload
${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/build-lambda.sh

# Update conversion lambda code
echo $'\e[31mUpdating code for conversion lambda named' ${CONVERSION_LAMBDA} $'...\e[0m'
${AWS_CLI} lambda update-function-code \
  --function-name ${CONVERSION_LAMBDA} \
  --no-cli-pager \
  --zip-file fileb://${WIBL_PACKAGE}

# Update validation lambda code
echo $'\e[31mUpdating code for validation lambda named' ${VALIDATION_LAMBDA} $'...\e[0m'
${AWS_CLI} lambda update-function-code \
  --function-name ${VALIDATION_LAMBDA} \
  --no-cli-pager \
  --zip-file fileb://${WIBL_PACKAGE}

# Update submission lambda code
echo $'\e[31mUpdating code for submission lambda named' ${SUBMISSION_LAMBDA} $'...\e[0m'
${AWS_CLI} lambda update-function-code \
  --function-name ${SUBMISSION_LAMBDA} \
  --no-cli-pager \
  --zip-file fileb://${WIBL_PACKAGE}

echo $'\e[31mUpdating code for conversion start lambda named' ${CONVERSION_START_LAMBDA} $'...\e[0m'
${AWS_CLI} lambda update-function-code \
  --function-name ${CONVERSION_START_LAMBDA} \
  --no-cli-pager \
  --zip-file fileb://${WIBL_PACKAGE}

echo "Done."
