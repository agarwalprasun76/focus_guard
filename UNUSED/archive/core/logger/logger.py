"""
FocusGuard Logger Module
Provides centralized logging functionality for the entire application.
"""
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

class Logger:
    """
    Centralized logging for FocusGuard.
    Supports console output and file logging with configurable levels.
    """
    
    # Log levels
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    # Default format strings
    DEFAULT_CONSOLE_FORMAT = "[%(levelname)s] %(message)s"
    DEFAULT_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the logger with optional configuration.
        
        Args:
            config: Configuration dictionary with the following optional keys:
                - log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                - log_to_file: Whether to log to file (default: False)
                - log_dir: Directory for log files (default: 'logs')
                - log_file: Log file name (default: 'focus_guard_{date}.log')
                - console_format: Format string for console output
                - file_format: Format string for file output
        """
        self.config = config or {}
        self.log_level = self.config.get("log_level", logging.INFO)
        self.log_to_file = self.config.get("log_to_file", False)
        self.log_dir = self.config.get("log_dir", "logs")
        self.log_file = self.config.get("log_file", f"focus_guard_{datetime.now().strftime('%Y-%m-%d')}.log")
        self.console_format = self.config.get("console_format", self.DEFAULT_CONSOLE_FORMAT)
        self.file_format = self.config.get("file_format", self.DEFAULT_FILE_FORMAT)
        
        # Initialize root logger
        self.root_logger = logging.getLogger("focus_guard")
        self.root_logger.setLevel(self.log_level)
        self.root_logger.handlers = []  # Clear any existing handlers
        
        # Add console handler
        self._setup_console_handler()
        
        # Add file handler if enabled
        if self.log_to_file:
            self._setup_file_handler()
    
    def _setup_console_handler(self):
        """Set up console logging handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(self.console_format)
        console_handler.setFormatter(console_formatter)
        self.root_logger.addHandler(console_handler)
    
    def _setup_file_handler(self):
        """Set up file logging handler."""
        # Create log directory if it doesn't exist
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # Create file handler
        log_path = os.path.join(self.log_dir, self.log_file)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(self.log_level)
        file_formatter = logging.Formatter(self.file_format)
        file_handler.setFormatter(file_formatter)
        self.root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger for a specific module.
        
        Args:
            name: Name of the module (e.g., 'alert_system', 'activity_monitor')
            
        Returns:
            logging.Logger: Logger instance for the specified module
        """
        return logging.getLogger(f"focus_guard.{name}")

# Global logger instance
_logger_instance = None

def setup_logger(config: Optional[Dict[str, Any]] = None) -> Logger:
    """
    Set up and return the global logger instance.
    
    Args:
        config: Logger configuration
        
    Returns:
        Logger: Global logger instance
    """
    global _logger_instance
    _logger_instance = Logger(config)
    return _logger_instance

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Name of the module (e.g., 'alert_system', 'activity_monitor')
        
    Returns:
        logging.Logger: Logger instance for the specified module with safe Unicode handling
    """
    if _logger_instance is None:
        setup_logger()
    # Get the standard logger first
    logger = _logger_instance.get_logger(name)
    # Wrap it with the safe logger to handle Unicode encoding errors
    from core.logger.safe_logging import SafeLogger
    return SafeLogger(logger)

# Safe print function for cases where logger isn't available
def safe_print(msg):
    """Print a message safely, handling encoding errors."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode())
