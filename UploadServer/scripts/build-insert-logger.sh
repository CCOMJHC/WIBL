#!/bin/bash
# This builds the add-logger tool locally so that the logger.db SQLite file can be generated.
# If you get the following error when running:
#   # runtime/cgo
#   _cgo_export.c:3:10: fatal error: 'stdlib.h' file not found
# (especially under macOS if you have multiple copies of LLVM installed), first run:
#   export CC=/usr/bin/clang
# before running this script.
#
# USAGE:
#
# To add a logger with logger unique identifier 'F94E871E-8A66-4614-9E10-628FFC49540A' and
# password/token 'CC0E1FE1-46CA-4768-93A7-2252BF748118', run:
#    ./add-logger -config config-local.json -logger F94E871E-8A66-4614-9E10-628FFC49540A -password CC0E1FE1-46CA-4768-93A7-2252BF748118
# (if the database specified in config-local.json does not exist, it will first be created)
#
# You can then verify that the logger has been added by running:
#   sqlite3 ./db/loggers.db 'SELECT * FROM loggers'
#   name          hash
#   ------------  ----------------
#   F94E871E-8A6  JDJhJDEwJG90M3RK
#   6-4614-9E10-  dlJRbS9ZM3JOd2Zq
#   628FFC49540A  UUYxQXVsUHd4Nk94
#                 NHNSNEJJb2VjQWo4
#                 YVlkU1laOUlURHM2
#
CONTENT_ROOT=$(realpath "$(dirname $0)/..")

pushd "${CONTENT_ROOT}/src/tools/add-logger"
CGO_ENABLED=1 go build -o "${CONTENT_ROOT}/add-logger"
popd
