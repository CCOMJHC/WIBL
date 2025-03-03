#!/bin/bash

set -eu -o pipefail

source configuration-parameters.sh

echo $'\e[31mBuilding the WIBL package from' ${WIBL_SRC_LOCATION} $'...\e[0m'

cat > "${WIBL_BUILD_LOCATION}/package-setup.sh" <<-HERE
cd /build
pip install --target ./package -r requirements-lambda.txt
pip install --target ./package ./wibl-manager
pip install --target ./package --no-deps .
HERE

# Remove any previous packaging attempt, so it doesn't try to update what's there already
rm -rf ${WIBL_SRC_LOCATION}/package || exit $?

# Package up the WIBL software so that it can be deployed as a ZIP file
cat "${WIBL_BUILD_LOCATION}/package-setup.sh" | \
    docker run --platform linux/${ARCHITECTURE} --mount type=bind,source=${WIBL_SRC_LOCATION},target=/build \
	    -i --entrypoint /bin/bash public.ecr.aws/lambda/python:${PYTHONVERSION}-${ARCHITECTURE} || exit $?

# You may not be able to run these commands inside the docker container, since the
# AWS container doesn't have ZIP.  If that's the case, there should be a ./package
# directory in your WIBL distribution (from the container); zip the internals of that
# instead.
rm -rf ${WIBL_PACKAGE} || exit $?
(cd ${WIBL_SRC_LOCATION}/package;
zip -q -r ${WIBL_PACKAGE} .) || exit $?

# Clean up packaging attempt so that it doesn't throw off source code control tools
rm -r ${WIBL_SRC_LOCATION}/package || exit $?

exit 0
