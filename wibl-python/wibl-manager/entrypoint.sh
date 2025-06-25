#!/bin/bash

set -e
# Wait for postgres to start
echo "Waiting for Postgres Container"
until pg_isready -h db -p 6432 -U postgres; do
  sleep 1
done

echo "Run Alembic Migrations"
alembic upgrade head --sqlalchemy-url=postgresql://postgres:postgres@db:6432/postgres

echo "Migration Finished"

exec gunicorn wibl_manager.application:app --workers 1 --bind 0.0.0.0:8000 --access-logfile -