#!/bin/bash

# Script to view and format logs from the Docker container

if [ $# -lt 1 ]; then
  echo "Usage: $0 <log_type>"
  echo "Available log types: chat, error, tool, sql, all"
  exit 1
fi

log_type=$1

case "$log_type" in
  "chat")
    echo "Viewing chat logs..."
    docker-compose exec backend tail -f /app/logs/chat.log | python -m json.tool
    ;;
  "error")
    echo "Viewing error logs..."
    docker-compose exec backend tail -f /app/logs/error.log | python -m json.tool
    ;;
  "tool")
    echo "Viewing tool call logs..."
    docker-compose exec backend tail -f /app/logs/tool_calls.log | python -m json.tool
    ;;
  "sql")
    echo "Viewing SQL logs..."
    docker-compose exec backend tail -f /app/logs/sql.log | python -m json.tool
    ;;
  "all")
    echo "Viewing all logs in combined format..."
    docker-compose logs -f backend
    ;;
  *)
    echo "Unknown log type: $log_type"
    echo "Available log types: chat, error, tool, sql, all"
    exit 1
    ;;
esac
