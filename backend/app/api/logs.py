import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.database import get_db
from app.core.auth import get_current_active_user, get_current_superuser
from app.models.base import User
from app.core.logging import get_logger
from app.core.logging.decorators import log_endpoint

logger = get_logger("app.api.logs")

router = APIRouter(tags=["logs"])

# Path to logs directory
LOGS_DIR = Path("logs")

@router.get("/logs/files")
@log_endpoint("get_log_files")
async def get_log_files(
    current_user: User = Depends(get_current_superuser)  # Only super users can access logs
) -> List[Dict[str, Any]]:
    """Get a list of available log files"""
    try:
        LOGS_DIR.mkdir(exist_ok=True)  # Ensure logs directory exists
        
        files = []
        for file_path in LOGS_DIR.glob("*.log*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": str(file_path)
                })
        
        # Sort files by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return files
    except Exception as e:
        logger.error(f"Error listing log files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing log files: {str(e)}")


@router.get("/logs/{file_name}")
@log_endpoint("get_log_file")
async def get_log_file(
    file_name: str,
    current_user: User = Depends(get_current_superuser),  # Only super users can access logs
    max_lines: int = Query(1000, description="Maximum number of lines to return"),
    filter_level: Optional[str] = Query(None, description="Filter by log level"),
    filter_text: Optional[str] = Query(None, description="Filter by text content")
) -> List[Dict[str, Any]]:
    """Get contents of a log file with filtering options"""
    log_path = LOGS_DIR / file_name
    
    # Basic security check to prevent path traversal
    if ".." in file_name or not log_path.is_file() or not file_name.startswith("tooler_chat") and not file_name.startswith("error") and not file_name.startswith("daily") and not file_name.startswith("api") and not file_name.startswith("tool"):
        raise HTTPException(status_code=404, detail="Log file not found")
    
    try:
        # Read the log file (from end to get latest logs)
        lines = []
        
        with open(log_path, "r") as f:
            # Read from the end to get the latest logs
            all_lines = f.readlines()
            for line in reversed(all_lines[-max_lines:]):
                line = line.strip()
                if not line:
                    continue
                
                # Try to parse as JSON (for structured logs)
                try:
                    log_entry = json.loads(line)
                    
                    # Apply filtering if requested
                    if filter_level and log_entry.get("level", "").lower() != filter_level.lower():
                        continue
                        
                    if filter_text and filter_text.lower() not in json.dumps(log_entry).lower():
                        continue
                        
                    lines.append(log_entry)
                except json.JSONDecodeError:
                    # For non-JSON lines, just add the raw text
                    if filter_text and filter_text.lower() not in line.lower():
                        continue
                    lines.append({"message": line})
        
        return lines
    except Exception as e:
        logger.error(f"Error reading log file {file_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")


@router.get("/logs/{file_name}/download")
@log_endpoint("download_log_file")
async def download_log_file(
    file_name: str,
    current_user: User = Depends(get_current_superuser)  # Only super users can access logs
) -> StreamingResponse:
    """Download a log file"""
    log_path = LOGS_DIR / file_name
    
    # Basic security check to prevent path traversal
    if ".." in file_name or not log_path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    try:
        def log_file_generator():
            with open(log_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        headers = {
            "Content-Disposition": f"attachment; filename={file_name}"
        }
        
        return StreamingResponse(
            log_file_generator(),
            media_type="text/plain",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Error downloading log file {file_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading log file: {str(e)}")


@router.get("/logs/{file_name}/stream")
@log_endpoint("stream_log_file")
async def stream_log_file(
    file_name: str,
    current_user: User = Depends(get_current_superuser),  # Only super users can access logs
    max_lines: int = Query(100, description="Maximum number of lines to stream")
) -> StreamingResponse:
    """Stream a log file (latest lines first)"""
    log_path = LOGS_DIR / file_name
    
    # Basic security check to prevent path traversal
    if ".." in file_name or not log_path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    async def log_stream_generator():
        # Get the initial file size
        file_size = log_path.stat().st_size
        
        # Read initial chunk of log from the end
        with open(log_path, "rb") as f:
            # Seek to max_lines from end
            f.seek(0, 2)  # Seek to end
            end_pos = f.tell()
            
            # Find beginning of the last max_lines
            line_count = 0
            pos = end_pos
            
            while pos > 0 and line_count < max_lines:
                pos -= 1
                f.seek(pos)
                if f.read(1) == b"\n":
                    line_count += 1
                    
            # Read from this position to the end
            f.seek(pos)
            initial_data = f.read()
            
            # Send initial data
            yield initial_data
            
            # Remember last position for tail mode
            last_pos = f.tell()
        
        # Now tail the file
        try:
            while True:
                # Check if file has been updated
                current_size = log_path.stat().st_size
                
                if current_size > last_pos:
                    with open(log_path, "rb") as f:
                        f.seek(last_pos)
                        new_data = f.read()
                        last_pos = f.tell()
                        yield new_data
                
                # Sleep before checking again
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error streaming log file: {str(e)}")
            yield f"\nError streaming log: {str(e)}".encode()
    
    return StreamingResponse(
        log_stream_generator(),
        media_type="text/plain"
    )


@router.get("/logs/system-info")
@log_endpoint("get_system_info")
async def get_system_info(
    current_user: User = Depends(get_current_superuser)  # Only super users can access system info
) -> Dict[str, Any]:
    """Get system information for debugging"""
    try:
        import platform
        import psutil
        import sys
        
        # Get system information
        info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "python": {
                "version": sys.version,
                "implementation": platform.python_implementation(),
                "path": sys.executable
            },
            "memory": {
                "total": round(psutil.virtual_memory().total / (1024 * 1024 * 1024), 2),  # GB
                "available": round(psutil.virtual_memory().available / (1024 * 1024 * 1024), 2),  # GB
                "used": round(psutil.virtual_memory().used / (1024 * 1024 * 1024), 2),  # GB
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": round(psutil.disk_usage('/').total / (1024 * 1024 * 1024), 2),  # GB
                "used": round(psutil.disk_usage('/').used / (1024 * 1024 * 1024), 2),  # GB
                "free": round(psutil.disk_usage('/').free / (1024 * 1024 * 1024), 2),  # GB
                "percent": psutil.disk_usage('/').percent
            },
            "cpu": {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=0.5)
            },
            "time": {
                "now": datetime.datetime.now().isoformat(),
                "utc": datetime.datetime.utcnow().isoformat(),
                "timezone": datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo.tzname(None)
            },
            "env": {
                "PWD": os.environ.get("PWD", ""),
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "HOME": os.environ.get("HOME", "")
            },
            "processes": {
                "count": len(psutil.pids())
            }
        }
        
        # Log this information
        logger.info_data("System information requested", {"system_info": info})
        
        return info
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting system info: {str(e)}")