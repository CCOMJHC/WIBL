#!/bin/bash
#
# This script sets up the WIBL Cloud Manager service on AWS using ECS with Fargate as a capacity provider
# (rather than EC2).

set -eu -o pipefail

source configuration-parameters.sh

####################
# Phase 0: Setup ECR container registry repos and build and push container images

# Create manager repo
aws --region $AWS_REGION ecr create-repository \
  --repository-name wibl/manager | tee ${WIBL_BUILD_LOCATION}/create_ecr_repository.json

# Create frontend repo
aws --region $AWS_REGION ecr create-repository \
  --repository-name wibl/frontend | tee ${WIBL_BUILD_LOCATION}/create_ecr_repository_frontend.json

# Build manager image and push to ECR repo
./build-manager.sh

# Build frontend image and push to ECR repo
./build-frontend.sh

####################
# Phase 1: Create VPC, public and private subnets and route tables, as well as security groups for ECS Fargate
#          deployment of wibl-manager and wibl-frontend.

# Create a VPC with a 10.0.0.0/16 address block
aws --region $AWS_REGION ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --query Vpc.VpcId --output text | tee "${WIBL_BUILD_LOCATION}/create_vpc.txt"

# Update enable DNS hostnames on VPC
aws --region $AWS_REGION ec2 modify-vpc-attribute --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --enable-dns-hostnames

# Create public subnets
aws --region $AWS_REGION ec2 create-subnet --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --availability-zone us-east-2b \
  --cidr-block 10.0.2.0/24 \
	--query Subnet.SubnetId --output text | tee ${WIBL_BUILD_LOCATION}/create_subnet_public.txt
aws --region $AWS_REGION ec2 create-subnet --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --availability-zone us-east-2a \
  --cidr-block 10.0.4.0/24 \
	--query Subnet.SubnetId --output text | tee ${WIBL_BUILD_LOCATION}/create_subnet_public_2.txt

# Tag the subnets with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public.txt)" \
  --tags 'Key=Name,Value=wibl-public'
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public_2.txt)" \
  --tags 'Key=Name,Value=wibl-public2'

echo $'\e[31mCreating NAT gateway for lambdas and ECS ...\e[0m'
# Create NAT gateway so the lambdas can access the Internet for submission to DCDB, and ECS can access ECR.
# Create Elastic IP to associate with NAT gateway
aws --region ${AWS_REGION} ec2 allocate-address | tee "${WIBL_BUILD_LOCATION}/alloc_nat_gw_eip_lambda.json"

## Create NAT gateway
aws --region ${AWS_REGION} ec2 create-nat-gateway \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public.txt)" \
  --connectivity-type public \
  --allocation-id "$(cat ${WIBL_BUILD_LOCATION}/alloc_nat_gw_eip_lambda.json | jq -r '.AllocationId')" \
  | tee "${WIBL_BUILD_LOCATION}/create_nat_gateway_lambda.json"

echo $'\e[31mWaiting for 10 seconds to allow NAT gateway to propagate ...\e[0m'
sleep 10

# Tag NAT gateway with lambda
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_nat_gateway_lambda.json | jq -r '.NatGateway.NatGatewayId')" \
  --tags 'Key=Name,Value=wibl-lambda-nat'

# Create a routing table for public subnet of the VPC
aws --region $AWS_REGION ec2 create-route-table --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --query RouteTable.RouteTableId --output text | tee ${WIBL_BUILD_LOCATION}/create_route_table_public.txt

# Tag the route table with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_public.txt)" \
  --tags 'Key=Name,Value=wibl-public'

# Associate the custom routing table with the public subnets
aws --region $AWS_REGION ec2 associate-route-table \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public.txt)" \
  --route-table-id "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_public.txt)"
aws --region $AWS_REGION ec2 associate-route-table \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public_2.txt)" \
  --route-table-id "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_public.txt)"

# Create Internet gateway
aws --region $AWS_REGION ec2 create-internet-gateway --query InternetGateway.InternetGatewayId \
  --output text | tee ${WIBL_BUILD_LOCATION}/create_internet_gateway.txt

# Tag Internet gateway with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_internet_gateway.txt)" \
  --tags 'Key=Name,Value=wibl-public'

# Attach the Internet gateway to the VPC
aws --region $AWS_REGION ec2 attach-internet-gateway --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --internet-gateway-id "$(cat ${WIBL_BUILD_LOCATION}/create_internet_gateway.txt)"

# Create route pointing traffic to the Internet gateway
aws --region $AWS_REGION ec2 create-route \
  --route-table-id "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_public.txt)" \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id "$(cat ${WIBL_BUILD_LOCATION}/create_internet_gateway.txt)"

# Create security group to give us control over ingress/egress:
aws --region $AWS_REGION ec2 create-security-group \
	--group-name wibl-mgr-public \
	--vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
	--description "Security Group for use in public subnet of WIBL manager app" \
	| tee ${WIBL_BUILD_LOCATION}/create_security_group_public.json

# Tag the security group with a name:
aws --region $AWS_REGION ec2 create-tags \
  --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public.json | jq -r '.GroupId')" \
  --tags 'Key=Name,Value=wibl-mgr-public'

# Create PUBLIC ingress rule to the wibl-frontend load balancer to access the frontend via ports 80 and 443
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}, {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_public_rule_http.json

# Create private subnets (we need two because the frontend will be using an application load balancer, which requires >1)
aws --region $AWS_REGION ec2 create-subnet --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --availability-zone us-east-2b \
  --cidr-block 10.0.0.0/24 --query Subnet.SubnetId --output text \
  | tee "${WIBL_BUILD_LOCATION}/create_subnet_private.txt"
#aws --region $AWS_REGION ec2 create-subnet --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
#  --availability-zone us-east-2a \
#  --cidr-block 10.0.1.0/24 --query Subnet.SubnetId --output text \
#  | tee "${WIBL_BUILD_LOCATION}/create_subnet_private_2.txt"

# Tag private subnets with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --tags 'Key=Name,Value=wibl-private-ecs'
#aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private_2.txt)" \
#  --tags 'Key=Name,Value=wibl-private-ecs2'

# Create a routing table for private subnets to the VPC
aws --region $AWS_REGION ec2 create-route-table --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --query RouteTable.RouteTableId --output text | tee "${WIBL_BUILD_LOCATION}/create_route_table_private.txt"

# Tag the route table with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_private.txt)" \
  --tags 'Key=Name,Value=wibl-private-ecs'

# Associate the custom routing table with the private subnets:
aws --region $AWS_REGION ec2 associate-route-table \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --route-table-id "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_private.txt)"
#aws --region $AWS_REGION ec2 associate-route-table \
#  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private_2.txt)" \
#  --route-table-id "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_private.txt)"

# Update route table in private subnet to route to NAT gateway
aws --region ${AWS_REGION} ec2 create-route \
  --route-table-id "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_private.txt)" \
  --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$(cat ${WIBL_BUILD_LOCATION}/create_nat_gateway_lambda.json | jq -r '.NatGateway.NatGatewayId')"

# Create security group to give us control over ingress/egress
aws --region $AWS_REGION ec2 create-security-group \
	--group-name wibl-mgr-ecs-fargate \
	--vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
	--description "Security Group for WIBL Manager/Frontend on ECS Fargate" \
	| tee "${WIBL_BUILD_LOCATION}/create_security_group_private.json"

# Tag the security group with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --tags 'Key=Name,Value=wibl-mgr-ecs-fargate'

# Create ingress rule so that wibl-manager and wibl-frontend load balancers can access manager and frontend via port 8000
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 8000, "ToPort": 8000, "IpRanges": [{"CidrIp": "10.0.0.0/16"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_lambda.json

# Tag the load balancer ingress rules with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_lambda.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-elb'
#aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public_rule_allow_8000.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
#  --tags 'Key=Name,Value=wibl-frontend-elb'

# Create an ingress rules to allow anything running in the same VPC (e.g., ECS, lambdas, EC2) to access other
# services in the subnet via HTTPS and HTTPS (HTTPS allows access to VPC endpoints; HTTP rule only needed for accessing
# WIBL manager via ELB)
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "10.0.0.0/16"}]}, {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "10.0.0.0/16"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_private_rules_http_https.json

# Tag the HTTP/HTTPS ingress rules with names
aws --region ${AWS_REGION} ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rules_http_https.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-http'
aws --region ${AWS_REGION} ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rules_http_https.json | jq -r '.SecurityGroupRules[1].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-vpc-svc'

# Create service endpoint so that things running in the VPC can access S3
aws --region $AWS_REGION ec2 create-vpc-endpoint \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  --service-name "com.amazonaws.${AWS_REGION}.s3" \
  --route-table-ids "$(cat ${WIBL_BUILD_LOCATION}/create_route_table_private.txt)" \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=ecs-s3}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_vpc_endpoint_s3_ecs.json
# Create ingress rule to allow all connections from AWS_REGION_S3_PL (region-specific S3 CIDR blocks)
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --ip-permissions "[{\"IpProtocol\": \"tcp\", \"FromPort\": 0, \"ToPort\": 65535, \"PrefixListIds\": [{\"Description\": \"S3\", \"PrefixListId\": \"${AWS_REGION_S3_PL}\"}]}]" \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_s3.json
# Tag the S3 ingress rule with name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_s3.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-ecs-s3'

####################
# Phase 3: Create EFS volumes and mount points for private subnet

# Create the volumes
# Note: Make sure your account has the `AmazonElasticFileSystemFullAccess` permissions policy
# attached to it.
# wibl-manager volume
aws --region $AWS_REGION efs create-file-system \
  --creation-token wibl-manager-ecs-task-efs \
  --encrypted \
  --backup \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags 'Key=Name,Value=wibl-manager-ecs-task-efs' \
  | tee ${WIBL_BUILD_LOCATION}/create_efs_file_system.json
# wibl-frontend volume
aws --region $AWS_REGION efs create-file-system \
  --creation-token wibl-frontend-ecs-task-efs \
  --encrypted \
  --backup \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags 'Key=Name,Value=wibl-frontend-ecs-task-efs' \
  | tee ${WIBL_BUILD_LOCATION}/create_efs_file_system_frontend.json

echo $'\e[31mWaiting for 10 seconds to allow EFS volumes to propagate ...\e[0m'
sleep 10

# Create mount targets for EFS volume within our VPC subnet
# wibl-manager mount target
aws --region $AWS_REGION efs create-mount-target \
  --file-system-id "$(cat ${WIBL_BUILD_LOCATION}/create_efs_file_system.json | jq -r '.FileSystemId')" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-groups "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_efs_mount_target.json
# wibl-frontend mount target 1 (in first subnet in the AZ)
aws --region $AWS_REGION efs create-mount-target \
  --file-system-id "$(cat ${WIBL_BUILD_LOCATION}/create_efs_file_system_frontend.json | jq -r '.FileSystemId')" \
  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --security-groups "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_efs_mount_target_frontend.json
# wibl-frontend mount target 2 (in second subnet in the AZ)
#aws --region $AWS_REGION efs create-mount-target \
#  --file-system-id "$(cat ${WIBL_BUILD_LOCATION}/create_efs_file_system_frontend.json | jq -r '.FileSystemId')" \
#  --subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private_2.txt)" \
#  --security-groups "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
#  | tee ${WIBL_BUILD_LOCATION}/create_efs_mount_target_frontend_2.json

# Create ingress rule to allow NFS connections from the subnet (e.g., EFS mount points)
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 2049, "ToPort": 2049, "IpRanges": [{"CidrIp": "10.0.0.0/16"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_efs.json

# Tag the NFS ingress rule with a name:
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_efs.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-efs-mount-point'

####################
# Phase 4: Setup ECS cluster and task definitions

# Create cluster
aws --region $AWS_REGION ecs create-cluster \
	--cluster-name wibl-manager-ecs \
	--capacity-providers FARGATE | tee ${WIBL_BUILD_LOCATION}/create_ecs_cluster.json

# Setup 'ecsTaskExecutionRole' role and attach relevant policies
# Create `ecsTaskExecutionRole`
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

# Create load balancers so that lambdas can find wibl-manager and wibl-frontend services
# Create internal NETWORK load balancer for wibl-manager
aws --region $AWS_REGION elbv2 create-load-balancer --name wibl-manager-ecs-elb --type network \
  --subnets "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
  --scheme internal \
  | tee ${WIBL_BUILD_LOCATION}/create_elb.json

# Create internet-facing APPLICATION load balancer for wibl-frontend
# First create security group for load balancer
aws --region $AWS_REGION ec2 create-security-group \
	--group-name wibl-fe-elb-public \
	--vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
	--description "Security Group for use by WIBL frontend load balancer" \
	| tee ${WIBL_BUILD_LOCATION}/create_security_group_fe_elb_public.json
# Tag the security group with a name:
aws --region $AWS_REGION ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_fe_elb_public.json | jq -r '.GroupId')" \
  --tags 'Key=Name,Value=wibl-fe-elb-public'
# Create ingress rule to the wibl-frontend load balancer SG to allow access via ALB listener ports 80 and 443
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_fe_elb_public.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}, {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_fe_elb_public_rule_http.json
# Create egress rule to the wibl-frontend load balancer SG to allow access to front-end ECS instance on port 8000
aws --region $AWS_REGION ec2 authorize-security-group-egress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_fe_elb_public.json | jq -r '.GroupId')" \
  --source-group "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --protocol tcp \
  --port 8000 \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_fe_elb_ecs_sg_rule.json
# Add rule to ECS subnet security group to allow traffic from frontend load balancer
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --protocol tcp \
  --port '8000' \
  --source-group "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_fe_elb_public.json | jq -r '.GroupId')" \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_allow_fe_elb.json

# Finally create the internet-facing wibl-frontend APPLICATION load balancer
aws --region $AWS_REGION elbv2 create-load-balancer --name wibl-frontend-ecs-elb \
  --subnets "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public.txt)" "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public_2.txt)" \
  --security-groups "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_fe_elb_public.json | jq -r '.GroupId')" \
  --scheme internet-facing \
  | tee ${WIBL_BUILD_LOCATION}/create_elb_frontend.json

# Create target groups to associate load balancer listeners to ECS Fargate elastic IP addresses
# wibl-manager target group
aws --region $AWS_REGION elbv2 create-target-group --name wibl-manager-ecs-elb-tg \
  --protocol TCP --port 8000 \
  --target-type ip \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  | tee ${WIBL_BUILD_LOCATION}/create_elb_target_group.json
# wibl-frontend target group
aws --region $AWS_REGION elbv2 create-target-group --name wibl-frontend-ecs-elb-tg \
  --protocol HTTP --port 8000 \
  --health-check-protocol HTTP \
  --health-check-port 8000 \
  --health-check-path /heartbeat \
  --target-type ip \
  --vpc-id "$(cat ${WIBL_BUILD_LOCATION}/create_vpc.txt)" \
  | tee ${WIBL_BUILD_LOCATION}/create_elb_target_group_frontend.json

# Create ELB listeners
# wibl-manager listener
aws --region $AWS_REGION elbv2 create-listener \
  --load-balancer-arn "$(cat ${WIBL_BUILD_LOCATION}/create_elb.json | jq -r '.LoadBalancers[0].LoadBalancerArn')" \
  --protocol TCP \
  --port 80 \
  --default-actions \
    Type=forward,TargetGroupArn="$(cat ${WIBL_BUILD_LOCATION}/create_elb_target_group.json | jq -r '.TargetGroups[0].TargetGroupArn')" \
  | tee ${WIBL_BUILD_LOCATION}/create_elb_listener.json
# wibl-frontend TLS listener
# TODO: Make this a TLS listener (which requires a valid certificate)
aws --region $AWS_REGION elbv2 create-listener \
  --load-balancer-arn "$(cat ${WIBL_BUILD_LOCATION}/create_elb_frontend.json | jq -r '.LoadBalancers[0].LoadBalancerArn')" \
  --protocol HTTP \
  --port 80 \
  --default-actions \
    Type=forward,TargetGroupArn="$(cat ${WIBL_BUILD_LOCATION}/create_elb_target_group_frontend.json | jq -r '.TargetGroups[0].TargetGroupArn')" \
  | tee ${WIBL_BUILD_LOCATION}/create_elb_listener_frontend.json

# Using images pushed to ECR above, create task definitions
# Intantiate wibl-manager task definintion from template and register task with ECS
AWS_EFS_FS_ID="$(cat ${WIBL_BUILD_LOCATION}/create_efs_file_system.json | jq -r '.FileSystemId')"
sed "s|REPLACEME_ACCOUNT_NUMBER|$ACCOUNT_NUMBER|g" manager/input/manager-task-definition.proto | \
  sed "s|REPLACEME_AWS_EFS_FS_ID|$AWS_EFS_FS_ID|g" | \
  sed "s|REPLECEME_AWS_REGION|$AWS_REGION|g" > ${WIBL_BUILD_LOCATION}/manager-task-definition.json
aws --region $AWS_REGION ecs register-task-definition \
	--cli-input-json file://${WIBL_BUILD_LOCATION}/manager-task-definition.json | \
	tee ${WIBL_BUILD_LOCATION}/create_task_definition.json
# Intantiate wibl-frontend task definintion from template and register task with ECS
MANAGEMENT_URL=http://"$(cat ${WIBL_BUILD_LOCATION}/create_elb.json | jq -r '.LoadBalancers[0].DNSName')"/
AWS_EFS_FS_ID_FE="$(cat ${WIBL_BUILD_LOCATION}/create_efs_file_system_frontend.json | jq -r '.FileSystemId')"
sed "s|REPLACEME_ACCOUNT_NUMBER|$ACCOUNT_NUMBER|g" manager/input/frontend-task-definition.proto | \
  sed "s|REPLACEME_AWS_EFS_FS_ID|$AWS_EFS_FS_ID_FE|g" | \
  sed "s|REPLECEME_AWS_REGION|$AWS_REGION|g" | \
  sed "s|REPLACEME_MANAGEMENT_URL|$MANAGEMENT_URL|g" | \
  sed "s|REPLACEME_INCOMING_BUCKET|$INCOMING_BUCKET|g" | \
  sed "s|REPLACEME_STAGING_BUCKET|$STAGING_BUCKET|g" | \
  sed "s|REPLACEME_VIZ_BUCKET|$VIZ_BUCKET|g" | \
  sed "s|REPLACEME_VIZ_LAMBDA|$VIZ_LAMBDA|g" > ${WIBL_BUILD_LOCATION}/frontend-task-definition.json

# Create task role frontend so that we can access resources like S3 from boto3 running inside the frontend
aws --region $AWS_REGION iam create-role \
	--role-name ecsFrontEndTaskRole \
	--assume-role-policy-document file://manager/input/task-execution-assume-role.json \
	| tee ${WIBL_BUILD_LOCATION}/create_frontend_task_role.json
# Allow frontend task role to ccess S3 incoming, staging, and viz buckets
cat > "${WIBL_BUILD_LOCATION}/frontend-s3-access-all.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "FrontendAllowS3AccessAll",
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::${INCOMING_BUCKET}",
                "arn:aws:s3:::${INCOMING_BUCKET}/*",
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
	--role-name ecsFrontEndTaskRole \
	--policy-name frontend-s3-access-all \
	--policy-document file://"${WIBL_BUILD_LOCATION}/frontend-s3-access-all.json"
# Allow frontend task role to invoke VIZ_LAMBDA
cat > "${WIBL_BUILD_LOCATION}/frontend-invoke-vizlambda.json" <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "FrontendAllowVizLambdaInvoke",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:${AWS_REGION}:${ACCOUNT_NUMBER}:function:${VIZ_LAMBDA}"
            ]
        }
    ]
}
HERE
aws --region ${AWS_REGION} iam put-role-policy \
	--role-name ecsFrontEndTaskRole \
	--policy-name frontend-invoke-vizlambda \
	--policy-document file://"${WIBL_BUILD_LOCATION}/frontend-invoke-vizlambda.json"

# Finally register the frontend task definition, including the task role ARN
aws --region $AWS_REGION ecs register-task-definition \
	--cli-input-json file://${WIBL_BUILD_LOCATION}/frontend-task-definition.json \
	--task-role-arn "$(cat ${WIBL_BUILD_LOCATION}/create_frontend_task_role.json | jq -r '.Role.Arn')" | \
	tee ${WIBL_BUILD_LOCATION}/create_task_definition_frontend.json

# Create an ECS services in our cluster to launch one or more tasks based on our task definitions
# wibl-manager service
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
# wibl-frontend service
SUBNET1="$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)"
ELB_TARGET_GROUP_ARN_FE="$(cat ${WIBL_BUILD_LOCATION}/create_elb_target_group_frontend.json | jq -r '.TargetGroups[0].TargetGroupArn')"
aws --region $AWS_REGION ecs create-service \
	--cluster wibl-manager-ecs \
	--service-name wibl-frontend-ecs-svc \
	--task-definition wibl-frontend-ecs-task \
	--desired-count 1 \
	--load-balancers "targetGroupArn=${ELB_TARGET_GROUP_ARN_FE},containerName=wibl-frontend,containerPort=8000" \
	--network-configuration "awsvpcConfiguration={subnets=[ ${SUBNET1} ],securityGroups=[ ${SECURITY_GROUP_ID} ]}" \
	--launch-type "FARGATE" | tee ${WIBL_BUILD_LOCATION}/create_ecs_service_frontend.json
