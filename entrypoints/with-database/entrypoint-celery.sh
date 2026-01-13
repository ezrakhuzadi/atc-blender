#!/bin/bash

# Virtual environment is already activated via PATH in Dockerfile

echo "Waiting for DBs..."
wait-for-it $REDIS_HOST:$REDIS_PORT --timeout=30 -- echo "Redis is up"

celery --app=flight_blender worker --loglevel=info

