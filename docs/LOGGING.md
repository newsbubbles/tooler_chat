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
7. Ultra-verbose debugging mode with full request/response bodies
8. SQL query logging with timing information

## Log Files

Logs are stored in the `logs/` directory with several different files:

- `tooler_chat.log` - Main application log (rotating by size)
- `error.log` - Errors and exceptions only
- `daily.log` - Daily rotating log
- `tool_calls.log` - Log of tool calls only
- `api_endpoints.log` - Log of API endpoint calls only
- `chat.log` - **NEW!** Dedicated log for chat operations

When MAX_DEBUG mode is enabled, additional log files are created:

- `requests.log` - Detailed log of all HTTP requests and responses with bodies
- `sql.log` - Detailed log of all SQL queries with parameters and timing

## Configuration

Logging can be configured via environment variables in your `.env` file:

```env
LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR, CRITICAL
STRUCTURED_LOGS=true       # Whether to use JSON format (true/false)
MAX_DEBUG=false           # Enable ultra-verbose logging (true/false)
SQL_ECHO=false            # Enable SQL query logging (true/false)
```

### MAX_DEBUG Mode

For maximum debugging capabilities, enable MAX_DEBUG mode:

```env
MAX_DEBUG=true
```

This will:

1. Log **every** HTTP request with full headers and bodies
2. Log **every** HTTP response with full headers and bodies
3. Log **every** SQL query with parameters and timing
4. Create dedicated log files for requests and SQL queries
5. Set all loggers to DEBUG level

**Note:** This generates a large volume of logs and should only be used temporarily for debugging.

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

### Exception Catching

Use the catch_exceptions context manager to automatically log and re-raise exceptions:

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# This will catch, log, and re-raise any exceptions
with logger.catch_exceptions("important_operation"):
    # Code that might raise exceptions
    process_data()
```

## Chat-Specific Logging

### Using the Dedicated Chat Logger

For chat operations, use the dedicated chat logger module:

```python
from app.api.chat_logger import (
    log_chat_session_operation,
    log_message_operation,
    log_agent_operation,
    log_chat_error,
    timed_operation
)

# Log a chat session operation
log_chat_session_operation(
    "created", 
    session_uuid=str(chat_session.uuid), 
    user_id=current_user.id, 
    title=session_data.title
)

# Log a message operation
log_message_operation(
    "sent",
    session_uuid=str(session_uuid),
    message_uuid=str(message.uuid),
    role="user",
    content_length=len(message.content)
)

# Time an agent operation
async with timed_operation(
    "process_message",
    session_uuid=str(session_uuid),
    agent_name=agent.name
):
    # Complex agent processing here
    result = await agent.process(message)
```

### Debugging Chat Issues

When debugging chat-related issues, focus on these log files:

```bash
# View dedicated chat logs
docker exec -it tooler_chat_backend_1 tail -f /app/logs/chat.log

# View chat errors
docker exec -it tooler_chat_backend_1 grep -r "Chat error" /app/logs/error.log

# Track a specific chat session
docker exec -it tooler_chat_backend_1 grep -r "YOUR_SESSION_UUID" /app/logs/chat.log
```

## Middleware for Request Tracking

All HTTP requests are automatically logged by the `LoggingMiddleware` with:

- Unique request IDs for each request
- Timing information at millisecond precision
- HTTP method, path, and status code
- Request headers (with sensitive values redacted)
- Response headers (with sensitive values redacted)

In MAX_DEBUG mode, it also logs:

- Full request bodies (with sensitive fields redacted)
- Full response bodies (with sensitive fields redacted)
- Query parameters
- Client information

The request ID is returned in the response header `X-Request-ID` and can be used for correlating logs across multiple services.

## Database Query Logging

When `SQL_ECHO=true` or `MAX_DEBUG=true`, all database queries are logged with:

- SQL query text
- Query parameters 
- Execution time in milliseconds
- Success or failure status

This logging is done automatically for all database operations.

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

### Database Health Check

Check database connectivity and performance:

```python
from app.db.database import db_health_check

# Get database status and performance metrics
health_status = await db_health_check()
print(health_status)
```

## Troubleshooting

### Common Issues

1. **Missing Logs**: Ensure the `logs` directory exists and is writable
2. **Log Format Issues**: Set `STRUCTURED_LOGS=false` to use plain text logs
3. **Performance Issues**: Set `LOG_LEVEL=WARNING` in production for fewer logs
4. **Large Log Files**: Disable `MAX_DEBUG` mode when not actively debugging

### Debugging Chat Message Issues

To specifically debug chat message problems:

1. Enable MAX_DEBUG mode temporarily
2. Send a problematic message from the frontend
3. Check these logs in order:
   - `chat.log` - For the flow of the chat operation
   - `error.log` - For any exceptions that occurred
   - `tool_calls.log` - If the issue involves agent tools
   - `sql.log` - If the issue might be database-related

4. Look for the `debug_step` field in error logs to identify the exact point of failure

### Viewing Logs in Docker

To view logs when running in Docker:

```bash
# View logs directory content
docker exec -it tooler_chat_backend_1 ls -la /app/logs

# View a specific log file
docker exec -it tooler_chat_backend_1 cat /app/logs/error.log

# Follow chat logs in real-time
docker exec -it tooler_chat_backend_1 tail -f /app/logs/chat.log

# Follow request logs in MAX_DEBUG mode
docker exec -it tooler_chat_backend_1 tail -f /app/logs/requests.log
```

Alternatively, logs are mounted to the host system in the `./logs` directory when using docker-compose.

### Checking Log Settings

Add this API endpoint to check current log settings:

```python
@app.get("/api/logs/settings")
async def get_log_settings():
    import logging
    return {
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "structured_logs": os.getenv("STRUCTURED_LOGS", "true"),
        "max_debug": os.getenv("MAX_DEBUG", "false"),
        "sql_echo": os.getenv("SQL_ECHO", "false"),
        "root_logger_level": logging.getLevelName(logging.getLogger().level),
        "loggers": {
            "app": logging.getLevelName(logging.getLogger("app").level),
            "app.api": logging.getLevelName(logging.getLogger("app.api").level),
            "app.api.chat": logging.getLevelName(logging.getLogger("app.api.chat").level),
            "sqlalchemy": logging. getLevelName(logging.getLogger("sqlalchemy").level),
        }
    }
```