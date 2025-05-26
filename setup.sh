#!/bin/bash

echo "Setting up Tooler Chat development environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker before continuing."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose before continuing."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit the .env file with your configuration before running the application."
fi

# Setup frontend dependencies
echo "Setting up frontend dependencies..."
cd frontend
if [ -f "package.json" ]; then
    if command -v npm &> /dev/null; then
        echo "Installing frontend dependencies with npm..."
        npm install
    else
        echo "npm is not installed. Skipping frontend dependency installation."
        echo "Please install Node.js and npm, then run 'npm install' in the frontend directory."
    fi
fi
cd ..

# Build Docker images
echo "Building Docker images..."
docker-compose build

echo ""
echo "Setup complete! You can now run the application using:"
echo "  ./run.sh"
