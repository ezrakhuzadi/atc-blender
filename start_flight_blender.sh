#!/bin/bash
FLIGHT_BLENDER_ROOT=.

# Only copy .env.sample if .env doesn't exist
if [ ! -f ".env" ] && [ -f ".env.sample" ]; then
    cp .env.sample .env
    echo "Created .env from .env.sample"
elif [ ! -f ".env" ]; then
    echo "ERROR: No .env file found. Please create one from the template."
    exit 1
fi

chmod +x $FLIGHT_BLENDER_ROOT/entrypoints/with-database/entrypoint.sh 2>/dev/null
chmod +x $FLIGHT_BLENDER_ROOT/entrypoints/no-database/entrypoint.sh 2>/dev/null

# Stop local postgresql if running
STATUS="$(systemctl is-active postgresql 2>/dev/null)"
if [ "${STATUS}" = "active" ]; then
    echo "Stopping local instance of postgresql..."
    sudo systemctl stop postgresql
fi

# Create the external network if it doesn't exist
if ! docker network inspect interop_ecosystem_network >/dev/null 2>&1; then
    echo "Creating Docker network: interop_ecosystem_network"
    docker network create interop_ecosystem_network
fi

# Clean up any existing containers and volumes (safely)
docker compose down 2>/dev/null

CONTAINERS=$(docker ps -a -q 2>/dev/null)
if [ -n "$CONTAINERS" ]; then
    docker rm -f $CONTAINERS
fi

VOLUMES=$(docker volume ls -q 2>/dev/null)
if [ -n "$VOLUMES" ]; then
    docker volume rm $VOLUMES
fi

cd $FLIGHT_BLENDER_ROOT
docker compose up --build
