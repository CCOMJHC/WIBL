#!/bin/bash

set -eu -o pipefail

source configuration-parameters.sh

# Rebuild lambda package for upload
./build-lambda.sh || exit $?

# Update conversion lambda code
echo $'\e[31mUpdating code for conversion lambda named' ${CONVERSION_LAMBDA} $'...\e[0m'
aws lambda update-function-code \
  --function-name ${CONVERSION_LAMBDA} \
  --no-cli-pager \
  --zip-file fileb://${WIBL_PACKAGE} || exit $?

# Update validation lambda code
echo $'\e[31mUpdating code for validation lambda named' ${VALIDATION_LAMBDA} $'...\e[0m'
aws lambda update-function-code \
  --function-name ${VALIDATION_LAMBDA} \
  --no-cli-pager \
  --zip-file fileb://${WIBL_PACKAGE} || exit $?

# Update submission lambda code
echo $'\e[31mUpdating code for submission lambda named' ${SUBMISSION_LAMBDA} $'...\e[0m'
aws lambda update-function-code \
  --function-name ${SUBMISSION_LAMBDA} \
  --no-cli-pager \
  --zip-file fileb://${WIBL_PACKAGE} || exit $?

echo $'\e[31mUpdating code for conversion start lambda named' ${CONVERSION_START_LAMBDA} $'...\e[0m'
aws lambda update-function-code \
  --function-name ${CONVERSION_START_LAMBDA} \
  --no-cli-pager \
  --zip-file fileb://${WIBL_PACKAGE} || exit $?

exit 0
