#!/bin/bash
#
# This sets up the permissions, triggers, and lambdas required for the WIBL code to run in
# AWS.  If, of course, you have part of this set up already, then you're likely to encounter
# difficulties.  Probably best to clean up in the console first, then try again.

source configuration-parameters.sh

# Specify the URL for the management console component.  Leave empty if you don't want
# to run the management console.
# TODO: This would probably be better generated automatically based on the provider ID
# and some sensible default for URL of the server.
# TODO: Having this set to a value rather than being empty should be the trigger to
# package and deploy the management server container.
MANAGEMENT_URL=http://"$(cat ${WIBL_BUILD_LOCATION}/create_elb.json | jq -r '.LoadBalancers[0].DNSName')"/

LAMBDA_SUBNETS="$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)"
LAMBDA_SECURITY_GROUP="$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')"

####################
# Phase 1: Package up the WIBL software
#
./build-lambda.sh || exit $?

#####################
# Phase 2: Generate IAM roles for the conversion and submission roles, add policy support
#
echo $'\e[31mBuilding the IAM roles for lambdas ...\e[0m'

cat > "${WIBL_BUILD_LOCATION}/lambda-trust-policy.json" <<-HERE
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "lambda.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
HERE

# Generate roles that allow lambdas to assume its execution role, one each for conversion, validation, submission,
# conversion start, and visualization
aws --region ${AWS_REGION} iam create-role \
	--role-name ${CONVERSION_LAMBDA_ROLE} \
	--assume-role-policy-document file://"${WIBL_BUILD_LOCATION}/lambda-trust-policy.json"
test_aws_cmd_success $?

aws --region ${AWS_REGION} iam create-role \
	--role-name ${VALIDATION_LAMBDA_ROLE} \
	--assume-role-policy-document file://"${WIBL_BUILD_LOCATION}/lambda-trust-policy.json"
test_aws_cmd_success $?

aws --region ${AWS_REGION} iam create-role \
	--role-name ${SUBMISSION_LAMBDA_ROLE} \
	--assume-role-policy-document file://"${WIBL_BUILD_LOCATION}/lambda-trust-policy.json"
test_aws_cmd_success $?

aws --region ${AWS_REGION} iam create-role \
	--role-name ${CONVERSION_START_LAMBDA_ROLE} \
	--assume-role-policy-document file://"${WIBL_BUILD_LOCATION}/lambda-trust-policy.json"
test_aws_cmd_success $?

aws --region ${AWS_REGION} iam create-role \
	--role-name ${VIZ_LAMBDA_ROLE} \
	--assume-role-policy-document file://"${WIBL_BUILD_LOCATION}/lambda-trust-policy.json"
test_aws_cmd_success $?

# Attach the ability to run Lambdas to these roles
aws --region ${AWS_REGION} iam attach-role-policy \
	--role-name ${CONVERSION_LAMBDA_ROLE} \
	--policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole || exit $?

aws --region ${AWS_REGION} iam attach-role-policy \
	--role-name ${VALIDATION_LAMBDA_ROLE} \
	--policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole || exit $?

aws --region ${AWS_REGION} iam attach-role-policy \
	--role-name ${SUBMISSION_LAMBDA_ROLE} \
	--policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole || exit $?

aws --region ${AWS_REGION} iam attach-role-policy \
	--role-name ${CONVERSION_START_LAMBDA_ROLE} \
	--policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole || exit $?

aws --region ${AWS_REGION} iam attach-role-policy \
	--role-name ${VIZ_LAMBDA_ROLE} \
	--policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole || exit $?

# Create policy to allow lambdas to join our VPC
# Define policy
cat > "${WIBL_BUILD_LOCATION}/lambda-nic-policy.json" <<-HERE
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:DescribeInstances",
        "ec2:AttachNetworkInterface"
      ],
      "Resource": "*"
    }
  ]
}
HERE

# Create policy
aws --region ${AWS_REGION} iam create-policy \
  --policy-name 'Lambda-VPC' \
  --policy-document file://"${WIBL_BUILD_LOCATION}/lambda-nic-policy.json" \
  | tee "${WIBL_BUILD_LOCATION}/create_lambda_nic_policy.json"

# Attach policy to lambda execution roles
aws --region ${AWS_REGION} iam attach-role-policy \
  --role-name ${CONVERSION_LAMBDA_ROLE} \
  --policy-arn "$(cat ${WIBL_BUILD_LOCATION}/create_lambda_nic_policy.json | jq -r '.Policy.Arn')" \
  | tee "${WIBL_BUILD_LOCATION}/attach_role_policy_lamda_nic_conversion.json"

aws --region ${AWS_REGION} iam attach-role-policy \
  --role-name ${VALIDATION_LAMBDA_ROLE} \
  --policy-arn "$(cat ${WIBL_BUILD_LOCATION}/create_lambda_nic_policy.json | jq -r '.Policy.Arn')" \
  | tee "${WIBL_BUILD_LOCATION}/attach_role_policy_lambda_nic_validation.json"

aws --region ${AWS_REGION} iam attach-role-policy \
  --role-name ${SUBMISSION_LAMBDA_ROLE} \
  --policy-arn "$(cat ${WIBL_BUILD_LOCATION}/create_lambda_nic_policy.json | jq -r '.Policy.Arn')" \
  | tee "${WIBL_BUILD_LOCATION}/attach_role_policy_lambda_nic_submission.json"

aws --region ${AWS_REGION} iam attach-role-policy \
  --role-name ${CONVERSION_START_LAMBDA_ROLE} \
  --policy-arn "$(cat ${WIBL_BUILD_LOCATION}/create_lambda_nic_policy.json | jq -r '.Policy.Arn')" \
  | tee "${WIBL_BUILD_LOCATION}/attach_role_policy_lambda_nic_conversion_start.json"

aws --region ${AWS_REGION} iam attach-role-policy \
  --role-name ${VIZ_LAMBDA_ROLE} \
  --policy-arn "$(cat ${WIBL_BUILD_LOCATION}/create_lambda_nic_policy.json | jq -r '.Policy.Arn')" \
  | tee "${WIBL_BUILD_LOCATION}/attach_role_policy_lambda_nic_viz.json"

echo $'\e[31mWaiting for 10 seconds to allow roles to propagate ...\e[0m'
sleep 10

########################
# Phase 3: Generate the conversion lambda, and configure it to trigger from the conversion SNS topic, which gets
# notifications from S3 upon upload to the incoming bucket.
# Create the conversion lambda
echo $'\e[31mGenerating conversion lambda...\e[0m'
aws --region ${AWS_REGION} lambda create-function \
  --function-name ${CONVERSION_LAMBDA} \
  --no-cli-pager \
	--role arn:aws:iam::${ACCOUNT_NUMBER}:role/${CONVERSION_LAMBDA_ROLE} \
	--runtime python${PYTHONVERSION} \
  --timeout ${LAMBDA_TIMEOUT} \
  --memory-size ${LAMBDA_MEMORY} \
	--handler wibl.processing.cloud.aws.lambda_function.lambda_handler \
	--zip-file fileb://${WIBL_PACKAGE} \
	--architectures ${ARCHITECTURE} \
	--layers ${NUMPY_LAYER_NAME} \
	--vpc-config "SubnetIds=${LAMBDA_SUBNETS},SecurityGroupIds=${LAMBDA_SECURITY_GROUP}" \
	--environment "Variables={NOTIFICATION_ARN=${TOPIC_ARN_VALIDATION},PROVIDER_ID=${DCDB_PROVIDER_ID},DEST_BUCKET=${STAGING_BUCKET},UPLOAD_POINT=${DCDB_UPLOAD_URL},MANAGEMENT_URL=${MANAGEMENT_URL}}" \
	| tee "${WIBL_BUILD_LOCATION}/create_lambda_conversion.json"

echo $'\e[31mConfiguring S3 access policy so that conversion lambda can access S3 incoming and staging buckets...\e[0m'
cat > "${WIBL_BUILD_LOCATION}/lambda-s3-access-all.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowS3AccessAll",
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::${INCOMING_BUCKET}",
                "arn:aws:s3:::${INCOMING_BUCKET}/*",
                "arn:aws:s3:::${STAGING_BUCKET}",
                "arn:aws:s3:::${STAGING_BUCKET}/*"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name "${CONVERSION_LAMBDA_ROLE}" \
	--policy-name lambda-s3-access-all \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-s3-access-all.json" || exit $?

echo $'\e[31mAdding permissions to the conversion lambda for invocation from SNS topic...\e[0m'
aws --region ${AWS_REGION} lambda add-permission \
  --function-name "${CONVERSION_LAMBDA}" \
	--action lambda:InvokeFunction \
	--statement-id s3invoke \
	--principal sns.amazonaws.com \
	--source-arn "${TOPIC_ARN_CONVERSION}" \
	--source-account "${ACCOUNT_NUMBER}" || exit $?

echo $'\e[31mConfiguring SNS access policy so that conversion lambda can publish to' ${TOPIC_NAME_VALIDATION} $'...\e[0m'
cat > "${WIBL_BUILD_LOCATION}/lambda-sns-access-validation.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowSNSAccessValidation",
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": [
                "${TOPIC_ARN_VALIDATION}"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name "${CONVERSION_LAMBDA_ROLE}" \
	--policy-name lambda-conversion-sns-access-validation \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-sns-access-validation.json" || exit $?

########################
# Phase 4: Generate the validation lambda, and configure it to trigger from the validation SNS topic.
# Create the conversion lambda
echo $'\e[31mGenerating conversion lambda...\e[0m'
aws --region ${AWS_REGION} lambda create-function \
  --function-name ${VALIDATION_LAMBDA} \
  --no-cli-pager \
	--role arn:aws:iam::${ACCOUNT_NUMBER}:role/${VALIDATION_LAMBDA_ROLE} \
	--runtime python${PYTHONVERSION} \
  --timeout ${LAMBDA_TIMEOUT} \
  --memory-size ${LAMBDA_MEMORY} \
	--handler wibl.validation.cloud.aws.lambda_function.lambda_handler \
	--zip-file fileb://${WIBL_PACKAGE} \
	--architectures ${ARCHITECTURE} \
	--layers ${NUMPY_LAYER_NAME} \
	--vpc-config "SubnetIds=${LAMBDA_SUBNETS},SecurityGroupIds=${LAMBDA_SECURITY_GROUP}" \
	--environment "Variables={NOTIFICATION_ARN=${TOPIC_ARN_SUBMISSION},PROVIDER_ID=${DCDB_PROVIDER_ID},STAGING_BUCKET=${STAGING_BUCKET},UPLOAD_POINT=${DCDB_UPLOAD_URL},MANAGEMENT_URL=${MANAGEMENT_URL}}" \
	| tee "${WIBL_BUILD_LOCATION}/create_lambda_validation.json"

echo $'\e[31mConfiguring S3 access policy so that conversion lambda can access S3 staging buckets...\e[0m'
cat > "${WIBL_BUILD_LOCATION}/lambda-s3-access-staging.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowS3AccessStaging",
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::${STAGING_BUCKET}",
                "arn:aws:s3:::${STAGING_BUCKET}/*"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name "${VALIDATION_LAMBDA_ROLE}" \
	--policy-name lambda-s3-access-staging \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-s3-access-staging.json" || exit $?

echo $'\e[31mAdding permissions to the validation lambda for invocation from SNS topic...\e[0m'
aws --region ${AWS_REGION} lambda add-permission \
  --function-name "${VALIDATION_LAMBDA}" \
	--action lambda:InvokeFunction \
	--statement-id s3invoke \
	--principal sns.amazonaws.com \
	--source-arn "${TOPIC_ARN_VALIDATION}" \
	--source-account "${ACCOUNT_NUMBER}" || exit $?

echo $'\e[31mConfiguring SNS access policy so that validation lambda can publish to' ${TOPIC_NAME_SUBMISSION} $'...\e[0m'
cat > "${WIBL_BUILD_LOCATION}/lambda-sns-access-submission.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowSNSAccessSubmission",
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": [
                "${TOPIC_ARN_SUBMISSION}"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name "${VALIDATION_LAMBDA_ROLE}" \
	--policy-name lambda-conversion-sns-access-submission \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-sns-access-submission.json" || exit $?

########################
# Phase 5: Generate the submission lambda, and configure it to trigger from the submission SNS topic
# TODO: PROVIDER_AUTH should be encrypted secrets, not an environment variable
# Create the submission bucket
echo $'\e[31mGenerating submission lambda...\e[0m'
aws --region ${AWS_REGION} lambda create-function \
	--function-name ${SUBMISSION_LAMBDA} \
	--no-cli-pager \
	--role arn:aws:iam::${ACCOUNT_NUMBER}:role/${SUBMISSION_LAMBDA_ROLE} \
	--runtime python${PYTHONVERSION} \
  --timeout ${LAMBDA_TIMEOUT} \
  --memory-size ${LAMBDA_MEMORY} \
	--handler wibl.submission.cloud.aws.lambda_function.lambda_handler \
	--zip-file fileb://${WIBL_PACKAGE} \
	--vpc-config "SubnetIds=${LAMBDA_SUBNETS},SecurityGroupIds=${LAMBDA_SECURITY_GROUP}" \
	--environment "Variables={NOTIFICATION_ARN=${TOPIC_ARN_SUBMITTED},PROVIDER_ID=${DCDB_PROVIDER_ID},PROVIDER_AUTH=${AUTHKEY},STAGING_BUCKET=${STAGING_BUCKET},UPLOAD_POINT=${DCDB_UPLOAD_URL},MANAGEMENT_URL=${MANAGEMENT_URL}}" \
	| tee "${WIBL_BUILD_LOCATION}/create_lambda_submission.json"

echo $'\e[31mConfiguring S3 access policy so that submission lambda can access S3 staging bucket...\e[0m'
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name "${SUBMISSION_LAMBDA_ROLE}" \
	--policy-name lambda-s3-access-staging \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-s3-access-staging.json" || exit $?

echo $'\e[31mAdding permissions to the submission lambda for invocation from topic' \
  "${TOPIC_NAME_SUBMISSION}" $'...\e[0m'
aws --region ${AWS_REGION} lambda add-permission \
  --function-name "${SUBMISSION_LAMBDA}" \
	--action lambda:InvokeFunction \
	--statement-id s3invoke \
	--principal sns.amazonaws.com \
	--source-arn "${TOPIC_ARN_SUBMISSION}" \
	--source-account "${ACCOUNT_NUMBER}" || exit $?

echo $'\e[31mConfiguring SNS access policy so that submission lambda can publish to' ${TOPIC_NAME_SUBMITTED} $'...\e[0m'
cat > "${WIBL_BUILD_LOCATION}/lambda-sns-access-submitted.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowSNSAccessSubmitted",
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": [
                "${TOPIC_ARN_SUBMITTED}"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name "${SUBMISSION_LAMBDA_ROLE}" \
	--policy-name lambda-submission-sns-access-submitted \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-sns-access-submitted.json" || exit $?

########################
# Phase 6: Generate the conversion start HTTP lambda, which initiates conversion by publishing to the conversion topic
# Create the conversion start HTTP lambda
echo $'\e[31mGenerating conversion start HTTP lambda...\e[0m'
aws --region ${AWS_REGION} lambda create-function \
  --function-name ${CONVERSION_START_LAMBDA} \
  --no-cli-pager \
	--role arn:aws:iam::${ACCOUNT_NUMBER}:role/${CONVERSION_START_LAMBDA_ROLE} \
	--runtime python${PYTHONVERSION} \
  --timeout ${LAMBDA_TIMEOUT} \
  --memory-size ${LAMBDA_MEMORY} \
	--handler wibl.upload.cloud.aws.lambda_function.lambda_handler \
	--zip-file fileb://${WIBL_PACKAGE} \
	--architectures ${ARCHITECTURE} \
	--layers ${NUMPY_LAYER_NAME} \
	--vpc-config "SubnetIds=${LAMBDA_SUBNETS},SecurityGroupIds=${LAMBDA_SECURITY_GROUP}" \
	--environment "Variables={NOTIFICATION_ARN=${TOPIC_ARN_CONVERSION},INCOMING_BUCKET=${INCOMING_BUCKET}}" \
	| tee "${WIBL_BUILD_LOCATION}/create_lambda_conversion_start.json"

echo $'\e[31mConfiguring S3 access policy so that conversion start lambda can access S3 incoming bucket...\e[0m'
cat > "${WIBL_BUILD_LOCATION}/lambda-s3-access-incoming.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowS3AccessAll",
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::${INCOMING_BUCKET}",
                "arn:aws:s3:::${INCOMING_BUCKET}/*"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name "${CONVERSION_START_LAMBDA_ROLE}" \
	--policy-name lambda-s3-access-incoming \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-s3-access-incoming.json" || exit $?

echo $'\e[31mConfiguring SNS access policy so that conversion start lambda can publish to' ${TOPIC_NAME_CONVERSION} $'...\e[0m'
cat > "${WIBL_BUILD_LOCATION}/lambda-sns-access-conversion.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowSNSAccessConversion",
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": [
                "${TOPIC_ARN_CONVERSION}"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name "${CONVERSION_START_LAMBDA_ROLE}" \
	--policy-name lambda-conversion-sns-access-validation \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-sns-access-conversion.json" || exit $?

echo $'\e[31mAdd policy to conversion start lambda granting permissions to allow public access from function URL\e[0m'
aws --region ${AWS_REGION} lambda add-permission \
    --function-name ${CONVERSION_START_LAMBDA} \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type "NONE" \
    --statement-id url \
    | tee "${WIBL_BUILD_LOCATION}/url_invoke_lambda_conversion_start.json"

echo $'\e[31mCreate a URL endpoint for conversion start lambda...\e[0m'
aws lambda create-function-url-config \
    --function-name ${CONVERSION_START_LAMBDA} \
    --auth-type NONE \
    | tee "${WIBL_BUILD_LOCATION}/create_url_lambda_conversion_start.json"

CONVERSION_START_URL="$(cat ${WIBL_BUILD_LOCATION}/create_url_lambda_conversion_start.json | jq -r '.FunctionUrl')"
echo $'\e[31mConversion start lambda URL:' ${CONVERSION_START_URL} $'\e[0m'

########################
# Phase 7: Generate the visualization lambda
# Create ingress rule to allow NFS connections from the subnet (e.g., EFS mount point)
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 2049, "ToPort": 2049, "IpRanges": [{"CidrIp": "10.0.2.0/24"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_public_rule_efs.json

# Tag the NFS ingress rule with a name:
aws --region $AWS_REGION ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public_rule_efs.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-vizlambda-efs-mount-point'

# Create EFS volume for storing GEBCO data on
aws --region $AWS_REGION efs create-file-system \
  --creation-token wibl-vizlambda-efs \
  --no-encrypted \
  --no-backup \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags 'Key=Name,Value=wibl-vizlambda-efs' \
  | tee ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_file_system.json
WIBL_VIZ_LAMBDA_EFS_ID=$(cat ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_file_system.json | jq -r '.FileSystemId')

# To delete:
# aws --region $AWS_REGION efs delete-file-system \
#  --file-system-id $(cat ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_file_system.json | jq -r '.FileSystemId')

# Create mount target for EFS volume within our EC2 subnet (this is only needed temporarily while mounted from
# an EC2 instance to load data onto the volume)
aws --region $AWS_REGION efs create-mount-target \
  --file-system-id "$(cat ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_file_system.json | jq -r '.FileSystemId')" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public.txt)" \
  --security-groups "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_mount_target.json

echo $'\e[31mWaiting for 30 seconds to allow EFS-related security group rule to propagate ...\e[0m'
sleep 30

# To delete:
# aws --region $AWS_REGION efs delete-mount-target \
#  --mount-target-id $(cat ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_mount_target.json | jq -r '.MountTargetId')

# Create SSH key pair to access temporary EC2 instance
aws --region $AWS_REGION ec2 create-key-pair \
  --key-name wibl-tmp-key \
  --key-type rsa \
  --key-format pem \
  --query "KeyMaterial" \
  --output text > "${WIBL_BUILD_LOCATION}/wibl-tmp-key.pem"
chmod 400 "${WIBL_BUILD_LOCATION}/wibl-tmp-key.pem"

aws --region $AWS_REGION ec2 run-instances --image-id ami-0d9b5e9b3272cff13 --count 1 --instance-type t4g.nano \
	--key-name wibl-tmp-key \
	--associate-public-ip-address \
	--security-group-ids \
	  "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public.json | jq -r '.GroupId')" \
	--subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public.txt)" \
	| tee ${WIBL_BUILD_LOCATION}/run-wibl-test-ec2-instance.json

# Tag the instance with a name
aws --region $AWS_REGION ec2 create-tags \
  --resources "$(cat ${WIBL_BUILD_LOCATION}/run-wibl-test-ec2-instance.json| jq -r '.Instances[0].InstanceId')" \
  --tags 'Key=Name,Value=wibl-test'

echo $'\e[31mWaiting for 30 seconds to allow EC2 instance to start ...\e[0m'
sleep 30

TEST_INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids "$(cat ${WIBL_BUILD_LOCATION}/run-wibl-test-ec2-instance.json | jq -r '.Instances[0].InstanceId')" \
  | jq -r '.Reservations[0].Instances[0].PublicIpAddress')

# Connect to EC2 instance via SSH, mount EFS, download GEBCO data
ssh -o StrictHostKeyChecking=accept-new -i "${WIBL_BUILD_LOCATION}/wibl-tmp-key.pem" ec2-user@${TEST_INSTANCE_IP} <<-EOF
sudo dnf install -y wget amazon-efs-utils && \
  mkdir -p efs && \
  sudo mount -t efs "$WIBL_VIZ_LAMBDA_EFS_ID" efs && \
  cd efs && \
  sudo mkdir -p -m 777 gebco && \
  cd gebco && \
  echo 'Downloading GEBCO data to EFS volume (this will take several minutes)...' && \
  wget -q https://www.bodc.ac.uk/data/open_download/gebco/gebco_2023/zip/ -O gebco_2023.zip && \
  unzip gebco_2023.zip && \
  chmod 755 GEBCO_2023.nc && \
  rm gebco_2023.zip *.pdf && \
  cd && \
  sudo umount efs
EOF
test_aws_cmd_success $?

# Terminate EC2 instance
aws --region $AWS_REGION ec2 terminate-instances \
  --instance-ids "$(cat ${WIBL_BUILD_LOCATION}/run-wibl-test-ec2-instance.json | jq -r '.Instances[0].InstanceId')"

# Delete EC2 mount target so that we can later create one in the private subnet for use by lambdas
aws --region $AWS_REGION efs delete-mount-target \
  --mount-target-id "$(cat ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_mount_target.json | jq -r '.MountTargetId')"

# Phase 7b: Now we can create the container image for the lambda and create the lambda that mounts the EFS volume
#   created above.

# Create ECR repo
aws --region $AWS_REGION ecr create-repository \
  --repository-name wibl/vizlambda | tee ${WIBL_BUILD_LOCATION}/create_ecr_repository_vizlambda.json

# Delete: aws --region $AWS_REGION ecr delete-repository --repository-name wibl/vizlambda

# `docker login` to the repo so that we can push to it
aws --region $AWS_REGION ecr get-login-password | docker login \
  --username AWS \
  --password-stdin \
  "$(cat ${WIBL_BUILD_LOCATION}/create_ecr_repository_vizlambda.json | jq -r '.repository.repositoryUri')"
# If `docker login` is successful, you should see `Login Succeeded` printed to STDOUT.

# Build image and push to ECR repo
docker build --provenance=false -f ../../../Dockerfile.vizlambda -t wibl/vizlambda:latest ../../../
docker tag wibl/vizlambda:latest "${ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/wibl/vizlambda:latest"
docker push "${ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/wibl/vizlambda:latest" | tee "${WIBL_BUILD_LOCATION}/docker_push_vizlambda_to_ecr.txt"

# Create policy to allow lambdas to mount EFS read-only
# Define policy
cat > "${WIBL_BUILD_LOCATION}/lambda-efs-ro-policy.json" <<-HERE
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticfilesystem:ClientMount"
      ],
      "Resource": "*"
    }
  ]
}
HERE

# Create policy
aws --region ${AWS_REGION} iam create-policy \
  --policy-name 'Lambda-EFS-RO' \
  --policy-document file://"${WIBL_BUILD_LOCATION}/lambda-efs-ro-policy.json" \
  | tee "${WIBL_BUILD_LOCATION}/create_lambda-efs-ro-policy.json"

aws --region ${AWS_REGION} iam attach-role-policy \
  --role-name ${VIZ_LAMBDA_ROLE} \
  --policy-arn "$(cat ${WIBL_BUILD_LOCATION}/create_lambda-efs-ro-policy.json | jq -r '.Policy.Arn')" \
  | tee "${WIBL_BUILD_LOCATION}/attach_role_policy_lambda_efs_ro_viz.json"

# Create mount target and access point to later be used by lambda
aws --region $AWS_REGION efs create-mount-target \
  --file-system-id "$(cat ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_file_system.json | jq -r '.FileSystemId')" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-groups "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_mount_target_private.json

aws --region ${AWS_REGION} efs create-access-point \
  --file-system-id "$(cat ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_file_system.json | jq -r '.FileSystemId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_access_point.json
VIZ_LAMBDA_EFS_AP_ARN=$(cat ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_access_point.json | jq -r '.AccessPointArn')

# Create the vizualization lambda which mounts the vizlambda EFS volume to provide access to GEBCO data
echo $'\e[31mGenerating vizualization lambda...\e[0m'
aws --region ${AWS_REGION} lambda create-function \
  --function-name ${VIZ_LAMBDA} \
  --no-cli-pager \
	--role arn:aws:iam::${ACCOUNT_NUMBER}:role/${VIZ_LAMBDA_ROLE} \
  --timeout ${LAMBDA_TIMEOUT} \
  --memory-size ${LAMBDA_MEMORY} \
	--package-type Image \
	--code ImageUri="${ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/wibl/vizlambda:latest" \
	--architectures ${ARCHITECTURE} \
	--file-system-configs "Arn=${VIZ_LAMBDA_EFS_AP_ARN},LocalMountPath=/mnt/efs0" \
	--vpc-config "SubnetIds=${LAMBDA_SUBNETS},SecurityGroupIds=${LAMBDA_SECURITY_GROUP}" \
	--environment "Variables={WIBL_GEBCO_PATH=/mnt/efs0/gebco/GEBCO_2023.nc,DEST_BUCKET=${VIZ_BUCKET},STAGING_BUCKET=${STAGING_BUCKET},MANAGEMENT_URL=${MANAGEMENT_URL}}" \
	| tee "${WIBL_BUILD_LOCATION}/create_lambda_viz.json"

# To update function (i.e., after new image has been pushed), use update-function-code:
# aws --region ${AWS_REGION} lambda update-function-code \
#   --function-name ${VIZ_LAMBDA} \
#   --image-uri "${ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/wibl/vizlambda:latest" \
#   | tee "${WIBL_BUILD_LOCATION}/update_lambda_viz.json"

echo $'\e[31mConfiguring S3 access policy so that viz lambda can access S3 staging and viz buckets...\e[0m'
cat > "${WIBL_BUILD_LOCATION}/lambda-s3-access-viz.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowS3AccessAll",
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::${STAGING_BUCKET}",
                "arn:aws:s3:::${STAGING_BUCKET}/*",
                "arn:aws:s3:::${VIZ_BUCKET}",
                "arn:aws:s3:::${VIZ_BUCKET}/*"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name "${VIZ_LAMBDA_ROLE}" \
	--policy-name lambda-s3-access-viz \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-s3-access-viz.json" || exit $?

########################
# Phase 8: Configure SNS subscriptions for lambdas
#

# Optional: If you want to automatically trigger the conversion lambda on upload to the incoming S3 bucket
# (rather than using the conversion-start lambda to initiate WIBL file conversion), do the following:
#   1. Create incoming bucket policy to notify the conversion topic; and
#   2. Update conversion topic access policy to allow S3 to send notifications from our incoming bucket
# Create incoming bucket policy to notify the conversion topic when files needing conversion
echo $'\e[31mAdding bucket SNS notification to' ${INCOMING_BUCKET} $'...\e[0m'
UUID=$(uuidgen)
cat > "${WIBL_BUILD_LOCATION}/conversion-notification-cfg.json" <<-HERE
{
    "TopicConfigurations": [
        {
            "Id": "${UUID}",
            "TopicArn": "${TOPIC_ARN_CONVERSION}",
            "Events": [
                "s3:ObjectCreated:Put",
                "s3:ObjectCreated:CompleteMultipartUpload"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} s3api put-bucket-notification-configuration \
  --skip-destination-validation \
	--bucket "${INCOMING_BUCKET}" \
	--notification-configuration file://"${WIBL_BUILD_LOCATION}/conversion-notification-cfg.json" || exit $?

# Update conversion topic access policy to allow S3 to send notifications from our incoming bucket
UUID=$(uuidgen)
cat > "${WIBL_BUILD_LOCATION}/conversion-topic-access-policy.json" <<-HERE
{
    "Version": "2012-10-17",
    "Id": "${UUID}",
    "Statement": [
        {
            "Sid": "S3 SNS topic policy",
            "Effect": "Allow",
            "Principal": {
                "Service": "s3.amazonaws.com"
            },
            "Action": [
                "SNS:Publish"
            ],
            "Resource": "${TOPIC_ARN_CONVERSION}",
            "Condition": {
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:s3:::${INCOMING_BUCKET}"
                },
                "StringEquals": {
                    "aws:SourceAccount": "${ACCOUNT_NUMBER}"
                }
            }
        }
    ]
}
HERE
aws --region ${AWS_REGION} sns set-topic-attributes \
  --topic-arn "${TOPIC_ARN_CONVERSION}" \
  --attribute-name Policy \
  --attribute-value file://"${WIBL_BUILD_LOCATION}/conversion-topic-access-policy.json"
# End, optional configuration for automatically triggering conversion lambda on upload to incoming S3 bucket.

# Create subscription to conversion topic
echo $'\e[31mAdding subscription for conversion lambda...\e[0m'
aws --region ${AWS_REGION} sns subscribe \
  --protocol lambda \
  --topic-arn "${TOPIC_ARN_CONVERSION}" \
  --notification-endpoint "arn:aws:lambda:${AWS_REGION}:${ACCOUNT_NUMBER}:function:${CONVERSION_LAMBDA}" \
  | tee "${WIBL_BUILD_LOCATION}/create_sns_sub_lambda_conversion.json"

# Create subscription to validation topic
echo $'\e[31mAdding subscription for validation lambda...\e[0m'
aws --region ${AWS_REGION} sns subscribe \
  --protocol lambda \
  --topic-arn "${TOPIC_ARN_VALIDATION}" \
  --notification-endpoint "arn:aws:lambda:${AWS_REGION}:${ACCOUNT_NUMBER}:function:${VALIDATION_LAMBDA}" \
  | tee "${WIBL_BUILD_LOCATION}/create_sns_sub_lambda_validation.json"

# Create subscription to submission topic
echo $'\e[31mAdding subscription for submission lambda...\e[0m'
aws --region ${AWS_REGION} sns subscribe \
  --protocol lambda \
  --topic-arn "${TOPIC_ARN_SUBMISSION}" \
  --notification-endpoint "arn:aws:lambda:${AWS_REGION}:${ACCOUNT_NUMBER}:function:${SUBMISSION_LAMBDA}" \
  | tee "${WIBL_BUILD_LOCATION}/create_sns_sub_lambda_submission.json"
