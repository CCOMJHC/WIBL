WIBL_SRC_LOCATION=$(git rev-parse --show-toplevel)/wibl-python
WIBL_BUILD_LOCATION=${WIBL_SRC_LOCATION}/awsbuild
mkdir -p ${WIBL_BUILD_LOCATION} || exit $?

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")
AWS_TF_ROOT="${CONTENT_ROOT}/scripts/cloud/AWS/Terraform"
TF_VARS="${AWS_TF_ROOT}/terraform.tfvars"
ARCHITECTURE=$(grep '^architecture =' ${TF_VARS} | cut -d '=' -f 2 | tr -d '" ')
PYTHONVERSION=$(grep '^python_version =' ${TF_VARS} | cut -d '=' -f 2 | tr -d '" ')

# $WIBL_PACKAGE is the absolute path of the zip file containing the lambda code
WIBL_PACKAGE=${WIBL_BUILD_LOCATION}/wibl-package-py${PYTHONVERSION}-${ARCHITECTURE}.zip
