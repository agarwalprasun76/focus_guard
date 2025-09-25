"""
Central configuration for the FocusGuard application.
"""
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    # Network Configuration
    SERVER_HOST: str = "127.0.0.1"  # Bind to localhost only for security
    SERVER_PORT: int = 5000          # Default port, can be overridden by env
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Browser Configuration
    SUPPORTED_BROWSERS: list = ["msedge"]
    
    # Timeouts (in seconds)
    SERVER_STARTUP_TIMEOUT: int = 5
    REQUEST_TIMEOUT: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def init(cls) -> None:
        """Initialize configuration with environment overrides."""
        # Create necessary directories
        cls.LOGS_DIR.mkdir(exist_ok=True)
        
        # Apply environment overrides
        if "FG_SERVER_PORT" in os.environ:
            cls.SERVER_PORT = int(os.environ["FG_SERVER_PORT"])
            
        if "FG_LOG_LEVEL" in os.environ:
            cls.LOG__LEVEL = os.environ["FG_LOG_LEVEL"].upper()

# Initialize the configuration
Config.init()
