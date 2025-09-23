#!/bin/sh
docker compose --env-file manager_test.env up --force-recreate -d
# Wait for 2 seconds so that WIBL manager is probably up before we start running tests
# (--wait doesn't seem to work)
sleep 2
python -m unittest wibl_manager/tests/test_wibl_manager.py
TEST_STATUS=$?
docker compose --env-file manager_test.env down
exit $TEST_STATUS
