CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

if [ $# -gt 0 ] && [ "$1" == '--silent' ]; then
  SILENT=1
else
  SILENT=0
fi

if [ $SILENT -ne 1 ]; then
  echo "CONTENT_ROOT: ${CONTENT_ROOT}"
fi

AWS_TF_ROOT="${CONTENT_ROOT}/scripts/cloud/AWS/Terraform"
export AWS_TF_ROOT
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_TF_ROOT: ${AWS_TF_ROOT}"
fi

AWS_PROFILE='default'
export AWS_PROFILE
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_PROFILE: ${AWS_PROFILE}"
fi

TF_VARS="${AWS_TF_ROOT}/terraform.tfvars"
export TF_VARS
if [ $SILENT -ne 1 ]; then
  echo "Using TF_VARS: ${TF_VARS}"
fi

AWS_REGION=$(grep '^region =' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export AWS_REGION
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_REGION: ${AWS_REGION}"
fi

TF_STATE_BUCKET=$(grep '^terraform_state_bucket =' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export TF_STATE_BUCKET
if [ $SILENT -ne 1 ]; then
  echo "Using TF_STATE_BUCKET: ${TF_STATE_BUCKET}"
fi

TF_STATE_KEY=$(grep '^terraform_state_key =' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export TF_STATE_KEY
if [ $SILENT -ne 1 ]; then
  echo "Using TF_STATE_KEY: ${TF_STATE_KEY}"
fi

AWS_CLI="aws --profile ${AWS_PROFILE} --region ${AWS_REGION}"
export AWS_CLI
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_CLI: ${AWS_CLI}"
fi

AWS_ACCOUNT_NUMBER=$(eval "${AWS_CLI} sts get-caller-identity --query Account --output text")
export AWS_ACCOUNT_NUMBER
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_ACCOUNT_NUMBER: ${AWS_ACCOUNT_NUMBER}"
fi
