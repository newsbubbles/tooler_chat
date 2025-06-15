# Advanced Logging System for Tooler Chat

This document provides information on how to use the enhanced logging system in the Tooler Chat application.

## Overview

The advanced logging system provides:

1. Structured JSON logging for machine readability
2. Rotating file logs for different log levels
3. Request/response tracking with unique IDs
4. Log decorators for API endpoints and tools
5. Web-based log viewer for administrators
6. System information logging

## Log Files

Logs are stored in the `logs/` directory with several different files:

- `tooler_chat.log` - Main application log (rotating by size)
- `error.log` - Errors and exceptions only
- `daily.log` - Daily rotating log
- `tool_calls.log` - Log of tool calls only
- `api_endpoints.log` - Log of API endpoint calls only

## Configuration

Logging can be configured via environment variables in your `.env` file:

```env
LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR, CRITICAL
STRUCTURED_LOGS=true       # Whether to use JSON format (true/false)
```

## Using Logging in Code

### Basic Logging

Instead of using Python's standard `logging` module directly, use the enhanced logger:

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Basic logging
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# Enhanced structured logging with additional data
logger.debug_data("Debug with data", {"value": 123, "items": [1, 2, 3]})
logger.info_data("Info with data", {"user_id": 42, "action": "login"})
logger.error_data("Error with data", {"error_code": 500}, exc_info=True)
```

### Decorating API Endpoints

Use the `log_endpoint` decorator on FastAPI endpoint functions to automatically log requests and timing:

```python
from app.core.logging.decorators import log_endpoint

@router.post("/api/some/endpoint")
@log_endpoint("descriptive_endpoint_name")  # Optional name, defaults to function name
async def my_endpoint(data: SomeModel):
    # Your endpoint code here
    return {"result": "success"}
```

### Logging Tool Calls

Use the `log_tool` decorator on tool functions to automatically track timing and results:

```python
from app.core.logging.decorators import log_tool

@log_tool("descriptive_tool_name")  # Optional name, defaults to function name
async def my_tool_function(param1, param2):
    # Your tool code here
    return result
```

### Operation Context Managers

Wrap operations with context managers to log timing and catch exceptions:

```python
from app.core.logging.context import log_operation, async_log_operation

# Synchronous operations
with log_operation("database_cleanup", extra_data={"tables": ["users", "sessions"]}):
    # Code that will be timed and logged
    clean_database()

# Asynchronous operations
async with async_log_operation("batch_processing", log_level="DEBUG"):
    # Async code that will be timed and logged
    await process_batch(items)
```

## Middleware for Request Tracking

All HTTP requests are automatically logged by the `LoggingMiddleware` which adds unique request IDs to each request and tracks timing information.

The request ID is returned in the response header `X-Request-ID` and can be used for correlating logs across multiple services.

## Log Viewer UI

Administrators can access the log viewer UI at `/admin/logs` to:

- Browse all log files
- Filter logs by level and text content
- View detailed log entries in JSON format
- Download log files
- View system information

## Debugging Tools

### Log Sanitization

Sensitive data like passwords and tokens are automatically redacted in logs using the `sanitize_data` utility:

```python
from app.core.logging.utils import sanitize_data

# Safely log data with sensitive fields redacted
safe_data = sanitize_data(user_data)
logger.info_data("User data", safe_data)
```

### System Information Logging

Log system information for debugging:

```python
from app.core.logging.utils import log_system_info

# Log CPU, memory, disk usage, etc.
log_system_info()
```

## Troubleshooting

### Common Issues

1. **Missing Logs**: Ensure the `logs` directory exists and is writable
2. **Log Format Issues**: Set `STRUCTURED_LOGS=false` to use plain text logs
3. **Performance Issues**: Set `LOG_LEVEL=WARNING` in production for fewer logs

### Viewing Logs in Docker

To view logs when running in Docker:

```bash
# View logs directory content
docker exec -it tooler_chat_backend_1 ls -la /app/logs

# View a specific log file
docker exec -it tooler_chat_backend_1 cat /app/logs/error.log

# Follow a log file in real-time
docker exec -it tooler_chat_backend_1 tail -f /app/logs/tooler_chat.log
```

Alternatively, logs are mounted to the host system in the `./logs` directory when using docker-compose.
