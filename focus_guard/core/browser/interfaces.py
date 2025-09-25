"""
Core interfaces for browser integration.

This module defines the interfaces for browser detection, tab tracking,
tab blocking, and extension management.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable

from focus_guard.core.browser.models.browser import Browser, BrowserType
from focus_guard.core.browser.models.tab import Tab, TabEvent


class BrowserDetectorInterface(ABC):
    """Interface for detecting browsers and their windows."""
    
    @abstractmethod
    def get_active_browsers(self) -> List[Browser]:
        """Get a list of active browser instances.
        
        Returns:
            List[Browser]: List of active browser instances
        """
        pass
    
    @abstractmethod
    def get_active_browser_window(self) -> Optional[Browser]:
        """Get the currently active browser window.
        
        Returns:
            Optional[Browser]: Active browser window or None if no browser is active
        """
        pass


class TabTrackerInterface(ABC):
    """Interface for tracking browser tabs."""
    
    @abstractmethod
    def get_all_tabs(self) -> List[Tab]:
        """Get all open tabs across all browsers.
        
        Returns:
            List[Tab]: List of all open tabs
        """
        pass
    
    @abstractmethod
    def get_active_tab(self) -> Optional[Tab]:
        """Get the currently active tab.
        
        Returns:
            Optional[Tab]: Active tab or None if no tab is active
        """
        pass
    
    @abstractmethod
    def register_tab_event_handler(self, event_type: TabEvent, handler: Callable[[Tab], None]) -> None:
        """Register a handler for tab events.
        
        Args:
            event_type: Type of tab event to handle
            handler: Function to call when the event occurs
        """
        pass
    
    @abstractmethod
    def get_tabs_by_domain(self, domain: str) -> List[Tab]:
        """Get all tabs for a specific domain.
        
        Args:
            domain: Domain to filter by
            
        Returns:
            List[Tab]: List of tabs matching the domain
        """
        pass


class TabBlockerInterface(ABC):
    """Interface for blocking browser tabs."""
    
    @abstractmethod
    def close_tab(self, tab: Tab, reason: str = None) -> bool:
        """Close a browser tab.
        
        Args:
            tab: Tab to close
            reason: Reason for closing the tab
            
        Returns:
            bool: True if the tab was closed successfully
        """
        pass
    
    @abstractmethod
    def block_domain(self, domain: str, duration_seconds: int = None) -> bool:
        """Block a domain from being accessed.
        
        Args:
            domain: Domain to block
            duration_seconds: Duration of the block in seconds, or None for permanent
            
        Returns:
            bool: True if the domain was blocked successfully
        """
        pass


class ExtensionManagerInterface(ABC):
    """Interface for managing browser extensions."""
    
    @abstractmethod
    def is_extension_installed(self, browser_type: BrowserType) -> bool:
        """Check if the extension is installed for a browser type.
        
        Args:
            browser_type: Type of browser to check
            
        Returns:
            bool: True if the extension is installed
        """
        pass
    
    @abstractmethod
    def install_extension(self, browser_type: BrowserType) -> bool:
        """Install the extension for a browser type.
        
        Args:
            browser_type: Type of browser to install for
            
        Returns:
            bool: True if the extension was installed successfully
        """
        pass
    
    @abstractmethod
    def update_extension(self, browser_type: BrowserType) -> bool:
        """Update the extension for a browser type.
        
        Args:
            browser_type: Type of browser to update for
            
        Returns:
            bool: True if the extension was updated successfully
        """
        pass


class BrowserIntegrationInterface(ABC):
    """Interface for browser integration functionality."""
    
    @abstractmethod
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """Get all open tabs across all browsers.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about all open tabs
        """
        pass
    
    @abstractmethod
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Get the currently active tab.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the active tab,
                                     or None if no tab is active
        """
        pass
    
    @abstractmethod
    def is_extension_connected(self, browser_name: str = None) -> bool:
        """Check if the browser extension is connected.
        
        Args:
            browser_name: Name of the browser to check (optional)
            
        Returns:
            bool: True if the extension is connected, False otherwise
        """
        pass
    
    @abstractmethod
    def close_tab(self, tab_id: str, window_id: str = None, browser_name: str = None) -> bool:
        """Close a browser tab.
        
        Args:
            tab_id: ID of the tab to close
            window_id: ID of the window containing the tab (optional)
            browser_name: Name of the browser (optional)
            
        Returns:
            bool: True if the tab was closed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def send_command(self, command: str, data: Dict[str, Any], browser_name: str = None) -> bool:
        """Send a command to the browser extension.
        
        Args:
            command: Command to send
            data: Data to send with the command
            browser_name: Name of the browser (optional)
            
        Returns:
            bool: True if the command was sent successfully, False otherwise
        """
        pass


class UsageTrackerInterface(ABC):
    """Interface for tracking browser usage."""
    
    @abstractmethod
    def record_browser_session(self, browser: Browser, start_time: Any) -> str:
        """Record the start of a browser session.
        
        Args:
            browser: Browser instance
            start_time: Session start time
            
        Returns:
            str: Session ID
        """
        pass
    
    @abstractmethod
    def end_browser_session(self, session_id: str, end_time: Any) -> None:
        """Record the end of a browser session.
        
        Args:
            session_id: Session ID returned by record_browser_session
            end_time: Session end time
        """
        pass
    
    @abstractmethod
    def record_tab_event(self, tab: Tab, event_type: TabEvent, timestamp: Any) -> None:
        """Record a tab event.
        
        Args:
            tab: Tab instance
            event_type: Type of event
            timestamp: Event timestamp
        """
        pass
    
    @abstractmethod
    def record_domain_visit(self, domain: str, duration_seconds: float, timestamp: Any) -> None:
        """Record time spent on a domain.
        
        Args:
            domain: Domain name
            duration_seconds: Duration in seconds
            timestamp: Visit timestamp
        """
        pass
