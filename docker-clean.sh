#!/bin/bash

echo "Cleaning up all Tooler Chat Docker resources..."

# Stop and remove containers if they exist
docker stop tooler_frontend tooler_backend tooler_db 2>/dev/null || true
docker rm tooler_frontend tooler_backend tooler_db 2>/dev/null || true

# Remove images
echo "Removing Docker images..."
docker rmi tooler_frontend tooler_backend 2>/dev/null || true

# Optionally remove volumes (uncomment if you want to remove the database data)
# echo "Removing Docker volumes..."
# docker volume rm tooler_postgres_data 2>/dev/null || true

# Remove network
echo "Removing Docker network..."
docker network rm tooler_network 2>/dev/null || true

echo "Clean-up complete! All Tooler Chat Docker resources have been removed."
