import logging
import os
import sys
import time
import json
from datetime import datetime
import traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import uuid
import threading
from typing import Optional, Dict, Any, Union

# Define defaults
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_STRUCTURED_FORMAT = True

# Store request_id in thread local storage
local = threading.local()

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)


class RequestIdFilter(logging.Filter):
    """Filter that adds request_id to log records"""
    
    def filter(self, record):
        record.request_id = getattr(local, 'request_id', '-')
        return True


class StructuredLogFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""
    
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
    
    def format(self, record):
        log_record = {}
        
        # Standard log fields
        log_record["timestamp"] = datetime.fromtimestamp(record.created).strftime(
            DEFAULT_LOG_DATE_FORMAT
        )
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["message"] = record.getMessage()
        
        # Add thread and process info
        log_record["thread"] = record.threadName
        log_record["process"] = record.processName
        
        # Add request_id if available
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        
        # Add file and line info
        log_record["file"] = record.pathname
        log_record["line"] = record.lineno
        log_record["function"] = record.funcName
        
        # Add exception info if applicable
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add custom fields
        if hasattr(record, "data") and record.data:
            for key, value in record.data.items():
                # Avoid overwriting standard fields
                if key not in log_record:
                    log_record[key] = value
        
        try:
            return json.dumps(log_record)
        except Exception as e:
            # Fallback if JSON serialization fails
            return json.dumps({
                "timestamp": log_record["timestamp"],
                "level": log_record["level"],
                "logger": log_record["logger"],
                "message": log_record["message"],
                "error": f"Failed to serialize log record: {str(e)}"
            })


def setup_logging(
    log_level: str = None,
    structured: bool = None,
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_debug: bool = False  # New parameter for ultra-verbose logging
) -> None:
    """Set up logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Whether to use JSON structured logging format
        log_to_file: Whether to log to files
        log_to_console: Whether to log to console
        max_debug: Enable ultra-verbose logging (all requests, responses, etc.)
    """
    # Get configuration from environment variables or use defaults
    log_level = log_level or os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    structured = structured if structured is not None else os.getenv("STRUCTURED_LOGS", DEFAULT_STRUCTURED_FORMAT) in (True, "true", "True", "1")
    max_debug = max_debug or os.getenv("MAX_DEBUG", "false").lower() in ("true", "1", "yes")
    
    # Convert log level string to constant
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}, using default: {DEFAULT_LOG_LEVEL}")
        numeric_level = getattr(logging, DEFAULT_LOG_LEVEL)
        
    # Reset root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    
    # Add request ID filter to all logs
    request_filter = RequestIdFilter()
    root_logger.addFilter(request_filter)
    
    # Create formatter
    if structured:
        formatter = StructuredLogFormatter()
    else:
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_LOG_DATE_FORMAT)
    
    # Add console handler if enabled
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handlers if enabled
    if log_to_file:
        try:
            # Main application log - rotating by size
            app_log_path = logs_dir / "tooler_chat.log"
            app_handler = RotatingFileHandler(
                filename=app_log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            app_handler.setLevel(numeric_level)
            app_handler.setFormatter(formatter)
            root_logger.addHandler(app_handler)
            
            # Error log - separate file for errors and above
            error_log_path = logs_dir / "error.log"
            error_handler = RotatingFileHandler(
                filename=error_log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)
            
            # Daily log - rotating by date
            daily_log_path = logs_dir / "daily.log"
            daily_handler = TimedRotatingFileHandler(
                filename=daily_log_path,
                when="midnight",
                interval=1,
                backupCount=30  # Keep last 30 days
            )
            daily_handler.setLevel(numeric_level)
            daily_handler.setFormatter(formatter)
            daily_handler.suffix = "%Y-%m-%d"  # Use date as suffix for rotated files
            root_logger.addHandler(daily_handler)
            
            # Tool/API endpoint specific log
            tool_log_path = logs_dir / "tool_calls.log"
            tool_handler = RotatingFileHandler(
                filename=tool_log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            tool_handler.setLevel(numeric_level)
            tool_handler.setFormatter(formatter)
            tool_logger = logging.getLogger("app.tools")
            tool_logger.propagate = True  # Allow messages to propagate to root logger
            tool_logger.addHandler(tool_handler)
            
            # API endpoint log
            api_log_path = logs_dir / "api_endpoints.log"
            api_handler = RotatingFileHandler(
                filename=api_log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            api_handler.setLevel(numeric_level)
            api_handler.setFormatter(formatter)
            api_logger = logging.getLogger("app.api")
            api_logger.propagate = True  # Allow messages to propagate to root logger
            api_logger.addHandler(api_handler)
            
            # Request/Response log for ultra-verbose mode
            if max_debug:
                request_log_path = logs_dir / "requests.log"
                request_handler = RotatingFileHandler(
                    filename=request_log_path,
                    maxBytes=20 * 1024 * 1024,  # 20MB for verbose requests
                    backupCount=10
                )
                request_handler.setLevel(logging.DEBUG)  # Always DEBUG level
                request_handler.setFormatter(formatter)
                request_logger = logging.getLogger("app.api.middleware")
                request_logger.setLevel(logging.DEBUG)  # Force to DEBUG level
                request_logger.addHandler(request_handler)
                
                # Also set SQLModel and database loggers to DEBUG for SQL queries
                logging.getLogger("sqlmodel").setLevel(logging.DEBUG)
                logging.getLogger("sqlalchemy").setLevel(logging.DEBUG)
                logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)
                
                # Set FastAPI uvicorn logger to DEBUG
                logging.getLogger("uvicorn").setLevel(logging.DEBUG)
                logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
                
                # Add a handler for SQL queries
                sql_log_path = logs_dir / "sql.log"
                sql_handler = RotatingFileHandler(
                    filename=sql_log_path,
                    maxBytes=10 * 1024 * 1024,
                    backupCount=5
                )
                sql_handler.setLevel(logging.DEBUG)
                sql_handler.setFormatter(formatter)
                sql_logger = logging.getLogger("sqlalchemy.engine")
                sql_logger.addHandler(sql_handler)
                
                print(f"MAX DEBUG MODE ENABLED - All requests, responses, and SQL queries will be logged")
        except Exception as e:
            # Fallback to console-only logging if file handlers fail
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(numeric_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            print(f"Error setting up file handlers: {str(e)}. Falling back to console logging.")


def set_request_id(request_id: Optional[str] = None):
    """Set a request ID for the current thread"""
    local.request_id = request_id or str(uuid.uuid4())
    return local.request_id


def get_request_id() -> str:
    """Get the current request ID or generate a new one"""
    if not hasattr(local, "request_id"):
        set_request_id()
    return local.request_id


class LoggerExtension:
    """Adds additional methods to a logger instance"""
    
    def __init__(self, logger):
        self._logger = logger
    
    def catch_exceptions(self, operation_name: str):
        """Context manager for catching and logging exceptions"""
        from contextlib import contextmanager
        
        @contextmanager
        def context_manager():
            try:
                yield
            except Exception as e:
                self._logger.error_data(
                    f"Exception in {operation_name}",
                    {"error": str(e), "operation": operation_name},
                    exc_info=True
                )
                raise
        
        return context_manager()


def get_logger(name: str):
    """Get a logger with enhanced functionality"""
    logger = logging.getLogger(name)
    
    # Only enhance if not already enhanced
    if not hasattr(logger, "info_data"):
        # Add extension methods
        extension = LoggerExtension(logger)
        logger.catch_exceptions = extension.catch_exceptions
        
        def log_with_data(level: int, msg: str, data: Dict[str, Any] = None, **kwargs):
            """Log at the specified level with additional structured data"""
            if logger.isEnabledFor(level):
                # Create a record with extra data
                extra = kwargs.pop("extra", {}) or {}
                extra["data"] = data or {}
                
                # Add any kwargs to the data
                if kwargs:
                    extra["data"].update(kwargs)
                
                # Add request_id to all logs if not already present
                if "request_id" not in extra:
                    extra["request_id"] = get_request_id()
                    
                logger._log(level, msg, (), extra=extra)
        
        # Add custom methods to the logger
        logger.debug_data = lambda msg, data=None, **kwargs: log_with_data(logging.DEBUG, msg, data, **kwargs)
        logger.info_data = lambda msg, data=None, **kwargs: log_with_data(logging.INFO, msg, data, **kwargs)
        logger.warning_data = lambda msg, data=None, **kwargs: log_with_data(logging.WARNING, msg, data, **kwargs)
        logger.error_data = lambda msg, data=None, **kwargs: log_with_data(logging.ERROR, msg, data, **kwargs)
        logger.critical_data = lambda msg, data=None, **kwargs: log_with_data(logging.CRITICAL, msg, data, **kwargs)
    
    # Return the enhanced logger
    return logger
