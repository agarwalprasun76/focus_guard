"""
Safe logging utilities for handling Unicode and other encoding issues.
"""
import logging
from typing import Any, Optional, Dict

def safe_log(logger: logging.Logger, level: int, msg: str, *args, **kwargs) -> None:
    """
    Safely log a message, handling Unicode encoding errors.
    
    Args:
        logger: Logger instance
        level: Logging level (e.g., logging.INFO)
        msg: Message to log
        *args: Additional positional arguments for logging
        **kwargs: Additional keyword arguments for logging
    """
    try:
        logger.log(level, msg, *args, **kwargs)
    except UnicodeEncodeError:
        # Try to encode problematic characters
        safe_msg = msg.encode('ascii', 'replace').decode('ascii')
        logger.log(level, safe_msg, *args, **kwargs)
        
def safe_debug(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """Safely log a DEBUG message."""
    safe_log(logger, logging.DEBUG, msg, *args, **kwargs)
    
def safe_info(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """Safely log an INFO message."""
    safe_log(logger, logging.INFO, msg, *args, **kwargs)
    
def safe_warning(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """Safely log a WARNING message."""
    safe_log(logger, logging.WARNING, msg, *args, **kwargs)
    
def safe_error(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """Safely log an ERROR message."""
    safe_log(logger, logging.ERROR, msg, *args, **kwargs)
    
def safe_critical(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """Safely log a CRITICAL message."""
    safe_log(logger, logging.CRITICAL, msg, *args, **kwargs)

class SafeLogger:
    """
    A wrapper around a Logger that provides safe logging methods.
    
    This class wraps a Logger instance and provides methods that
    handle Unicode encoding errors gracefully.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize with a Logger instance.
        
        Args:
            logger: Logger instance to wrap
        """
        self.logger = logger
        
    def debug(self, msg: str, *args, **kwargs) -> None:
        """Safely log a DEBUG message."""
        safe_debug(self.logger, msg, *args, **kwargs)
        
    def info(self, msg: str, *args, **kwargs) -> None:
        """Safely log an INFO message."""
        safe_info(self.logger, msg, *args, **kwargs)
        
    def warning(self, msg: str, *args, **kwargs) -> None:
        """Safely log a WARNING message."""
        safe_warning(self.logger, msg, *args, **kwargs)
        
    def error(self, msg: str, *args, **kwargs) -> None:
        """Safely log an ERROR message."""
        safe_error(self.logger, msg, *args, **kwargs)
        
    def critical(self, msg: str, *args, **kwargs) -> None:
        """Safely log a CRITICAL message."""
        safe_critical(self.logger, msg, *args, **kwargs)
        
    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Safely log a message at the specified level."""
        safe_log(self.logger, level, msg, *args, **kwargs)
        
def get_safe_logger(name: str) -> SafeLogger:
    """
    Get a SafeLogger instance for the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        SafeLogger instance
    """
    logger = logging.getLogger(name)
    return SafeLogger(logger)
