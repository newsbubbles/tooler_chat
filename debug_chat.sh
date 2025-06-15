#!/bin/bash

# Script to enable maximum debugging and check logs for chat issues
echo "Enabling maximum debugging mode..."

# Create debug .env file
cat << EOF > .env.debug
LOG_LEVEL=DEBUG
STRUCTURED_LOGS=true
MAX_DEBUG=true
SQL_ECHO=true
ENVIRONMENT=development
# Copy other variables from your existing .env
$(grep -v "LOG_LEVEL\|STRUCTURED_LOGS\|MAX_DEBUG\|SQL_ECHO\|ENVIRONMENT" .env)
EOF

# Backup current .env
cp .env .env.backup

# Replace with debug version
cp .env.debug .env

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Debug environment enabled. Restarting the backend..."

# Restart backend container
docker-compose restart backend

echo "Waiting for backend to start..."
sleep 5

echo "\nFollow logs in separate terminal windows:\n"
echo "To monitor chat logs:           docker-compose exec backend tail -f /app/logs/chat.log"
echo "To monitor error logs:          docker-compose exec backend tail -f /app/logs/error.log"
echo "To monitor tool calls:          docker-compose exec backend tail -f /app/logs/tool_calls.log"
echo "\nTo reset the agent cache (fixes many issues):\n"
echo "curl -X POST http://localhost:34130/api/chat/reset-agent-cache"

echo "\nNow reproduce the issue with the first message not responding and the second one returning cached data.\n"
