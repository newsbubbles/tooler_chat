#!/bin/bash

# Apply the tooler agent integration changes
set -e

echo "Applying tooler agent integration..."

# Check if we are on the tooler-integration branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "tooler-integration" ]; then
    echo "Error: You must be on the tooler-integration branch to run this script."
    exit 1
fi

# Create project_tools directory if it doesn't exist
mkdir -p project_tools

# Run the copy_tooler_files.py script to copy necessary files from tooler
echo "Copying tools from tooler project..."
python scripts/copy_tooler_files.py

# Rename the updated files to replace the originals
echo "Applying code changes..."

# Check if the updated files exist
if [ -f "backend/app/api/chat_updated.py" ]; then
    mv backend/app/api/chat_updated.py backend/app/api/chat.py
    echo "Applied chat.py updates"
fi

if [ -f "backend/app/main_updated.py" ]; then
    mv backend/app/main_updated.py backend/app/main.py
    echo "Applied main.py updates"
fi

# Run the database migration to add default Tooler agent
echo "Running database migration..."
python -m backend.app.migrations.add_default_tooler_agent

echo "\nTooler agent integration complete!\n"
echo "You can now start the application with './run.sh'"
echo "Remember to set the required environment variables:"
echo "  - OPENAI_API_KEY or OPENROUTER_API_KEY"
echo "  - SERPER_API_KEY"

exit 0
