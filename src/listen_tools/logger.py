"""
Logging configuration for listen_tools.

Provides a simple, centralized logging setup that writes to both console
and a rotating file in the logs/ directory.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_log_level() -> int:
    """
    Get the log level from environment variable LOG_LEVEL.
    
    Returns:
        Logging level (default: INFO)
    """
    level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return level_map.get(level_name, logging.INFO)


def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.
    
    Args:
        name: Name of the logger (typically __name__ from the calling module)
        log_file: Name of the log file (stored in logs/ directory).
                 If None, derives filename from the module name.
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    log_level = get_log_level()
    logger.setLevel(log_level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create logs directory relative to project root
    # Go up from src/listen_tools to project root
    project_root = Path(__file__).parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Determine log file name from module name if not provided
    if log_file is None:
        # Extract the last component of the module name
        # e.g., "listen_tools.listen_app" -> "listen_app.log"
        module_base = name.split('.')[-1]
        log_file = f"{module_base}.log"
    
    log_path = log_dir / log_file
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # File handler (rotating, max 5MB, keep 3 backups)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    
    # Console handler (only warnings and above to stderr)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
