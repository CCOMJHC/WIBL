#!/bin/bash

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