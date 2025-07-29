#!/bin/bash

# Test wibl command line tool

## Define clean-up function
function cleanup () {
  rm -f /tmp/test-wibl.bin
  rm -f /tmp/test-wibl-buffer-constr.bin
  rm -f /tmp/test-wibl-inject.bin
  rm -f /tmp/test-wibl-inject.geojson
}

## Clean-up from possibly failed previous runs
cleanup

## Create some data using `datasim`
wibl datasim -f /tmp/test-wibl.bin -d 3600 -s -b || exit $?

## Create some data using `datasim` (use buffer constructor for logger file)
wibl datasim -f /tmp/test-wibl-buffer-constr.bin -d 3600 -s -b --use-buffer-constructor || exit $?

## Parse binary file into text output using `parsewibl`
wibl parsewibl /tmp/test-wibl.bin || exit $?

## Add platform metadata to WIBL file using `editwibl`
wibl editwibl -m tests/data/b12_v3_metadata_example.json /tmp/test-wibl.bin /tmp/test-wibl-inject.bin || exit $?

## Convert binary WIBL file into GeoJSON using `procwibl`
wibl procwibl -c tests/data/configure.local.json /tmp/test-wibl-inject.bin /tmp/test-wibl-inject.geojson || exit $?

cleanup

exit 0
