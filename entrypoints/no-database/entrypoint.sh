#!/bin/bash

# Virtual environment is already activated via PATH in Dockerfile

echo "Waiting for DBs..."
wait-for-it $REDIS_HOST:$REDIS_PORT --timeout=30 -- echo "Redis is up"

# Collect static files
#echo "Collect static files"
#python manage.py collectstatic --noinput

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

# Start server
echo "Starting server"
uvicorn flight_blender.asgi:application --host 0.0.0.0 --port 8000 --workers 3 --reload

