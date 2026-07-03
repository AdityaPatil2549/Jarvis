"""
utils/helpers.py - Utility functions for JARVIS-Lite.
"""

import platform
import os
from pathlib import Path
from typing import Optional


def get_os() -> str:
    """Return normalized OS name: 'win', 'mac', or 'linux'."""
    system = platform.system().lower()
    if system == 'windows':
        return 'win'
    elif system == 'darwin':
        return 'mac'
    else:
        return 'linux'


def expand_path(path: str) -> Path:
    """Expand ~ and environment variables in path."""
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def truncate(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_file_size(size_bytes: int) -> str:
    """Format file size to human-readable string."""
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def find_executable(name: str) -> Optional[str]:
    """
    Find executable in system PATH.
    Returns the full path or None if not found.
    """
    import shutil
    return shutil.which(name)
