"""
utils/logger.py - Structured logging for JARVIS-Lite.
Provides colored console output and optional JSON file logging.

Source of truth: Implementation_plan.md §3.2
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# ============================================================================
# FORMATTERS
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Console formatter with ANSI color codes matching ui.py Colors class."""

    COLORS = {
        logging.DEBUG:    '\033[38;5;242m',   # Dark Gray
        logging.INFO:     '\033[38;5;39m',    # Bright Blue
        logging.WARNING:  '\033[38;5;214m',   # Orange
        logging.ERROR:    '\033[38;5;196m',   # Red
        logging.CRITICAL: '\033[38;5;196m\033[1m',  # Bold Red
    }
    RESET = '\033[0m'
    DIM = '\033[38;5;242m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        level = record.levelname.ljust(8)
        timestamp = datetime.now().strftime('%H:%M:%S')
        msg = record.getMessage()

        # Include extra context if provided
        extra_parts = []
        for key in ('component', 'duration', 'state'):
            val = getattr(record, key, None)
            if val is not None:
                extra_parts.append(f"{key}={val}")
        extra_str = f" [{', '.join(extra_parts)}]" if extra_parts else ""

        return (
            f"{self.DIM}{timestamp}{self.RESET} "
            f"{color}{level}{self.RESET} "
            f"{msg}{self.DIM}{extra_str}{self.RESET}"
        )


class JSONFormatter(logging.Formatter):
    """File formatter that outputs structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        # Include extra context if provided
        for key in ('component', 'duration', 'state', 'intent', 'error_type'):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        return json.dumps(log_entry, default=str)


# ============================================================================
# MAIN LOGGER
# ============================================================================

class JarvisLogger:
    """
    Centralized logger with structured output.
    Singleton pattern — all modules share the same logger instance.
    """

    _instance: Optional['JarvisLogger'] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, name: str = "jarvis", verbose: bool = False,
                 log_file: Optional[str] = None):
        if self._initialized:
            return
        self._initialized = True

        self.logger = logging.getLogger(name)
        self.logger.handlers.clear()
        level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(level)
        self.logger.propagate = False

        # Console handler with color
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter())
        console_handler.setLevel(level)
        self.logger.addHandler(console_handler)

        # File handler (optional)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_path), encoding='utf-8')
            file_handler.setFormatter(JSONFormatter())
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

    def info(self, msg: str, **kwargs):
        self.logger.info(msg, extra=kwargs)

    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, extra=kwargs)

    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, extra=kwargs)

    def error(self, msg: str, **kwargs):
        self.logger.error(msg, extra=kwargs)

    def critical(self, msg: str, **kwargs):
        self.logger.critical(msg, extra=kwargs)

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        cls._instance = None
