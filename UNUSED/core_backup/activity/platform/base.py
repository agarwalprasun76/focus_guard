"""
Base interface for platform-specific activity monitoring.

This module defines the abstract base class that all platform-specific
implementations must inherit from.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, ClassVar


class PlatformActivityMonitor(ABC):
    """
    Abstract base class for platform-specific activity monitoring.
    
    This class defines the interface that all platform-specific implementations
    must implement. It provides methods for retrieving information about the
    active window and other visible windows on the screen.
    """
    
    @abstractmethod
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently active window.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the
                                     active window, or None if no window is active
                                     or information cannot be retrieved.
                                     
                                     The dictionary should contain at least the
                                     following keys:
                                     - app_name: Name of the application
                                     - window_title: Title of the window
                                     - pid: Process ID
                                     - timestamp: ISO-formatted timestamp
        """
        pass
    
    @abstractmethod
    def get_top_windows(self, top_region: int = 200) -> List[Dict[str, Any]]:
        """
        Get information about visible windows at the top of the screen.
        
        Args:
            top_region: Maximum distance from the top of the screen (in pixels)
                       to consider windows.
                       
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about
                                 visible windows. Each dictionary should contain
                                 the same keys as returned by get_active_window(),
                                 plus additional keys:
                                 - rect: Tuple of (left, top, right, bottom)
                                 - area: Window area in pixels
                                 - percent: Percentage of screen area occupied
        """
        pass
    
    @classmethod
    @abstractmethod
    def is_supported(cls) -> bool:
        """
        Check if this platform implementation is supported on the current system.
        
        Returns:
            bool: True if this implementation is supported, False otherwise.
        """
        pass
