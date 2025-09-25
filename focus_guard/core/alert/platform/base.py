"""
Platform interface for alert functionality.

This module defines the abstract base class for platform-specific alert functionality.
Each platform implementation must implement this interface to provide consistent
alert capabilities across different operating systems.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class PlatformAlertInterface(ABC):
    """
    Abstract base class for platform-specific alert functionality.
    
    This interface defines the methods that must be implemented by each platform
    to provide alert capabilities. Platform implementations should handle the
    details of showing notifications, playing sounds, and other platform-specific
    alert functionality.
    """
    
    @abstractmethod
    def show_notification(self, title: str, message: str, level: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Show a platform-native notification.
        
        Args:
            title: Title of the notification
            message: Content of the notification
            level: Alert level ("normal", "warning", "critical")
            options: Additional platform-specific options
                - app_name: Name of the application causing the alert
                - duration: How long to show the notification (seconds)
                - window_rect: Position and size of the window to show near
                - icon: Path to icon file or icon type
                - sound: Whether to play a sound with the notification
            
        Returns:
            bool: True if notification was shown successfully
        """
        pass
    
    @abstractmethod
    def play_sound(self, sound_type: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Play a sound alert.
        
        Args:
            sound_type: Type of sound to play ("normal", "warning", "critical")
            options: Additional options
                - volume: Sound volume (0.0 to 1.0)
                - repeat_count: Number of times to repeat the sound
                - custom_sound: Path to a custom sound file
            
        Returns:
            bool: True if sound was played successfully
        """
        pass
    
    @abstractmethod
    def show_blocking_alert(self, title: str, message: str, level: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Show a blocking alert that requires user acknowledgment.
        
        Args:
            title: Title of the alert
            message: Content of the alert
            level: Alert level ("normal", "warning", "critical")
            options: Additional platform-specific options
                - app_name: Name of the application causing the alert
                - timeout: Timeout in seconds (0 for no timeout)
                - buttons: List of button labels
                - default_button: Index of default button
            
        Returns:
            bool: True if alert was shown and acknowledged
        """
        pass
    
    @classmethod
    @abstractmethod
    def is_supported(cls) -> bool:
        """
        Check if this platform implementation is supported on the current system.
        
        Returns:
            bool: True if all dependencies and system requirements are met
        """
        pass
