"""
Base class for alert providers in FocusGuard.
"""
from typing import Dict, Any, Optional

class AlertProvider:
    """
    Base class for all alert providers.
    Alert providers are responsible for sending alerts through different channels.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the alert provider.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """
        Send an alert.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if alert was successfully sent
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def get_name(self) -> str:
        """
        Get the name of the alert provider.
        
        Returns:
            str: Name of the alert provider
        """
        return self.__class__.__name__
