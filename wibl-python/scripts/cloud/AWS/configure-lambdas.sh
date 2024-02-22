#!/bin/bash
#
# This sets up the permissions, triggers, and lambdas required for the WIBL code to run in
# AWS.  If, of course, you have part of this set up already, then you're likely to encounter
# difficulties.  Probably best to clean up in the console first, then try again.

set -eu -o pipefail

source configuration-parameters.sh

# Specify the URL for the management console component.  Leave empty if you don't want
# to run the management console.
# TODO: This would probably be better generated automatically based on the provider ID
# and some sensible default for URL of the server.
# TODO: Having this set to a value rather than being empty should be the trigger to
# package and deploy the management server container.
MANAGEMENT_URL=http://"$(cat ${WIBL_BUILD_LOCATION}/create_elb.json | jq -r '.LoadBalancers[0].DNSName')"/

#####################
## Phase 0: Setup & configure subnet and security group for lambdas
##
echo $'\e[31mCreating private subnet, routes, and security group for lambdas ...\e[0m'
aws --region $AWS_REGION ec2 create-subnet --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --availability-zone us-east-2b \
  --cidr-block 10.0.3.0/24 --query Subnet.SubnetId --output text \
  | tee "${WIBL_BUILD_LOCATION}/create_subnet_private_lambda.txt"
# Tag lambda subnets with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private_lambda.txt)" \
  --tags 'Key=Name,Value=wibl-private-lambda'
# Create a routing table for private subnets to the VPC
aws --region $AWS_REGION ec2 create-route-table --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --query RouteTable.RouteTableId --output text | tee "${WIBL_BUILD_LOCATION}/create_route_table_lambda.txt"
# Tag the route table with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_lambda.txt)" \
  --tags 'Key=Name,Value=wibl-private-lambda'
# Associate the custom routing table with the private subnet:
aws --region $AWS_REGION ec2 associate-route-table \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private_lambda.txt)" \
  --route-table-id "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_lambda.txt)"
# Create security group to give us control over ingress/egress
aws --region $AWS_REGION ec2 create-security-group \
	--group-name wibl-lambda \
	--vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
	--description "Security Group for WIBL lambdas" \
	| tee "${WIBL_BUILD_LOCATION}/create_security_group_lambda.json"
# Tag the security group with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_lambda.json | jq -r '.GroupId')" \
  --tags 'Key=Name,Value=wibl-lambda'

# Create an ingress rule to allow anything running in the same VPC (e.g., SNS VPC, ECS, lambdas, EC2, ELB, EFS) to access other
# services in the subnet via any port
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_lambda.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 0, "ToPort": 65535, "IpRanges": [{"CidrIp": "10.0.0.0/16"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_lambda_rules_vpc-svc.json
# Tag the lambda ingress rule with name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_lambda_rules_vpc-svc.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-lambda-vpc-svc'

# Create ingress rule to allow all connections from AWS_REGION_S3_PL (region-specific S3 CIDR blocks)
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_lambda.json | jq -r '.GroupId')" \
  --ip-permissions "[{\"IpProtocol\": \"tcp\", \"FromPort\": 0, \"ToPort\": 65535, \"PrefixListIds\": [{\"Description\": \"S3\", \"PrefixListId\": \"${AWS_REGION_S3_PL}\"}]}]" \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_lambda_rule_s3.json
# Tag the S3 ingress rule with name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_lambda_rule_s3.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-lambda-s3'

LAMBDA_SUBNET_1="$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private_lambda.txt)"
LAMBDA_SUBNETS="${LAMBDA_SUBNET_1}"
LAMBDA_SECURITY_GROUP="$(cat ${WIBL_BUILD_LOCATION}/create_security_group_lambda.json | jq -r '.GroupId')"

# Update route table in lambda subnet to route to internet gateway
aws --region ${AWS_REGION} ec2 create-route \
  --route-table-id "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_lambda.txt)" \
  --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$(cat ${WIBL_BUILD_LOCATION}/create_nat_gateway_lambda.json | jq -r '.NatGateway.NatGatewayId')"

echo $'\e[31mCreating S3 and SNS service gateways for lambdas ...\e[0m'
# Create service endpoint so that lambdas running in the VPC can access S3
aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --service-name "com.amazonaws.${AWS_REGION}.s3" \
  --route-table-ids "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_lambda.txt)" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_s3_lambda_subnet.json

## Create service endpoint so that lambdas running in the VPC can access SNS
echo $'\e[31mCreating SNS VPC endpoint for lambdas ...\e[0m'
aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --service-name "com.amazonaws.${AWS_REGION}.sns" \
  --vpc-endpoint-type Interface \
  --subnet-ids ${LAMBDA_SUBNETS} \
  --security-group-ids ${LAMBDA_SECURITY_GROUP} \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_sns_lambda_subnet.json

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
	--statement-id snsinvoke \
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
echo $'\e[31mGenerating validation lambda...\e[0m'
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
	--environment "Variables={NOTIFICATION_ARN=${TOPIC_ARN_SUBMISSION},PROVIDER_ID=${DCDB_PROVIDER_ID},STAGING_BUCKET=${STAGING_BUCKET},DEST_BUCKET=${STAGING_BUCKET},MANAGEMENT_URL=${MANAGEMENT_URL}}" \
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
	--statement-id snsinvoke \
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
	--environment "Variables={NOTIFICATION_ARN=${TOPIC_ARN_SUBMITTED},PROVIDER_ID=${DCDB_PROVIDER_ID},PROVIDER_AUTH=${AUTHKEY},STAGING_BUCKET=${STAGING_BUCKET},DEST_BUCKET=${STAGING_BUCKET},UPLOAD_POINT=${DCDB_UPLOAD_URL},MANAGEMENT_URL=${MANAGEMENT_URL}}" \
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
	--statement-id snsinvoke \
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
	--environment "Variables={NOTIFICATION_ARN=${TOPIC_ARN_CONVERSION},INCOMING_BUCKET=${INCOMING_BUCKET},DEST_BUCKET=notused}" \
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
	--policy-name lambda-conversion-sns-access-conversion \
	--policy-document file://"${WIBL_BUILD_LOCATION}/lambda-sns-access-conversion.json" || exit $?

echo $'\e[31mAdd permission to conversion start lambda granting permissions to allow public access from function URL\e[0m'
aws --region ${AWS_REGION} lambda add-permission \
    --function-name ${CONVERSION_START_LAMBDA} \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type "NONE" \
    --statement-id url \
    | tee "${WIBL_BUILD_LOCATION}/url_invoke_lambda_conversion_start.json"

echo $'\e[31mCreate a URL endpoint for conversion start lambda...\e[0m'
aws --region ${AWS_REGION} lambda create-function-url-config \
    --function-name ${CONVERSION_START_LAMBDA} \
    --auth-type NONE \
    | tee "${WIBL_BUILD_LOCATION}/create_url_lambda_conversion_start.json"

CONVERSION_START_URL="$(cat ${WIBL_BUILD_LOCATION}/create_url_lambda_conversion_start.json | jq -r '.FunctionUrl')"
echo $'\e[31mConversion start lambda URL:' ${CONVERSION_START_URL} $'\e[0m'

########################
# Phase 7: Configure SNS subscriptions for lambdas
#

# Optional: If you want to automatically trigger the conversion lambda on upload to the incoming S3 bucket
# (rather than using the conversion-start lambda to initiate WIBL file conversion), do the following:
#   1. Create incoming bucket policy to notify the conversion topic; and
#   2. Update conversion topic access policy to allow S3 to send notifications from our incoming bucket
# Create incoming bucket policy to notify the conversion topic when files needing conversion
#echo $'\e[31mAdding bucket SNS notification to' ${INCOMING_BUCKET} $'...\e[0m'
#UUID=$(uuidgen)
#cat > "${WIBL_BUILD_LOCATION}/conversion-notification-cfg.json" <<-HERE
#{
#    "TopicConfigurations": [
#        {
#            "Id": "${UUID}",
#            "TopicArn": "${TOPIC_ARN_CONVERSION}",
#            "Events": [
#                "s3:ObjectCreated:Put",
#                "s3:ObjectCreated:CompleteMultipartUpload"
#            ]
#        }
#    ]
#}
#HERE
#aws --region ${AWS_REGION} s3api put-bucket-notification-configuration \
#  --skip-destination-validation \
#	--bucket "${INCOMING_BUCKET}" \
#	--notification-configuration file://"${WIBL_BUILD_LOCATION}/conversion-notification-cfg.json" || exit $?
#
## Update conversion topic access policy to allow S3 to send notifications from our incoming bucket
#UUID=$(uuidgen)
#cat > "${WIBL_BUILD_LOCATION}/conversion-topic-access-policy.json" <<-HERE
#{
#    "Version": "2012-10-17",
#    "Id": "${UUID}",
#    "Statement": [
#        {
#            "Sid": "S3 SNS topic policy",
#            "Effect": "Allow",
#            "Principal": {
#                "Service": "s3.amazonaws.com"
#            },
#            "Action": [
#                "SNS:Publish"
#            ],
#            "Resource": "${TOPIC_ARN_CONVERSION}",
#            "Condition": {
#                "ArnLike": {
#                    "aws:SourceArn": "arn:aws:s3:::${INCOMING_BUCKET}"
#                },
#                "StringEquals": {
#                    "aws:SourceAccount": "${ACCOUNT_NUMBER}"
#                }
#            }
#        }
#    ]
#}
#HERE
#aws --region ${AWS_REGION} sns set-topic-attributes \
#  --topic-arn "${TOPIC_ARN_CONVERSION}" \
#  --attribute-name Policy \
#  --attribute-value file://"${WIBL_BUILD_LOCATION}/conversion-topic-access-policy.json"
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
