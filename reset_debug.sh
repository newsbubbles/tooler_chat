#!/bin/bash

# Script to restore normal settings after debugging
echo "Restoring normal settings from backup..."

if [ -f .env.backup ]; then
  cp .env.backup .env
  echo "Settings restored from backup."
else
  echo "No backup found. Creating standard settings..."
  cat << EOF > .env
LOG_LEVEL=INFO
STRUCTURED_LOGS=true
MAX_DEBUG=false
SQL_ECHO=false
ENVIRONMENT=development
# Copy other variables from debug .env
$(grep -v "LOG_LEVEL\|STRUCTURED_LOGS\|MAX_DEBUG\|SQL_ECHO\|ENVIRONMENT" .env)
EOF
fi

echo "Restarting the backend with normal settings..."
docker-compose restart backend

echo "Done!"
