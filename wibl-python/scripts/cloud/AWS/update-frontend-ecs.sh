#!/bin/bash

# IMPORTANT: This file and all other scripts other than "build-lambda.sh" are apart of the deprecated scripting
# build approach. The intended build method is to use Terraform. Follow the instructions in the README.md located in the
# Terraform folder.

set -eu -o pipefail

source configuration-parameters.sh

# Rebuild frontend image and push to ECR repo
./build-frontend.sh

aws --region $AWS_REGION ecs update-service \
  --cluster wibl-manager-ecs \
	--service wibl-frontend-ecs-svc \
	--force-new-deployment

# If you need to update a service after updating the task definition,
# do:
#  aws --region $AWS_REGION ecs update-service \
#    --cluster wibl-manager-ecs \
#    --service wibl-frontend-ecs-svc \
#    --force-new-deployment \
#    --task-definition wibl-frontend-ecs-task:N
# Where N=the number of the most recent task definition.
