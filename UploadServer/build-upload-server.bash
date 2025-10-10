#!/usr/bin/env bash
set -eu -o pipefail

echo "Running go mod download..."
go mod download
echo "Running go build for upload-server..."
CGO_ENABLED=1 GOOS=linux go build -o ${UPLOAD_SERVER_OUT}
