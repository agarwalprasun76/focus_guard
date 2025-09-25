"""
Stub platform implementation for alert functionality.

This module provides a fallback implementation of alert functionality
that logs alerts instead of displaying them when no platform-specific
implementation is available.
"""

import logging
from typing import Dict, Any, Optional

from focus_guard.core.alert.platform.base import PlatformAlertInterface

# Configure logging
logger = logging.getLogger(__name__)


class StubAlertPlatform(PlatformAlertInterface):
    """
    Stub implementation of alert functionality.
    
    This class provides a fallback implementation that logs alerts
    instead of displaying them when no platform-specific implementation
    is available.
    """
    
    def show_notification(self, title: str, message: str, level: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log a notification instead of showing it.
        
        Args:
            title: Title of the notification
            message: Content of the notification
            level: Alert level ("normal", "warning", "critical")
            options: Additional platform-specific options
            
        Returns:
            bool: Always returns True
        """
        options = options or {}
        app_name = options.get("app_name", "Unknown")
        
        logger.info(f"[STUB NOTIFICATION] [{level.upper()}] {app_name} - {title}: {message}")
        return True
    
    def play_sound(self, sound_type: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log a sound alert instead of playing it.
        
        Args:
            sound_type: Type of sound to play ("normal", "warning", "critical")
            options: Additional options
            
        Returns:
            bool: Always returns True
        """
        options = options or {}
        repeat_count = options.get("repeat_count", 1)
        
        logger.info(f"[STUB SOUND] [{sound_type.upper()}] Would play sound {repeat_count} times")
        return True
    
    def show_blocking_alert(self, title: str, message: str, level: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log a blocking alert instead of showing it.
        
        Args:
            title: Title of the alert
            message: Content of the alert
            level: Alert level ("normal", "warning", "critical")
            options: Additional platform-specific options
            
        Returns:
            bool: Always returns True
        """
        options = options or {}
        app_name = options.get("app_name", "Unknown")
        
        logger.info(f"[STUB BLOCKING ALERT] [{level.upper()}] {app_name} - {title}: {message}")
        return True
    
    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if stub implementation is supported.
        
        Returns:
            bool: Always returns True
        """
        return True
