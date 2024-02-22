#!/bin/bash
#
# This script creates an optional lambda for generating maps of soundings from one or more GeoJSON-converted WIBL
# data files stored in ${STAGING_BUCKET}.

set -eu -o pipefail

source configuration-parameters.sh

LAMBDA_SUBNET_1="$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private_lambda.txt)"
LAMBDA_SUBNETS="${LAMBDA_SUBNET_1}"
LAMBDA_SECURITY_GROUP="$(cat ${WIBL_BUILD_LOCATION}/create_security_group_lambda.json | jq -r '.GroupId')"

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
docker build -f ../../../Dockerfile.vizlambda -t wibl/vizlambda:latest ../../../
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
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private_lambda.txt)" \
  --security-groups "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_lambda.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vizlambda_efs_mount_target_lambda.json

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
