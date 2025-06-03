#!/bin/bash

echo "Starting Tooler Chat application..."

# Check if .env file exists, if not create one from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit the .env file with your configuration before running the application."
    exit 1
fi

# Load environment variables
source .env

# Use default ports if not set in .env
BACKEND_PORT=${BACKEND_PORT:-34130}
FRONTEND_PORT=${FRONTEND_PORT:-34140}

# Build and start the containers
docker-compose up --build -d

echo "Tooler Chat is starting up. Please wait a moment..."
echo "Frontend will be available at http://localhost:$FRONTEND_PORT"
echo "Backend API will be available at http://localhost:$BACKEND_PORT"
echo "API documentation will be available at http://localhost:$BACKEND_PORT/docs"

echo "To stop the application, run: ./stop.sh"
