#!/bin/bash

CONTENT_ROOT=$(realpath "$(dirname $0)/..")

pushd "${CONTENT_ROOT}/src/tools/add-logger"
CGO_ENABLED=1 go build -o "${CONTENT_ROOT}/add-logger"
popd
