CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")
source ${CONTENT_ROOT}/scripts/cloud/AWS/Terraform/configuration-base.sh

ARCHITECTURE=$(terraform output -raw architecture)
PYTHONVERSION=$(terraform output -raw python_version)
CONVERSION_LAMBDA=$(terraform output -raw conversion_lambda_name)
CONVERSION_START_LAMBDA=$(terraform output -raw conversion_start_lambda_name)
VALIDATION_LAMBDA=$(terraform output -raw validation_lambda_name)
SUBMISSION_LAMBDA=$(terraform output -raw submission_lambda_name)

# $WIBL_PACKAGE is the absolute path of the zip file containing the lambda code
WIBL_PACKAGE=${WIBL_BUILD_LOCATION}/wibl-package-py${PYTHONVERSION}-${ARCHITECTURE}.zip
