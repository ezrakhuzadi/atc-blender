#!/bin/bash
set -euo pipefail

FLIGHT_BLENDER_ROOT="."

RESET_VOLUMES=0
COMPOSE_FILE="docker-compose.yml"
for arg in "$@"; do
    case "${arg}" in
        --reset)
            RESET_VOLUMES=1
            ;;
        --dev)
            COMPOSE_FILE="docker-compose-dev.yml"
            ;;
        *)
            echo "Unknown argument: ${arg}"
            echo "Usage: $0 [--dev] [--reset]"
            exit 1
            ;;
    esac
done

COMPOSE_ARGS=(-f "${COMPOSE_FILE}")

# Only copy .env.sample if .env doesn't exist
if [ ! -f ".env" ] && [ -f ".env.sample" ]; then
    cp .env.sample .env
    echo "Created .env from .env.sample"
elif [ ! -f ".env" ]; then
    echo "ERROR: No .env file found. Please create one from the template."
    exit 1
fi

chmod +x "${FLIGHT_BLENDER_ROOT}/entrypoints/with-database/entrypoint.sh" 2>/dev/null || true
chmod +x "${FLIGHT_BLENDER_ROOT}/entrypoints/no-database/entrypoint.sh" 2>/dev/null || true

# Create the external network if it doesn't exist
if ! docker network inspect interop_ecosystem_network >/dev/null 2>&1; then
    echo "Creating Docker network: interop_ecosystem_network"
    docker network create interop_ecosystem_network
fi

cd "${FLIGHT_BLENDER_ROOT}"

if [ "${RESET_VOLUMES}" -eq 1 ]; then
    echo "Resetting Flight Blender compose stack (project-scoped): removing containers + volumes..."
    docker compose "${COMPOSE_ARGS[@]}" down -v --remove-orphans
else
    docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans
fi

docker compose "${COMPOSE_ARGS[@]}" up --build
