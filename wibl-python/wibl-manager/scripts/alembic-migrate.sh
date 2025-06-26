#!/bin/bash

db_user="postgres"
db_pass="postgres"
db_host="localhost"
db_port=5432
db_name="postgres"

DATABASE_HOST=$db_host DATABASE_PORT=$db_port \
  DATABASE_USER=$db_user DATABASE_PASSWORD=$db_pass DATABASE_NAME=$db_name \
  alembic upgrade head