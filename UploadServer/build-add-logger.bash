#!/usr/bin/env bash
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
# To add a logger with logger unique identifier 'TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A' and
# password/token 'CC0E1FE1-46CA-4768-93A7-2252BF748118', run:
#    ./add-logger -config config-local.json -logger TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A -password CC0E1FE1-46CA-4768-93A7-2252BF748118
# (if the database specified in config-local.json does not exist, it will first be created)
#
# You can then verify that the logger has been added by running:
#   sqlite3 ./db/loggers.db 'SELECT * FROM loggers'
#TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A|JDJhJDEwJGhyNVVPcWE0MkpTSjVTYjUySnhjZ3VTc1lsQmZqNHZWN2Q3NkNDZ2M5R0dDNWlmM0Vjemh1
#
if [[ -z ${ADD_LOGGER_OUT} ]]; then
  CONTENT_ROOT=$(realpath "$(dirname $0)")
  ADD_LOGGER_OUT="${CONTENT_ROOT}/add-logger"
  pushd ${CONTENT_ROOT}/src/tools/add-logger
fi

echo "Running go build for add-logger..."
CGO_ENABLED=1 go build -o ${ADD_LOGGER_OUT}
