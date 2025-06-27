#!/bin/bash

db_user="postgres"
db_pass="postgres"
db_host="localhost"
db_port=5432
db_name="postgres"

while getopts m: flag
do
    case "${flag}" in
        m) MESSAGE=${OPTARG};;
        *) MESSAGE="Alembic Revision"
    esac
done

cd ..

DATABASE_HOST=$db_host DATABASE_PORT=$db_port \
  DATABASE_USER=$db_user DATABASE_PASSWORD=$db_pass DATABASE_NAME=$db_name \
  alembic revision --autogenerate -m "$MESSAGE"