"""
Core activity monitoring functionality.

This module provides the main ActivityMonitor class that serves as the primary
interface for the activity monitoring system.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from core_v2.activity.models import WindowInfo, ActivityEvent
from core_v2.domain.models import URL, Domain
from core_v2.utils.domain_utils import create_url_from_string


class ActivityMonitor:
    """
    Monitor user activity across applications and browser tabs.
    
    This class provides methods for retrieving information about the active window
    and other visible windows on the screen. It abstracts away platform-specific
    details and integrates with browser monitoring for enhanced tab information.
    """
    
    def __init__(self):
        """
        Initialize the ActivityMonitor.
        
        This constructor initializes the platform-specific implementation and
        sets up any necessary resources.
        """
        self._platform_impl = None
        self._browser_monitor = None
        
    @property
    def platform_impl(self):
        """
        Get the platform-specific implementation.
        
        Returns:
            PlatformActivityMonitor: The platform-specific implementation.
        """
        if self._platform_impl is None:
            from core_v2.activity.platform import get_platform_implementation
            self._platform_impl = get_platform_implementation()
        return self._platform_impl
    
    @property
    def browser_monitor(self):
        """
        Get the browser tab monitor.
        
        Returns:
            BrowserTabMonitor: The browser tab monitor.
        """
        if self._browser_monitor is None:
            from core_v2.activity.browser.tab_monitor import BrowserTabMonitor
            self._browser_monitor = BrowserTabMonitor()
        return self._browser_monitor
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """
        Get information about the currently active window.
        
        Returns:
            Optional[WindowInfo]: Information about the active window, or None if
                                 no window is active or information cannot be retrieved.
        """
        window_data = self.platform_impl.get_active_window()
        if not window_data:
            return None
            
        # Create WindowInfo object
        window_info = WindowInfo.from_dict(window_data)
        
        # Try to enhance with browser tab information if it's a browser
        if self._is_browser(window_info.app_name):
            try:
                browser_info = self.browser_monitor.get_active_tab()
                if browser_info:
                    # Update window info with browser tab information
                    if 'url' in browser_info:
                        url_str = browser_info['url']
                        url = create_url_from_string(url_str)
                        window_info.url = url
                        window_info.domain = url.domain
            except Exception as e:
                # Fall back to window title parsing if browser integration fails
                url_str = self._extract_url_from_title(window_info.window_title)
                if url_str:
                    url = create_url_from_string(url_str)
                    window_info.url = url
                    window_info.domain = url.domain
                
        return window_info
        
    def get_top_windows(self, top_region: int = 200) -> List[WindowInfo]:
        """
        Get information about visible windows at the top of the screen.
        
        Args:
            top_region: Maximum distance from the top of the screen (in pixels)
                       to consider windows.
                       
        Returns:
            List[WindowInfo]: List of WindowInfo objects for visible windows.
        """
        windows_data = self.platform_impl.get_top_windows(top_region)
        return [WindowInfo.from_dict(window_data) for window_data in windows_data]
    
    def create_activity_event(self, event_type: str, metadata: Dict[str, Any] = None) -> ActivityEvent:
        """
        Create an activity event with the current active window information.
        
        Args:
            event_type: Type of activity event.
            metadata: Additional metadata for the event.
            
        Returns:
            ActivityEvent: A new activity event.
        """
        window_info = self.get_active_window()
        return ActivityEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            window_info=window_info,
            metadata=metadata or {}
        )
    
    def _is_browser(self, app_name: str) -> bool:
        """
        Check if an application is a web browser.
        
        Args:
            app_name: Name of the application.
            
        Returns:
            bool: True if the application is a web browser, False otherwise.
        """
        browsers = ["chrome", "firefox", "msedge", "opera", "safari", "brave"]
        return any(browser in app_name.lower() for browser in browsers)
        
    def _extract_url_from_title(self, title: str) -> Optional[str]:
        """
        Extract URL from window title if possible.
        
        Args:
            title: Window title.
            
        Returns:
            Optional[str]: Extracted URL, or None if no URL could be extracted.
        """
        # Common browser title patterns
        import re
        
        # Pattern: "Page Title - Browser Name"
        # We can't extract URL from this pattern, return None
        
        # Pattern: "Page Title - URL - Browser Name"
        url_pattern = re.compile(r'.*\s+-\s+(https?://\S+)\s+-\s+.*')
        match = url_pattern.match(title)
        if match:
            return match.group(1)
            
        # Pattern: "URL - Browser Name"
        url_pattern = re.compile(r'^(https?://\S+)\s+-\s+.*')
        match = url_pattern.match(title)
        if match:
            return match.group(1)
            
        return None
