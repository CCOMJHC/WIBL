#!/bin/bash

# IMPORTANT: This file and all other scripts other than "build-lambda.sh" are apart of the deprecated scripting
# build approach. The intended build method is to use Terraform. Follow the instructions in the README.md located in the
# Terraform folder.

# This script sets up the an EC2 instance running on a public subnet to allow access to the WIBL Cloud Manager
# service running on AWS using ECS.

source configuration-parameters.sh

# Update security group to allow SSH ingress from trusted public IP
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public.json | jq -r '.GroupId')" \
  --ip-permissions "[{\"IpProtocol\": \"tcp\", \"FromPort\": 22, \"ToPort\": 22, \"IpRanges\": [{\"CidrIp\": \"${TRUSTED_IP_ADDRESS}/32\"}]}]" \
  | tee "${WIBL_BUILD_LOCATION}/create_security_group_public_rule_vpc_ssh.json"

# Tag the SSH ingress rule with a name
aws ec2 create-tags \
  --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public_rule_vpc_ssh.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-test-ec2-ssh'

# Create SSH key pair
aws ec2 create-key-pair \
  --key-name wibl-manager-key \
  --key-type rsa \
  --key-format pem \
  --query "KeyMaterial" \
  --output text > "${WIBL_BUILD_LOCATION}/wibl-manager-key.pem"
chmod 400 "${WIBL_BUILD_LOCATION}/wibl-manager-key.pem"

# Launch test EC2 instance with key, security group, in the public subnet
# Note: This will be used as a "jump box" to access the EC2 instance running within the private subnet
aws ec2 run-instances --image-id ami-09f3bb43b9f607008 --count 1 --instance-type t4g.nano \
	--key-name wibl-manager-key \
	--associate-public-ip-address \
	--security-group-ids \
	  "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public.json | jq -r '.GroupId')" \
	--subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_public.txt)" \
	| tee ${WIBL_BUILD_LOCATION}/run-test-ec2-instance.json

# Tag the instance with a name
aws ec2 create-tags \
  --resources "$(cat ${WIBL_BUILD_LOCATION}/run-test-ec2-instance.json | jq -r '.Instances[0].InstanceId')" \
  --tags 'Key=Name,Value=wibl-manager-test'

# Launch test EC2 instance with key, security group, in the PRIVATE subnet
aws ec2 run-instances --image-id ami-09f3bb43b9f607008 --count 1 --instance-type t4g.nano \
	--key-name wibl-manager-key \
	--security-group-ids \
	  "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_public.json | jq -r '.GroupId')" \
	  "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
	--subnet-id "$(cat ${WIBL_BUILD_LOCATION}/create_subnet_private.txt)" \
	| tee ${WIBL_BUILD_LOCATION}/run-private-ec2-instance.json

# Tag the instance with a name
aws ec2 create-tags \
  --resources "$(cat ${WIBL_BUILD_LOCATION}/run-private-ec2-instance.json | jq -r '.Instances[0].InstanceId')" \
  --tags 'Key=Name,Value=wibl-manager-private'

# Create ingress rule to allow SSH access to instances in the private subnet from anywhere in the VPC
aws --region $AWS_REGION ec2 authorize-security-group-ingress \
  --group-id "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private.json | jq -r '.GroupId')" \
  --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "10.0.0.0/16"}]}]' \
  | tee ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_ssh.json

# Tag the load balancer ingress rule with a name
aws ec2 create-tags --resources "$(cat ${WIBL_BUILD_LOCATION}/create_security_group_private_rule_ssh.json | jq -r '.SecurityGroupRules[0].SecurityGroupRuleId')" \
  --tags 'Key=Name,Value=wibl-manager-private-ssh'