#!/bin/bash

echo "Stopping Tooler Chat Docker containers..."

# Stop and remove containers
docker stop tooler_frontend tooler_backend tooler_db
docker rm tooler_frontend tooler_backend tooler_db

echo "Done! All containers have been stopped and removed."
