import os
import sys
import traceback
from typing import Dict, Any, Optional, List, Union
import json
from datetime import datetime
from pydantic import BaseModel

from .config import get_logger

logger = get_logger("app.core.logging.utils")

def sanitize_data(data: Any) -> Any:
    """Sanitize data for logging to avoid sensitive information"""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Skip sensitive keys
            if key.lower() in (
                "password", "token", "secret", "authorization", 
                "api_key", "key", "credential", "hashed_password"
            ):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, (BaseModel,)):
        # Handle Pydantic models
        try:
            return sanitize_data(data.model_dump())
        except Exception:
            return str(data)
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        # For other complex types, convert to string
        return str(data)


def format_exception(exc: Exception) -> Dict[str, Any]:
    """Format exception details for logging"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    frames = traceback.extract_tb(exc_traceback)
    
    # Format frames
    formatted_frames = []
    for frame in frames:
        formatted_frames.append({
            "filename": frame.filename,
            "lineno": frame.lineno,
            "name": frame.name,
            "line": frame.line
        })
    
    return {
        "type": exc_type.__name__ if exc_type else type(exc).__name__,
        "message": str(exc),
        "traceback": formatted_frames
    }


def log_system_info() -> None:
    """Log system information"""
    import platform
    import psutil
    import datetime
    
    system_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "memory": {
            "total": round(psutil.virtual_memory().total / (1024 * 1024 * 1024), 2),  # GB
            "available": round(psutil.virtual_memory().available / (1024 * 1024 * 1024), 2),  # GB
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": round(psutil.disk_usage('/').total / (1024 * 1024 * 1024), 2),  # GB
            "free": round(psutil.disk_usage('/').free / (1024 * 1024 * 1024), 2),  # GB
            "percent": psutil.disk_usage('/').percent
        },
        "time": datetime.datetime.now().isoformat(),
        "timezone": datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo.tzname(None)
    }
    
    logger.info_data("System information", {"system": system_info})


def log_api_call_result(call_name: str, status_code: int, response_data: Any, elapsed_ms: int) -> None:
    """Log API call result with detailed information
    
    Args:
        call_name: Name of the API call
        status_code: HTTP status code
        response_data: Response data
        elapsed_ms: Time taken in milliseconds
    """
    # Sanitize response data
    safe_response = sanitize_data(response_data)
    
    # Determine log level based on status code
    if status_code >= 500:
        log_level = "error"
    elif status_code >= 400:
        log_level = "warning"
    else:
        log_level = "info"
    
    # Get the appropriate logger method
    log_func = getattr(logger, f"{log_level}_data")
    
    # Log the API call result
    log_func(
        f"API Call Result: {call_name} - Status: {status_code}",
        {
            "api_call": call_name,
            "status_code": status_code,
            "elapsed_ms": elapsed_ms,
            "response_size": len(json.dumps(safe_response)) if isinstance(safe_response, (dict, list)) else len(str(safe_response)),
            "response": safe_response
        }
    )


def log_db_operation(operation: str, model: str, query_params: Optional[Dict[str, Any]] = None, result_count: Optional[int] = None, elapsed_ms: Optional[int] = None) -> None:
    """Log database operation details
    
    Args:
        operation: Type of operation (SELECT, INSERT, UPDATE, DELETE)
        model: Database model name
        query_params: Query parameters
        result_count: Number of records affected/returned
        elapsed_ms: Time taken in milliseconds
    """
    logger.info_data(
        f"DB Operation: {operation} on {model}",
        {
            "db": {
                "operation": operation,
                "model": model,
                "params": sanitize_data(query_params) if query_params else None,
                "result_count": result_count,
                "elapsed_ms": elapsed_ms
            }
        }
    )