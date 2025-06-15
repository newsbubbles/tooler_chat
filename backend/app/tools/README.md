# Tool Logging

This directory contains tools that can be decorated with the enhanced logging system. Here's how to use logging with tools:

## Basic Tool Logging

For any tool function you create, import the `log_tool` decorator from the logging module:

```python
from app.core.logging.decorators import log_tool
from app.core.logging import get_logger

logger = get_logger("app.tools.your_tool")

@log_tool("descriptive_name_for_tool")  # Optional: provide a descriptive name
def your_tool_function(param1, param2):
    # Your tool code here
    logger.info_data("Processing in tool", {
        "param1": param1,
        "additional_info": "some context"
    })
    return result
```

## Async Tool Logging

The same decorator works with both synchronous and asynchronous functions:

```python
from app.core.logging.decorators import log_tool

@log_tool()  # Uses function name by default
async def async_tool_function(param1, param2):
    # Your async tool code here
    return await process_async()
```

## Benefits of Tool Logging Decorator

The `log_tool` decorator automatically:

1. Logs the start of a tool call with parameters (safely redacted)
2. Logs the end of a tool call with timing information
3. Logs any exceptions that occur during the tool call
4. Makes logs appear in both the main log and the dedicated `tool_calls.log` file

## Context Managers for Complex Operations

For more control, use context managers within your tools:

```python
from app.core.logging.context import log_operation, async_log_operation

@log_tool()
def complex_tool_function():
    # Main tool logic...
    
    with log_operation("database_query", log_level="DEBUG"):
        # Database operations that will be timed and logged
        result = db.execute_query()
    
    with log_operation("data_processing", extra_data={"items": count}):
        # More operations
        process_results(result)
        
    return final_result
```

## Finding Tool Logs

Tool logs appear in two places:

1. `logs/tooler_chat.log` - Main application log
2. `logs/tool_calls.log` - Tool-specific log

Admins can also view logs in the web interface at `/admin/logs`.
