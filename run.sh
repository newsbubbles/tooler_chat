#!/bin/bash

echo "Starting Tooler Chat application..."

# Check if .env file exists, if not create one from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit the .env file with your configuration before running the application."
    exit 1
fi

# Build and start the containers
docker-compose up --build -d

echo "Tooler Chat is starting up. Please wait a moment..."
echo "Frontend will be available at http://localhost:3000"
echo "Backend API will be available at http://localhost:8000"
echo "API documentation will be available at http://localhost:8000/docs"

echo "To stop the application, run: docker-compose down"
