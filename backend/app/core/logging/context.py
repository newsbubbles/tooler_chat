import time
import asyncio
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Dict, Any

from .config import get_logger

logger = get_logger("app.core.logging.context")

@contextmanager
def log_operation(operation_name: str, log_level: str = "INFO", extra_data: Optional[Dict[str, Any]] = None):
    """Context manager for logging operations with timing information
    
    Args:
        operation_name: Name of the operation to log
        log_level: Log level to use (INFO, DEBUG, etc.)
        extra_data: Additional data to include in logs
    """
    start_time = time.time()
    
    # Data to log
    data = {
        "operation": operation_name
    }
    
    if extra_data:
        data.update(extra_data)
    
    # Log start of operation
    log_func = getattr(logger, log_level.lower(), logger.info)
    log_func_data = getattr(logger, f"{log_level.lower()}_data", logger.info_data)
    
    log_func_data(f"Operation started: {operation_name}", data)
    
    try:
        # Yield control back to the with block
        yield
        
        # Log successful completion
        elapsed = time.time() - start_time
        data["elapsed_ms"] = round(elapsed * 1000)
        data["success"] = True
        
        log_func_data(f"Operation completed: {operation_name} ({elapsed:.3f}s)", data)
        
    except Exception as e:
        # Log error
        elapsed = time.time() - start_time
        data["elapsed_ms"] = round(elapsed * 1000)
        data["success"] = False
        data["error"] = {
            "type": type(e).__name__,
            "message": str(e)
        }
        
        logger.error_data(f"Operation failed: {operation_name} ({elapsed:.3f}s)", data, exc_info=True)
        
        # Re-raise the exception
        raise


@asynccontextmanager
async def async_log_operation(operation_name: str, log_level: str = "INFO", extra_data: Optional[Dict[str, Any]] = None):
    """Async context manager for logging operations with timing information
    
    Args:
        operation_name: Name of the operation to log
        log_level: Log level to use (INFO, DEBUG, etc.)
        extra_data: Additional data to include in logs
    """
    start_time = time.time()
    
    # Data to log
    data = {
        "operation": operation_name
    }
    
    if extra_data:
        data.update(extra_data)
    
    # Log start of operation
    log_func = getattr(logger, log_level.lower(), logger.info)
    log_func_data = getattr(logger, f"{log_level.lower()}_data", logger.info_data)
    
    log_func_data(f"Async operation started: {operation_name}", data)
    
    try:
        # Yield control back to the with block
        yield
        
        # Log successful completion
        elapsed = time.time() - start_time
        data["elapsed_ms"] = round(elapsed * 1000)
        data["success"] = True
        
        log_func_data(f"Async operation completed: {operation_name} ({elapsed:.3f}s)", data)
        
    except Exception as e:
        # Log error
        elapsed = time.time() - start_time
        data["elapsed_ms"] = round(elapsed * 1000)
        data["success"] = False
        data["error"] = {
            "type": type(e).__name__,
            "message": str(e)
        }
        
        logger.error_data(f"Async operation failed: {operation_name} ({elapsed:.3f}s)", data, exc_info=True)
        
        # Re-raise the exception
        raise