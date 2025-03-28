#!/bin/bash

set -eu -o pipefail

source configuration-parameters.sh

echo $'\e[31mBuilding and pushing the WIBL manager container...\e[0m'

# `docker login` to the repo so that we can push to it
aws --region $AWS_REGION ecr get-login-password | docker login \
  --username AWS \
  --password-stdin \
  "$(cat ${WIBL_BUILD_LOCATION}/create_ecr_repository.json | jq -r '.repository.repositoryUri')"
# If `docker login` is successful, you should see `Login Succeeded` printed to STDOUT.

docker build --platform linux/${ARCHITECTURE} -t wibl/manager ../../../wibl-manager/
docker tag wibl/manager:latest "${ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/wibl/manager:latest"
docker push "${ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/wibl/manager:latest" | tee "${WIBL_BUILD_LOCATION}/docker_push_to_ecr.txt"
