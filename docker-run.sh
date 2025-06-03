#!/bin/bash

echo "Starting Tooler Chat application with plain Docker..."

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
SECRET_KEY=${SECRET_KEY:-very-secret-key-for-development-only}

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "OPENAI_API_KEY is not set in your .env file. Please add it and try again."
    exit 1
fi

# Create network if it doesn't exist
if ! docker network inspect tooler_network >/dev/null 2>&1; then
    echo "Creating Docker network 'tooler_network'..."
    docker network create tooler_network
fi

# Start the PostgreSQL container
echo "Starting PostgreSQL container..."
docker run -d \
    --name tooler_db \
    --network tooler_network \
    -p 5432:5432 \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_DB=toolerchat \
    -v tooler_postgres_data:/var/lib/postgresql/data \
    postgres:14

# Wait for PostgreSQL to initialize
echo "Waiting for PostgreSQL to initialize..."
sleep 10  # Add a delay to give PostgreSQL time to start

# Build and start the backend container
echo "Building and starting backend container..."
docker build -t tooler_backend ./backend/
docker run -d \
    --name tooler_backend \
    --network tooler_network \
    -p $BACKEND_PORT:$BACKEND_PORT \
    -e DATABASE_URL="postgresql+asyncpg://postgres:postgres@tooler_db:5432/toolerchat" \
    -e SECRET_KEY="$SECRET_KEY" \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e PORT="$BACKEND_PORT" \
    -v $(pwd)/backend/app:/app/app \
    tooler_backend

# Build and start the frontend container
echo "Building and starting frontend container..."
docker build -t tooler_frontend ./frontend/
docker run -d \
    --name tooler_frontend \
    --network tooler_network \
    -p $FRONTEND_PORT:80 \
    -e BACKEND_URL="http://tooler_backend:$BACKEND_PORT" \
    -e REACT_APP_API_URL="/api" \
    tooler_frontend

echo "Tooler Chat is starting up. Please wait a moment..."
echo "Frontend will be available at http://localhost:$FRONTEND_PORT"
echo "Backend API will be available at http://localhost:$BACKEND_PORT"
echo "API documentation will be available at http://localhost:$BACKEND_PORT/docs"

echo "To stop the application, run: ./docker-stop.sh"
