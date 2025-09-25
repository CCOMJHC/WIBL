# This provides information on the configuration of the lambdas
# being generated, the specification for the buckets being used,
# roles, and so on.  This is a separate file so that it can be
# sourced by code to set up lambdas, and another to set up the
# buckets.

# Set this to your AWS account number (twelve-digit AWS account number)
ACCOUNT_NUMBER=$(aws sts get-caller-identity --query Account --output text)

# DCDB will issue you with a unique provider ID to identify your uploads.  This is
# used in many different places in the code; set it here.
DCDB_PROVIDER_ID=UNHJHC

# Provide a trusted IP address limit SSH ingress to our public VPC
TRUSTED_IP_ADDRESS=132.177.103.226

# The script needs to know where to find the WIBL source code so that it can package
# the Python library for upload to AWS.  It also needs a place to stash the resulting
# package.  Set those locations here.
WIBL_SRC_LOCATION=$(git rev-parse --show-toplevel)/wibl-python
WIBL_BUILD_LOCATION=${WIBL_SRC_LOCATION}/awsbuild
mkdir -p ${WIBL_BUILD_LOCATION} || exit $?

# DCDB should provide you with a token to authorise you to upload; change this code
# so that it can find where you've stashed it, and read it in to allow for setup of
# the submission Lambda.
#AUTHKEY=`cat ingest-external-${DCDB_PROVIDER_ID}.txt`

# These parameters configure the AWS region and technical details of the Lambda runtime
# that will be used.  If you change the region, you will also want to change the NumPy
# layer name to reflect your local version.  You can change the architecture and Python
# version, but note that not all combinations of these will result in a Lambda that can
# both get the NumPy later that it needs, and boot successfully.
AWS_REGION=us-east-2
AWS_REGION_S3_PL=pl-7ba54012
ARCHITECTURE=arm64
PYTHONVERSION=3.12
NUMPY_LAYER_NAME=arn:aws:lambda:us-east-2:336392948345:layer:AWSSDKPandas-Python312-Arm64:4

# $WIBL_PACKAGE is the absolute path of the zip file containing the lambda code
WIBL_PACKAGE=${WIBL_BUILD_LOCATION}/wibl-package-py${PYTHONVERSION}-${ARCHITECTURE}.zip

#---------------------------------------------------------------------------------------
# Below here you probably don't need to change much

#DCDB_UPLOAD_URL=https://www.ngdc.noaa.gov/ingest-external/upload/csb/geojson/
DCDB_UPLOAD_URL=https://www.ngdc.noaa.gov/ingest-external/upload/csb/test/geojson/

PROVIDER_PREFIX=`echo ${DCDB_PROVIDER_ID} | tr '[:upper:]' '[:lower:]'`

CONVERSION_LAMBDA=${PROVIDER_PREFIX}-wibl-conversion
VALIDATION_LAMBDA=${PROVIDER_PREFIX}-wibl-validation
SUBMISSION_LAMBDA=${PROVIDER_PREFIX}-wibl-submission
CONVERSION_START_LAMBDA=${PROVIDER_PREFIX}-wibl-conversion-start
VIZ_LAMBDA=${PROVIDER_PREFIX}-wibl-visualization
CONVERSION_LAMBDA_ROLE=${CONVERSION_LAMBDA}-lambda
VALIDATION_LAMBDA_ROLE=${VALIDATION_LAMBDA}-lambda
SUBMISSION_LAMBDA_ROLE=${SUBMISSION_LAMBDA}-lambda
CONVERSION_START_LAMBDA_ROLE=${CONVERSION_START_LAMBDA}-lambda
VIZ_LAMBDA_ROLE=${VIZ_LAMBDA}-lambda

LAMBDA_TIMEOUT=90
LAMBDA_MEMORY=2048

INCOMING_BUCKET=${PROVIDER_PREFIX}-wibl-incoming
STAGING_BUCKET=${PROVIDER_PREFIX}-wibl-staging
VIZ_BUCKET=${PROVIDER_PREFIX}-wibl-viz

# Topic for announcing the existance of files needing conversion
TOPIC_NAME_CONVERSION=${PROVIDER_PREFIX}-wibl-conversion
# Topic for announcing the existance of files needing validation
TOPIC_NAME_VALIDATION=${PROVIDER_PREFIX}-wibl-validation
# Topic for announcing the existance of files needing submission
TOPIC_NAME_SUBMISSION=${PROVIDER_PREFIX}-wibl-submission
# Topic for announcing the successful submission of a file to DCDB
TOPIC_NAME_SUBMITTED=${PROVIDER_PREFIX}-wibl-submitted

TOPIC_ARN_CONVERSION="arn:aws:sns:${AWS_REGION}:${ACCOUNT_NUMBER}:${TOPIC_NAME_CONVERSION}"
TOPIC_ARN_VALIDATION="arn:aws:sns:${AWS_REGION}:${ACCOUNT_NUMBER}:${TOPIC_NAME_VALIDATION}"
TOPIC_ARN_SUBMISSION="arn:aws:sns:${AWS_REGION}:${ACCOUNT_NUMBER}:${TOPIC_NAME_SUBMISSION}"
TOPIC_ARN_SUBMITTED="arn:aws:sns:${AWS_REGION}:${ACCOUNT_NUMBER}:${TOPIC_NAME_SUBMITTED}"

function exit_with_error () {
  echo "Exiting with error:" $1
  exit $?
}

function test_aws_cmd_success () {
  # Test whether AWS CLI command fails if an entity exists
  # Consider successful exit codes to be 0 or 254 (entity already exists)
  if [[ $1 -ne 0 && $1 -ne  254 ]]
  then
    echo "AWS CMD was not successful (exit code was $1), exiting."
    exit $1
  else
    echo "AWS CMD was successful."
  fi
}
