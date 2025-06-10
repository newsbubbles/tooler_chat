#!/usr/bin/env python

"""
Script to copy necessary files from the tooler project to tooler_chat

This script should be run after cloning both repositories to copy the
project_tools directory from tooler to tooler_chat for the agent to work.

Usage: python scripts/copy_tooler_files.py [tooler_path] [target_path]

By default, it will look for the tooler project at "../tooler" and copy
the files to "./project_tools".
"""

import os
import shutil
import sys
from pathlib import Path


def copy_tooler_files(tooler_path="../tooler", target_path="./project_tools"):
    """Copy necessary files from tooler project to tooler_chat"""
    # Convert to Path objects for easier manipulation
    tooler_path = Path(tooler_path).resolve()
    target_path = Path(target_path).resolve()
    
    # Check if source paths exist
    project_tools_path = tooler_path / "project_tools"
    if not project_tools_path.exists():
        print(f"Error: project_tools directory not found at {project_tools_path}")
        return False
    
    # Create target directory if it doesn't exist
    target_path.mkdir(exist_ok=True, parents=True)
    
    # Copy all .py files from project_tools
    files_copied = 0
    for source_file in project_tools_path.glob("*.py"):
        target_file = target_path / source_file.name
        print(f"Copying {source_file} to {target_file}")
        shutil.copy2(source_file, target_file)
        files_copied += 1
    
    print(f"Copied {files_copied} files from {project_tools_path} to {target_path}")
    return True


if __name__ == "__main__":
    # Get paths from command line arguments if provided
    tooler_path = sys.argv[1] if len(sys.argv) > 1 else "../tooler"
    target_path = sys.argv[2] if len(sys.argv) > 2 else "./project_tools"
    
    success = copy_tooler_files(tooler_path, target_path)
    sys.exit(0 if success else 1)
