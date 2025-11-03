"""Logging utility using loguru with automatic file detection and rotation."""

import inspect
import os
import sys
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class Logger:
    """Centralized logger using loguru with automatic file detection and rotation."""

    @staticmethod
    def _find_project_root() -> Path:
        """
        Find the project root directory (where src/ is located).

        Returns:
            Path to project root
        """
        # Start from this file's location
        current = Path(__file__).resolve().parent
        while current.parent != current:
            if (current / "src").exists():
                return current
            current = current.parent
        # Fallback to current working directory
        return Path.cwd()

    def __init__(
        self,
        log_dir: Optional[str] = None,
        log_to_stdout: bool = True,
        max_file_size: str = "100 MB",
        retention: str = "10 days",
        json_format: bool = True,
    ):
        """
        Initialize the logger.

        Args:
            log_dir: Directory where log files will be stored (default: logs/ in project root)
            log_to_stdout: Whether to also log to stdout
            max_file_size: Maximum size before rotation (e.g., "100 MB", "1 GB")
            retention: How long to keep rotated logs (e.g., "10 days", "1 week")
            json_format: Whether to store logs in JSON format (default: True)
        """
        # Remove default handler
        logger.remove()

        # Default to logs/ in project root if not specified
        if log_dir is None:
            project_root = self._find_project_root()
            log_path = project_root / "logs"
        else:
            log_path = Path(log_dir)

        # Create log directory if it doesn't exist
        log_path.mkdir(parents=True, exist_ok=True)

        # Configure format with time and file fields
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[file]}</cyan> | "
            "<level>{message}</level>"
        )

        # Add file handler with rotation based on size (memory threshold proxy)
        log_file = log_path / "app.log"
        
        if json_format:
            # JSON format for file storage
            logger.add(
                str(log_file),
                format="{time} | {level} | {extra[file]} | {message}",
                serialize=True,  # Serialize to JSON format
                rotation=max_file_size,  # Rotate when file exceeds this size
                retention=retention,
                compression="zip",  # Compress old logs to save space
                encoding="utf-8",
                enqueue=True,  # Thread-safe logging
                backtrace=True,
                diagnose=True,
            )
        else:
            # Human-readable format for file storage
            logger.add(
                str(log_file),
                format=log_format,
                rotation=max_file_size,  # Rotate when file exceeds this size
                retention=retention,
                compression="zip",  # Compress old logs to save space
                encoding="utf-8",
                enqueue=True,  # Thread-safe logging
                backtrace=True,
                diagnose=True,
            )

        # Optionally add stdout handler (always human-readable)
        if log_to_stdout:
            logger.add(
                sys.stdout,
                format=log_format,
                colorize=True,
                level="INFO",
            )

        self.log_to_stdout = log_to_stdout

    def _get_calling_file(self, depth: int = 2) -> str:
        """
        Automatically detect the file that called the logger.

        Args:
            depth: Stack depth to check (2 = caller's caller)

        Returns:
            Relative path to the calling file
        """
        frame = inspect.stack()[depth]
        filepath = frame.filename

        # Get relative path from project root
        try:
            # Find project root (where src/ is)
            current = Path(filepath).resolve()
            while current.parent != current:
                if (current / "src").exists():
                    project_root = current
                    break
                current = current.parent
            else:
                project_root = Path.cwd()

            rel_path = Path(filepath).resolve().relative_to(project_root)
            return str(rel_path)
        except (ValueError, OSError):
            # Fallback to just filename if relative path fails
            return os.path.basename(filepath)

    def log(
        self,
        message: str,
        level: str = "INFO",
        file: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log a message with automatic file detection.

        Args:
            message: The log message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            file: Optional file name to override automatic detection
            **kwargs: Additional context to include in the log
        """
        # Auto-detect file if not provided
        if file is None:
            file = self._get_calling_file()

        # Bind file to logger context
        bound_logger = logger.bind(file=file)

        # Log with appropriate level
        level_upper = level.upper()
        if level_upper == "DEBUG":
            bound_logger.debug(message, **kwargs)
        elif level_upper == "INFO":
            bound_logger.info(message, **kwargs)
        elif level_upper == "WARNING" or level_upper == "WARN":
            bound_logger.warning(message, **kwargs)
        elif level_upper == "ERROR":
            bound_logger.error(message, **kwargs)
        elif level_upper == "CRITICAL":
            bound_logger.critical(message, **kwargs)
        else:
            bound_logger.info(message, **kwargs)

    def debug(self, message: str, file: Optional[str] = None, **kwargs: Any) -> None:
        """Log a debug message."""
        self.log(message, level="DEBUG", file=file, **kwargs)

    def info(self, message: str, file: Optional[str] = None, **kwargs: Any) -> None:
        """Log an info message."""
        self.log(message, level="INFO", file=file, **kwargs)

    def warning(self, message: str, file: Optional[str] = None, **kwargs: Any) -> None:
        """Log a warning message."""
        self.log(message, level="WARNING", file=file, **kwargs)

    def error(self, message: str, file: Optional[str] = None, **kwargs: Any) -> None:
        """Log an error message."""
        self.log(message, level="ERROR", file=file, **kwargs)

    def critical(self, message: str, file: Optional[str] = None, **kwargs: Any) -> None:
        """Log a critical message."""
        self.log(message, level="CRITICAL", file=file, **kwargs)

    def exception(
        self,
        message: str,
        file: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log an exception with full traceback.

        Args:
            message: The log message
            file: Optional file name to override automatic detection
            **kwargs: Additional context to include in the log
        """
        if file is None:
            file = self._get_calling_file()
        bound_logger = logger.bind(file=file)
        bound_logger.exception(message, **kwargs)


# Global logger instance (lazy initialization)
_global_logger: Optional[Logger] = None


def get_logger(
    log_dir: Optional[str] = None,
    log_to_stdout: bool = True,
    max_file_size: str = "100 MB",
    retention: str = "10 days",
    json_format: bool = True,
) -> Logger:
    """
    Get or create the global logger instance.

    Args:
        log_dir: Directory where log files will be stored (default: logs/ in project root)
        log_to_stdout: Whether to also log to stdout
        max_file_size: Maximum size before rotation
        retention: How long to keep rotated logs
        json_format: Whether to store logs in JSON format (default: True)

    Returns:
        Logger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger(
            log_dir=log_dir,
            log_to_stdout=log_to_stdout,
            max_file_size=max_file_size,
            retention=retention,
            json_format=json_format,
        )
    return _global_logger


# Convenience function for easy logging from anywhere
def log(
    message: str,
    level: str = "INFO",
    file: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Convenience function to log a message using the global logger.

    Args:
        message: The log message
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file: Optional file name to override automatic detection
        **kwargs: Additional context to include in the log
    """
    logger_instance = get_logger()
    logger_instance.log(message, level=level, file=file, **kwargs)

