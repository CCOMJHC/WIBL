#!/bin/bash
while getopts u:p:h:a:n: flag
do
    case "${flag}" in
        u) DB_USER=${OPTARG};;
        p) DB_PASS=${OPTARG};;
        h) DB_HOST=${OPTARG};;
        a) DB_PORT=${OPTARG};;
        n) DB_NAME=${OPTARG};;
        *)
    esac
done

DATABASE_URI="postgres://${DB_USER}:${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

echo "Writing these values to manager.env..."
echo "Username: $DB_USER"
echo "Password: $DB_PASS"
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "DB Name: $DB_NAME"
echo "DB URI: $DATABASE_URI"

cat > ../manager.env <<EOF
DATABASE_USER=${DB_USER}
DATABASE_PASSWORD=${DB_USER}
DATABASE_HOST=${DB_HOST}
DATABASE_PORT=${DB_PORT}
DATABASE_NAME=${DB_NAME}
MANAGER_DATABASE_URI=${DATABASE_URI}
EOF