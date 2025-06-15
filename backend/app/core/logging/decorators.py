import functools
import time
import inspect
from typing import Callable, Any, Dict

from .config import get_logger

def log_endpoint(endpoint_name: str = None):
    """Decorator for logging API endpoint calls
    
    Args:
        endpoint_name: Name of the endpoint (defaults to function name)
    """
    def decorator(func):
        # Get appropriate logger
        logger_name = f"app.api.endpoints"
        logger = get_logger(logger_name)
        
        # Get the endpoint name
        nonlocal endpoint_name
        if endpoint_name is None:
            endpoint_name = func.__name__
            
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Extract request parameters for logging (safely)
            log_params = {}
            try:
                # Get function signature
                signature = inspect.signature(func)
                params = signature.parameters
                
                # Extract only primitive types to avoid serialization issues
                for name, value in kwargs.items():
                    if name in params and not name.startswith('_'):
                        # Skip request and response objects
                        if name.lower() in ('request', 'response', 'db', 'current_user'):
                            continue
                            
                        # Skip non-primitive types
                        if isinstance(value, (str, int, float, bool, type(None))):
                            log_params[name] = value
                        else:
                            # For complex types, just log the type
                            log_params[name] = f"<{type(value).__name__}>"
            except Exception as e:
                log_params["error_getting_params"] = str(e)
            
            # Log the call
            logger.info_data(
                f"API Call: {endpoint_name} started",
                {
                    "endpoint": endpoint_name,
                    "parameters": log_params
                }
            )
            
            try:
                # Call the function
                result = await func(*args, **kwargs)
                
                # Calculate elapsed time
                elapsed = time.time() - start_time
                
                # Log the result
                logger.info_data(
                    f"API Call: {endpoint_name} completed in {elapsed:.3f}s",
                    {
                        "endpoint": endpoint_name,
                        "elapsed_ms": round(elapsed * 1000),
                        "success": True,
                        "result_type": type(result).__name__
                    }
                )
                
                return result
            except Exception as e:
                # Calculate elapsed time
                elapsed = time.time() - start_time
                
                # Log the error
                logger.error_data(
                    f"API Call: {endpoint_name} failed in {elapsed:.3f}s",
                    {
                        "endpoint": endpoint_name,
                        "elapsed_ms": round(elapsed * 1000),
                        "success": False,
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e)
                        }
                    },
                    exc_info=True
                )
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator


def log_tool(tool_name: str = None):
    """Decorator for logging tool calls
    
    Args:
        tool_name: Name of the tool (defaults to function name)
    """
    def decorator(func):
        # Get appropriate logger
        logger_name = f"app.tools"
        logger = get_logger(logger_name)
        
        # Get the tool name
        nonlocal tool_name
        if tool_name is None:
            tool_name = func.__name__
            
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Extract parameters for logging
            log_params = {}
            try:
                # Get function signature
                signature = inspect.signature(func)
                params = signature.parameters
                
                # Extract only primitive types to avoid serialization issues
                for name, value in kwargs.items():
                    if name in params and not name.startswith('_'):
                        # Skip non-primitive types
                        if isinstance(value, (str, int, float, bool, type(None))):
                            log_params[name] = value
                        else:
                            # For complex types, just log the type
                            log_params[name] = f"<{type(value).__name__}>"
            except Exception as e:
                log_params["error_getting_params"] = str(e)
            
            # Log the call
            logger.info_data(
                f"Tool Call: {tool_name} started",
                {
                    "tool": tool_name,
                    "parameters": log_params
                }
            )
            
            try:
                # Call the function
                result = await func(*args, **kwargs)
                
                # Calculate elapsed time
                elapsed = time.time() - start_time
                
                # Log the result
                logger.info_data(
                    f"Tool Call: {tool_name} completed in {elapsed:.3f}s",
                    {
                        "tool": tool_name,
                        "elapsed_ms": round(elapsed * 1000),
                        "success": True,
                        "result_type": type(result).__name__
                    }
                )
                
                return result
            except Exception as e:
                # Calculate elapsed time
                elapsed = time.time() - start_time
                
                # Log the error
                logger.error_data(
                    f"Tool Call: {tool_name} failed in {elapsed:.3f}s",
                    {
                        "tool": tool_name,
                        "elapsed_ms": round(elapsed * 1000),
                        "success": False,
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e)
                        }
                    },
                    exc_info=True
                )
                
                # Re-raise the exception
                raise
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Extract parameters for logging (similar to async version)
            log_params = {}
            try:
                # Get function signature
                signature = inspect.signature(func)
                params = signature.parameters
                
                # Extract only primitive types to avoid serialization issues
                for name, value in kwargs.items():
                    if name in params and not name.startswith('_'):
                        # Skip non-primitive types
                        if isinstance(value, (str, int, float, bool, type(None))):
                            log_params[name] = value
                        else:
                            log_params[name] = f"<{type(value).__name__}>"
            except Exception as e:
                log_params["error_getting_params"] = str(e)
            
            # Log the call
            logger.info_data(
                f"Tool Call: {tool_name} started",
                {
                    "tool": tool_name,
                    "parameters": log_params
                }
            )
            
            try:
                # Call the function
                result = func(*args, **kwargs)
                
                # Calculate elapsed time
                elapsed = time.time() - start_time
                
                # Log the result
                logger.info_data(
                    f"Tool Call: {tool_name} completed in {elapsed:.3f}s",
                    {
                        "tool": tool_name,
                        "elapsed_ms": round(elapsed * 1000),
                        "success": True,
                        "result_type": type(result).__name__
                    }
                )
                
                return result
            except Exception as e:
                # Calculate elapsed time
                elapsed = time.time() - start_time
                
                # Log the error
                logger.error_data(
                    f"Tool Call: {tool_name} failed in {elapsed:.3f}s",
                    {
                        "tool": tool_name,
                        "elapsed_ms": round(elapsed * 1000),
                        "success": False,
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e)
                        }
                    },
                    exc_info=True
                )
                
                # Re-raise the exception
                raise
        
        # Return appropriate wrapper based on whether the original function is async or not
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator