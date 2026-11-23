#!/bin/bash

# IMPORTANT: This file and all other scripts other than "build-lambda.sh" are apart of the deprecated scripting
# build approach. The intended build method is to use Terraform. Follow the instructions in the README.md located in the
# Terraform folder.

# This script sets up the WIBL Cloud Manager service on AWS using ECS with Fargate as a capacity provider
# (rather than EC2).
# NOTE: This configuration uses VPC endpoints to provide access to AWS services from within a private VPC.
#       It is intended for reference purposes only as the presence of lambdas in the private VPC
#       subnet requires the use of a NAT gateway (required to provide Internet access for WIBL
#       file submission), which obviates the need for EPC endpints (and costs less when you have
#       more than 4 endpoints; the below configuration has 8)

source configuration-parameters.sh

####################
# Phase 0: Setup ECR container registry

# Create repo
aws --region $AWS_REGION ecr create-repository \
  --repository-name wibl/manager | tee ${WIBL_BUILD_LOCATION}/create_ecr_repository.json
```

# `docker login` to the repo so that we can push to it
aws --region $AWS_REGION ecr get-login-password | docker login \
  --username AWS \
  --password-stdin \
  $(cat ${WIBL_BUILD_LOCATION}/create_ecr_repository.json | jq -r '.repository.repositoryUri')
# If `docker login` is successful, you should see `Login Succeeded` printed to STDOUT.

# Build image and push to ECR repo
docker build -t wibl/manager ../../../wibl-manager/
docker tag wibl/manager:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wibl/manager:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wibl/manager:latest | tee "${WIBL_BUILD_LOCATION}/docker_push_to_ecr.txt"

####################
# Phase 1: Create VPC, private subnet with route table, and security group for ECS Fargate deployment of WIBL
#          manager.

# Create a VPC with a 10.0.0.0/16 address block
aws --region $AWS_REGION ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --query Vpc.VpcId --output text | tee "${WIBL_BUILD_LOCATION}/create_vpc.txt"

# Update enable DNS hostnames on VPC
aws --region $AWS_REGION ec2 modify-vpc-attribute --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --enable-dns-hostnames

# Create a subnet with a 10.0.0.0/24 CIDR block, this will be the private subnet
aws --region $AWS_REGION ec2 create-subnet --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --cidr-block 10.0.0.0/24 --query Subnet.SubnetId --output text \
  | tee "${WIBL_BUILD_LOCATION}/create_subnet_private.txt"

# Tag the subnet with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --tags 'Key=Name,Value=wibl-private-ecs'

# Create a routing table for private subnet to the VPC
aws --region $AWS_REGION ec2 create-route-table --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --query RouteTable.RouteTableId --output text | tee "${WIBL_BUILD_LOCATION}/create_route_table_private.txt"

# Tag the route table with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_private.txt)" \
  --tags 'Key=Name,Value=wibl-private-ecs'

# Associate the custom routing table with the private subnet:
aws --region $AWS_REGION ec2 associate-route-table \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --route-table-id "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_private.txt)"

# Create security group to give us control over ingress/egress
aws --region $AWS_REGION ec2 create-security-group \
	--group-name wibl-mgr-ecs-fargate \
	--vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
	--description "Security Group for WIBL lambdas and WIBL Manager on ECS Fargate" \
	| tee "${WIBL_BUILD_LOCATION}/create_security_group_private.json"

# Tag the security group with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --tags 'Key=Name,Value=wibl-mgr-ecs-fargate'

# Create ingress rule to the load balancer to access the manager via port 8000
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 8000, "ToPort": 8000, "IpRanges": [{"CidrIp": "10.0.0.0/24"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_lambda.json

# Tag the load balancer ingress rule with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_lambda.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-elb'

####################
# Phase 2: Create VPC service endpoints to allowing ECS to access various AWS services (why don't the just bake this in
#          to their VPC subnets?)

# First, create an ingress rules to allow anything running in the same VPC (e.g., ECS, lambdas, EC2) to access other
# services in the subnet via HTTPS and HTTPS (HTTPS allows access to VPC endpoints; HTTP rule only needed for accessing
# WIBL manager via ELB)
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "10.0.0.0/24"}]}, {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "10.0.0.0/24"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_private_rules_http_https.json

# Tag the HTTP/HTTPS ingress rules with names
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rules_http_https.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-http'
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rules_http_https.json | jq -r '.SecurityGroupRules[1].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-vpc-svc'

# Create service endpoint so that things running in the VPC can access S3
aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --service-name "com.amazonaws.${AWS_REGION}.s3" \
  --route-table-ids "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_private.txt)" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_s3.json

# Create service endpoint so that things running in the VPC can access SNS
aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --vpc-endpoint-type Interface \
  --service-name "com.amazonaws.${AWS_REGION}.sns" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-group-ids "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_sns.json

# Create service endpoints for ECR
aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --vpc-endpoint-type Interface \
  --service-name "com.amazonaws.${AWS_REGION}.ecr.dkr" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-group-ids "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_ecr_dkr.json

aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --vpc-endpoint-type Interface \
  --service-name "com.amazonaws.${AWS_REGION}.ecr.api" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-group-ids "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_ecr_api.json

# Create service endpoints for ECS:
aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --vpc-endpoint-type Interface \
  --service-name "com.amazonaws.${AWS_REGION}.ecs-agent" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-group-ids "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_ecs_agent.json

aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --vpc-endpoint-type Interface \
  --service-name "com.amazonaws.${AWS_REGION}.ecs-telemetry" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-group-ids "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_ecs_telemetry.json

aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --vpc-endpoint-type Interface \
  --service-name "com.amazonaws.${AWS_REGION}.ecs" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-group-ids "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_ecs.json

# Create service endpoint for CloudWatch
aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --vpc-endpoint-type Interface \
  --service-name "com.amazonaws.${AWS_REGION}.logs" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-group-ids "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_logs.json

# Create service endpoint for EFS
aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --vpc-endpoint-type Interface \
  --service-name "com.amazonaws.${AWS_REGION}.elasticfilesystem" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-group-ids "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_efs.json

####################
# Phase 3: Create EFS volume and mount point for private subnet

# Create the volume
# Note: Make sure your account has the `AmazonElasticFileSystemFullAccess` permissions policy
# attached to it.
aws --region $AWS_REGION efs create-file-system \
  --creation-token wibl-manager-ecs-task-efs \
  --encrypted \
  --backup \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags 'Key=Name,Value=wibl-manager-ecs-task-efs' \
  | tee ${WIBL_BUILD_LOCATION}/create_efs_file_system.json

# Create mount target for EFS volume within our VPC subnet
aws --region $AWS_REGION efs create-mount-target \
  --file-system-id "$(cat ${WIBL_BUILD_LOCATION}/create_efs_file_system.json | jq -r '.FileSystemId')" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-groups "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_efs_mount_target.json

# Create ingress rule to allow NFS connections from the subnet (e.g., EFS mount point)
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 2049, "ToPort": 2049, "IpRanges": [{"CidrIp": "10.0.0.0/24"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_efs.json

# Tag the NFS ingress rule with a name:
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_efs.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-efs-mount-point'

####################
# Phase 4: Setup ECS cluster and task definition

# Create cluster
aws --region $AWS_REGION ecs create-cluster \
	--cluster-name wibl-manager-ecs \
	--capacity-providers FARGATE | tee ${WIBL_BUILD_LOCATION}/create_ecs_cluster.json

# Setup and attach `ecsInstanceRole`
# Create `ecsInstanceRole`
aws --region $AWS_REGION iam create-role \
	--role-name ecsTaskExecutionRole \
	--assume-role-policy-document file://manager/input/task-execution-assume-role.json \
	| tee ${WIBL_BUILD_LOCATION}/create_task_exec_role.json
# If the role already exists, you will get an error to the following:
#   An error occurred (EntityAlreadyExists) when calling the CreateRole operation: Role with name ecsTaskExecutionRole already exists.
# This is okay and can be ignored.

# Next, attach role policy:
aws --region $AWS_REGION iam attach-role-policy \
	--role-name ecsTaskExecutionRole \
	--policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
	| tee ${WIBL_BUILD_LOCATION}/attach_role_policy.json

# Associate CloudWatch policy to `ecsInstanceRole` to allow ECS tasks to send logs to CloudWatch
# Create policy
aws --region $AWS_REGION iam create-policy \
  --policy-name 'ECS-CloudWatchLogs' \
  --policy-document file://manager/input/ecs-cloudwatch-policy.json | tee ${WIBL_BUILD_LOCATION}/create_log_policy.json
# If the role already exists, you will get an error to the following:
#   An error occurred (EntityAlreadyExists) when calling the CreatePolicy operation: A policy called ECS-CloudWatchLogs
#   already exists. Duplicate names are not allowed.
# This is okay and can be ignored.

# Attach policy to ECS role
aws --region $AWS_REGION iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn "$(cat ${WIBL_BUILD_LOCATION}/create_log_policy.json| jq -r '.Policy.Arn')" \
  | tee ${WIBL_BUILD_LOCATION}/attach_role_policy_cloudwatch.json

# Create application load balancer so that lambdas can find our WIBL manager service
# Create load balancer
aws elbv2 create-load-balancer --name wibl-manager-ecs-elb --type network \
  --subnets "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --scheme internal \
  | tee ${WIBL_BUILD_LOCATION}/create_elb.json
# Note: If you want to make the manager accessible over the Internet, change the `scheme` to `internet-facing`.

# Create target group to associate load balancer listeners to ECS Fargate elastic IP addresses
aws elbv2 create-target-group --name wibl-manager-ecs-elb-tg \
  --protocol TCP --port 8000 \
  --target-type ip \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  | tee ${WIBL_BUILD_LOCATION}/create_elb_target_group.json

# Create ELB listener
aws elbv2 create-listener \
  --load-balancer-arn "$(cat ${WIBL_BUILD_LOCATION}/create_elb.json | jq -r '.LoadBalancers[0].LoadBalancerArn')" \
  --protocol TCP \
  --port 80 \
  --default-actions \
    Type=forward,TargetGroupArn="$(cat ${WIBL_BUILD_LOCATION}/create_elb_target_group.json | jq -r '.TargetGroups[0].TargetGroupArn')" \
  | tee ${WIBL_BUILD_LOCATION}/create_elb_listener.json

# Using image pushed to ECR above, create task definition
AWS_EFS_FS_ID=$(cat ${WIBL_BUILD_LOCATION}/create_efs_file_system.json | jq -r '.FileSystemId')
sed "s|REPLACEME_AWS_ACCOUNT_ID|$ACCOUNT_NUMBER|g" manager/input/manager-task-definition.proto | \
  sed "s|REPLACEME_AWS_EFS_FS_ID|$AWS_EFS_FS_ID|g" | \
  sed "s|REPLECEME_AWS_REGION|$AWS_REGION|g" > ${WIBL_BUILD_LOCATION}/manager-task-definition.json
aws --region $AWS_REGION ecs register-task-definition \
	--cli-input-json file://${WIBL_BUILD_LOCATION}/manager-task-definition.json | \
	tee ${WIBL_BUILD_LOCATION}/create_task_definition.json

# Create an ECS service in our cluster to launch one or more tasks based on our task definition
SECURITY_GROUP_ID="$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')"
SUBNETS="$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)"
ELB_TARGET_GROUP_ARN="$(cat ${WIBL_BUILD_LOCATION}/create_elb_target_group.json | jq -r '.TargetGroups[0].TargetGroupArn')"
aws --region $AWS_REGION ecs create-service \
	--cluster wibl-manager-ecs \
	--service-name wibl-manager-ecs-svc \
	--task-definition wibl-manager-ecs-task \
	--desired-count 1 \
	--load-balancers "targetGroupArn=${ELB_TARGET_GROUP_ARN},containerName=wibl-manager,containerPort=8000" \
	--network-configuration "awsvpcConfiguration={subnets=[ ${SUBNETS} ],securityGroups=[ ${SECURITY_GROUP_ID} ]}" \
	--launch-type "FARGATE" | tee ${WIBL_BUILD_LOCATION}/create_ecs_service.json
