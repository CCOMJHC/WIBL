CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

if [ $# -gt 0 ] && [ "$1" == '--silent' ]; then
  SILENT=1
else
  SILENT=0
fi

if [ $SILENT -ne 1 ]; then
  echo "CONTENT_ROOT: ${CONTENT_ROOT}"
fi

AWS_TF_ROOT="${CONTENT_ROOT}/scripts/cloud/Terraform/aws"
export AWS_TF_ROOT
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_TF_ROOT: ${AWS_TF_ROOT}"
fi

ARCHITECTURE=arm64
export ARCHITECTURE
if [ $SILENT -ne 1 ]; then
  echo "Using ARCHITECTURE: ${ARCHITECTURE}"
fi

AWS_BUILD='aws-build'
export AWS_BUILD
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_BUILD: ${AWS_BUILD}"
fi

BUILD_DEST=${CONTENT_ROOT}/${AWS_BUILD}
export BUILD_DEST
if [ $SILENT -ne 1 ]; then
  echo "Using BUILD_DEST: ${BUILD_DEST}"
fi

WIBL_UPLOAD_BINARY=upload-server
export WIBL_UPLOAD_BINARY
if [ $SILENT -ne 1 ]; then
  echo "Using WIBL_UPLOAD_BINARY: ${WIBL_UPLOAD_BINARY}"
fi

WIBL_UPLOAD_BINARY_PATH=${BUILD_DEST}/${WIBL_UPLOAD_BINARY}
export WIBL_UPLOAD_BINARY_PATH
if [ $SILENT -ne 1 ]; then
  echo "Using WIBL_UPLOAD_BINARY_PATH: ${WIBL_UPLOAD_BINARY_PATH}"
fi

WIBL_UPLOAD_CONFIG_PROTO=${AWS_TF_ROOT}/config-aws.json.proto
export WIBL_UPLOAD_CONFIG_PROTO
if [ $SILENT -ne 1 ]; then
  echo "Using WIBL_UPLOAD_CONFIG_PROTO: ${WIBL_UPLOAD_CONFIG_PROTO}"
fi

WIBL_UPLOAD_CONFIG_PATH=${BUILD_DEST}/config.json
export WIBL_UPLOAD_CONFIG_PATH
if [ $SILENT -ne 1 ]; then
  echo "Using WIBL_UPLOAD_CONFIG_PATH: ${WIBL_UPLOAD_CONFIG_PATH}"
fi

AWS_PROFILE='wibl-upload-server'
export AWS_PROFILE
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_PROFILE: ${AWS_PROFILE}"
fi

TF_VARS="${AWS_TF_ROOT}/terraform.tfvars"
export TF_VARS
if [ $SILENT -ne 1 ]; then
  echo "Using TF_VARS: ${TF_VARS}"
fi

WIBL_UPLOAD_SERVER_PORT=$(grep 'wibl_upload_server_port=' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export WIBL_UPLOAD_SERVER_PORT
if [ $SILENT -ne 1 ]; then
  echo "Using WIBL_UPLOAD_SERVER_PORT: ${WIBL_UPLOAD_SERVER_PORT}"
fi

AWS_REGION=$(grep 'aws_region=' ${TF_VARS} | cut -d '=' -f 2 | tr -d '"')
export AWS_REGION
if [ $SILENT -ne 1 ]; then
  echo "Using AWS_REGION: ${AWS_REGION}"
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
