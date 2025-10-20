#!/usr/bin/env bash
set -eu -o pipefail

CONTENT_ROOT=$(realpath "$(dirname $0)/../../../..")

source ${CONTENT_ROOT}/scripts/cloud/Terraform/aws/tf-aws-init.sh --silent

rm -rf ${BUILD_DEST}
mkdir -p ${BUILD_DEST}

# Build wibl-upload server container image, create a container, copy upload-server binary from the container,
# then delete the container.
docker buildx build --platform linux/${ARCHITECTURE} -t wibl-upload-server-aws-build ${CONTENT_ROOT}
container=$(docker create wibl-upload-server-aws-build)

cleanup()
{
  docker rm -v -f $container
}
trap cleanup EXIT

docker cp $container:/usr/local/wibl/upload-server/bin/${WIBL_UPLOAD_BINARY} ${BUILD_DEST}
docker cp $container:/usr/local/wibl/upload-server/bin/${ADD_LOGGER_BINARY} ${BUILD_DEST}
