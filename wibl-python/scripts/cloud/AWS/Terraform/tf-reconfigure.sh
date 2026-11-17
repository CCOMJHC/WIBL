#!/usr/bin/env bash
set -eu -o pipefail

terraform init -reconfigure -backend-config=backend.hcl