"""
Interfaces for browser extension integration.

This module defines interfaces for browser extension integration components,
including tab server, extension management, and process management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union

@dataclass
class TabServerConfig:
    """Configuration for the tab server."""
    host: str = "127.0.0.1"
    port: int = 5000
    connection_timeout: int = 30  # seconds
    max_command_queue_size: int = 100
    max_retries: int = 3
    retry_delay: int = 1  # seconds


class TabServerInterface(ABC):
    """Interface for tab server implementations."""
    
    @abstractmethod
    def start(self, port: Optional[int] = None) -> bool:
        """
        Start the tab server.
        
        Args:
            port: Optional port override
            
        Returns:
            bool: True if server started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the tab server."""
        pass
    
    @abstractmethod
    def is_port_available(self, port: Optional[int] = None) -> bool:
        """
        Check if a port is available.
        
        Args:
            port: Port to check
            
        Returns:
            bool: True if the port is available, False otherwise
        """
        pass
    
    @abstractmethod
    def update_tabs(self, data: Dict[str, Any]) -> None:
        """
        Update the tab data.
        
        Args:
            data: Dictionary containing tab data
        """
        pass
    
    @abstractmethod
    def add_command(self, command: Dict[str, Any]) -> None:
        """
        Add a command to the command queue for the browser extension.
        
        Args:
            command: Dictionary containing command data
        """
        pass
    
    @abstractmethod
    def get_commands(self, browser_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all pending commands for the browser extension.
        
        Args:
            browser_name: Optional browser name to filter commands by
            
        Returns:
            List of command dictionaries
        """
        pass
    
    @abstractmethod
    def clear_commands(self) -> None:
        """Clear all pending commands after they've been processed."""
        pass
    
    @abstractmethod
    def get_tabs(self) -> List[Dict[str, Any]]:
        """
        Get a thread-safe copy of the tab data.
        
        Returns:
            List of tab dictionaries
        """
        pass
    
    @abstractmethod
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently active tab.
        
        Returns:
            dict or None: The active tab data or None if no active tab
        """
        pass
    
    @abstractmethod
    def is_extension_connected(self, browser_name: Optional[str] = None) -> bool:
        """
        Check if the browser extension is connected.
        
        Args:
            browser_name: Optional browser name to check specific browser connection
            
        Returns:
            bool: True if the extension has sent data recently, False otherwise
        """
        pass


class ProcessManagerInterface(ABC):
    """Interface for process manager implementations."""
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the managed process.
        
        Returns:
            bool: True if process started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the managed process."""
        pass
    
    @abstractmethod
    def restart(self) -> bool:
        """
        Restart the managed process.
        
        Returns:
            bool: True if process restarted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if the managed process is running.
        
        Returns:
            bool: True if the process is running, False otherwise
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the managed process.
        
        Returns:
            dict: Status information
        """
        pass


class ExtensionManagerInterface(ABC):
    """Interface for extension manager implementations."""
    
    @abstractmethod
    def is_extension_installed(self, browser_type: str) -> bool:
        """
        Check if the extension is installed for a browser type.
        
        Args:
            browser_type: Type of browser to check
            
        Returns:
            bool: True if the extension is installed, False otherwise
        """
        pass
    
    @abstractmethod
    def install_extension(self, browser_type: str) -> bool:
        """
        Install the extension for a browser type.
        
        Args:
            browser_type: Type of browser to install for
            
        Returns:
            bool: True if installation was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def update_extension(self, browser_type: str) -> bool:
        """
        Update the extension for a browser type.
        
        Args:
            browser_type: Type of browser to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def verify_extension_connection(self, browser_type: str, timeout_seconds: int = 30) -> bool:
        """
        Verify that the extension is properly connected to the tab server.
        
        Args:
            browser_type: Type of browser to verify
            timeout_seconds: Timeout for verification
            
        Returns:
            bool: True if connection is verified, False otherwise
        """
        pass
