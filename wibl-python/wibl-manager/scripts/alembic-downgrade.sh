#!/bin/bash

# DATABASE_HOST="localhost" DATABASE_PORT=5432 DATABASE_USER="postgres" \
# DATABASE_PASSWORD="postgres" DATABASE_NAME="postgres" alembic current

db_user="postgres"
db_pass="postgres"
db_host="localhost"
db_port=5432
db_name="postgres"

cd ..

DATABASE_HOST=$db_host DATABASE_PORT=$db_port \
  DATABASE_USER=$db_user DATABASE_PASSWORD=$db_pass DATABASE_NAME=$db_name \
  alembic downgrade head