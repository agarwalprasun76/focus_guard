"""
App blocker provider for FocusGuard.
Temporarily blocks distracting applications.
"""
import sys
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .alert_provider import AlertProvider
from core.logger.logger import get_logger

class AppBlockerProvider(AlertProvider):
    """
    Alert provider that temporarily blocks distracting applications.
    
    This provider can close applications that are causing distractions
    and prevent them from being reopened for a specified duration.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the app blocker provider.
        
        Args:
            config: Configuration dictionary with optional keys:
                - block_duration: Duration in seconds to block apps (default: 300)
                - block_message: Message to show when blocking an app
                - allow_override: Whether to allow user override (default: False)
                - block_levels: Alert levels that trigger blocking (default: ["critical"])
        """
        super().__init__(config or {})
        self.logger = get_logger("alert_system.app_blocker")
        self.blocked_apps = {}  # app_name -> unblock_time
        self.block_duration = self.config.get("block_duration", 300)  # Default: 5 minutes
        self.block_levels = self.config.get("block_levels", ["critical"])
        self.enabled = True
    
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """
        Block the application.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if app was successfully blocked
        """
        if not self.enabled:
            self.logger.debug("App blocker provider is disabled, skipping alert")
            return False
        
        # Only block if the level is in block_levels
        if level not in self.block_levels:
            self.logger.debug(f"Alert level '{level}' doesn't trigger blocking, skipping")
            return False
            
        app_name = window_info.get("app_name")
        if not app_name:
            self.logger.warning("No app_name provided, cannot block")
            return False
            
        # Set block expiration time
        block_until = datetime.now() + timedelta(seconds=self.block_duration)
        self.blocked_apps[app_name] = block_until
        
        self.logger.info(f"Blocking {app_name} until {block_until.isoformat()}")
        
        # Attempt to close the application
        try:
            if sys.platform == "win32":
                # Windows - taskkill
                self.logger.debug(f"Using taskkill to close {app_name}")
                result = subprocess.run([
                    "taskkill", "/F", "/IM", app_name
                ], capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    self.logger.info(f"Successfully closed {app_name}")
                    return True
                else:
                    self.logger.warning(
                        f"Failed to close {app_name}: {result.stderr.strip()}"
                    )
                    return False
                
            elif sys.platform == "darwin":
                # macOS - pkill
                self.logger.debug(f"Using pkill to close {app_name}")
                result = subprocess.run([
                    "pkill", "-f", app_name
                ], capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    self.logger.info(f"Successfully closed {app_name}")
                    return True
                else:
                    self.logger.warning(
                        f"Failed to close {app_name}: {result.stderr.strip()}"
                    )
                    return False
                
            elif sys.platform == "linux":
                # Linux - pkill
                self.logger.debug(f"Using pkill to close {app_name}")
                result = subprocess.run([
                    "pkill", "-f", app_name
                ], capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    self.logger.info(f"Successfully closed {app_name}")
                    return True
                else:
                    self.logger.warning(
                        f"Failed to close {app_name}: {result.stderr.strip()}"
                    )
                    return False
            
            self.logger.warning(f"Unsupported platform: {sys.platform}")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to block application: {e}", exc_info=True)
            return False
            
    def is_blocked(self, app_name: str) -> bool:
        """
        Check if an application is currently blocked.
        
        Args:
            app_name: Name of the application
            
        Returns:
            bool: True if the application is blocked
        """
        if app_name not in self.blocked_apps:
            return False
            
        # Check if block has expired
        if datetime.now() > self.blocked_apps[app_name]:
            self.logger.debug(f"Block for {app_name} has expired, removing from blocked apps")
            del self.blocked_apps[app_name]
            return False
            
        return True
    
    def get_blocked_apps(self) -> Dict[str, datetime]:
        """
        Get all currently blocked apps and their unblock times.
        
        Returns:
            Dict[str, datetime]: Dictionary of app_name -> unblock_time
        """
        # First clean up expired blocks
        current_time = datetime.now()
        expired = [
            app for app, unblock_time in self.blocked_apps.items()
            if current_time > unblock_time
        ]
        
        for app in expired:
            del self.blocked_apps[app]
        
        return self.blocked_apps.copy()
    
    def unblock_app(self, app_name: str) -> bool:
        """
        Manually unblock an application.
        
        Args:
            app_name: Name of the application to unblock
            
        Returns:
            bool: True if the app was unblocked, False if it wasn't blocked
        """
        if app_name in self.blocked_apps:
            del self.blocked_apps[app_name]
            self.logger.info(f"Manually unblocked {app_name}")
            return True
        return False
