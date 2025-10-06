CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

if [ $# -gt 0 ] && [ "$1" == '--silent' ]; then
  SILENT=1
else
  SILENT=0
fi

if [ $SILENT -ne 1 ]; then
  echo "CONTENT_ROOT: ${CONTENT_ROOT}"
fi

AWS_PROFILE='wibl-upload-server'
export AWS_PROFILE
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_PROFILE: ${AWS_PROFILE}"
fi

AWS_TF_ROOT="${CONTENT_ROOT}/scripts/cloud/Terraform/aws"
export AWS_TF_ROOT
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_TF_ROOT: ${AWS_TF_ROOT}"
fi

TF_VARS="${AWS_TF_ROOT}/terraform.tfvars"
export TF_VARS
if [ $SILENT -ne 1 ]; then
  echo "Using TF_VARS: ${TF_VARS}"
fi

AWS_REGION=$(grep 'region=' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export AWS_REGION
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_REGION: ${AWS_REGION}"
fi

TF_STATE_BUCKET=$(grep 'terraform_state_bucket=' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export TF_STATE_BUCKET
if [ $SILENT -ne 1 ]; then
  echo "Using TF_STATE_BUCKET: ${TF_STATE_BUCKET}"
fi

TF_STATE_KEY=$(grep 'terraform_state_key=' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export TF_STATE_KEY
if [ $SILENT -ne 1 ]; then
  echo "Using TF_STATE_KEY: ${TF_STATE_KEY}"
fi

WIBL_UPLOAD_BUCKET_NAME=$(grep 'upload_bucket_name=' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export WIBL_UPLOAD_BUCKET_NAME
if [ $SILENT -ne 1 ]; then
  echo "Using WIBL_UPLOAD_BUCKET_NAME: ${WIBL_UPLOAD_BUCKET_NAME}"
fi

WIBL_UPLOAD_SNS_TOPIC_NAME=$(grep 'upload_sns_topic_name=' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export WIBL_UPLOAD_SNS_TOPIC_NAME
if [ $SILENT -ne 1 ]; then
  echo "Using WIBL_UPLOAD_SNS_TOPIC_NAME: ${WIBL_UPLOAD_SNS_TOPIC_NAME}"
fi

WIBL_UPLOAD_SERVER_PORT=$(grep 'upload_server_port=' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export WIBL_UPLOAD_SERVER_PORT
if [ $SILENT -ne 1 ]; then
  echo "Using WIBL_UPLOAD_SERVER_PORT: ${WIBL_UPLOAD_SERVER_PORT}"
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

WIBL_UPLOAD_SNS_TOPIC_ARN="arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_NUMBER}:${WIBL_UPLOAD_SNS_TOPIC_NAME}"
export WIBL_UPLOAD_SNS_TOPIC_ARN
if [ $SILENT -ne 1 ]; then
  echo "Using WIBL_UPLOAD_SNS_TOPIC_ARN: ${WIBL_UPLOAD_SNS_TOPIC_ARN}"
fi
