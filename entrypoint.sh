#!/bin/sh
# Exit immediately if a command exits with a non-zero status
set -e  

echo "Waiting for database..."
# Wait until Postgres is available
until nc -z primary-db 5432; do
  sleep 1
done

echo "Database is up, running migrations..."
flask db upgrade

echo "Starting the web server..."
exec gunicorn -b 0.0.0.0:8000 "run:app"
