#!/bin/bash

docker compose up -d

until [ "$(docker inspect -f '{{.State.Health.Status}}' frontend)" == "healthy" ]; do
  sleep 1
done

docker compose run frontend python manager.py makemigrations && docker compose run frontend python manager.py migrate

