"""
Core activity monitoring functionality.

This module provides the main ActivityMonitor class that serves as the primary
interface for the activity monitoring system.
"""

from typing import Optional, List, Dict, Any, Callable
import logging
from datetime import datetime

from focus_guard.core.activity.models import WindowInfo, ActivityEvent
from focus_guard.core.activity.platform.base import PlatformActivityMonitor
from focus_guard.core.activity.platform.windows import WindowsActivityMonitor
from focus_guard.core.activity.browser.tab_monitor import BrowserTabMonitor
from focus_guard.core.domain.utils import normalize_url, extract_domain_from_url
from focus_guard.core.activity.idle_detector import IdleDetector, IdleConfiguration, IdleEvent, IdleState

class ActivityMonitor:
    """
    Monitor user activity across applications and browser tabs.
    
    This class provides methods for retrieving information about the active window
    and other visible windows on the screen. It abstracts away platform-specific
    details and integrates with browser monitoring for enhanced tab information.
    Enhanced with comprehensive idle detection and active usage tracking.
    """
    
    def __init__(self, idle_config: Optional[IdleConfiguration] = None):
        """
        Initialize the ActivityMonitor.
        
        Args:
            idle_config: Configuration for idle detection thresholds
        """
        self._platform_impl = None
        self._browser_monitor = None
        self._idle_detector = IdleDetector(idle_config)
        self._idle_callbacks: List[Callable[[IdleEvent], None]] = []
        
    @property
    def platform_impl(self):
        """
        Get the platform-specific implementation.
        
        Returns:
            PlatformActivityMonitor: The platform-specific implementation.
        """
        if self._platform_impl is None:
            from focus_guard.core.activity.platform import get_platform_implementation
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
            from focus_guard.core.activity.browser.tab_monitor import BrowserTabMonitor
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
                        normalized_url = normalize_url(url_str)
                        if normalized_url:
                            window_info.url = normalized_url
                            window_info.domain = extract_domain_from_url(normalized_url)
            except Exception as e:
                # Fall back to window title parsing if browser integration fails
                url_str = self._extract_url_from_title(window_info.window_title)
                if url_str:
                    normalized_url = normalize_url(url_str)
                    if normalized_url:
                        window_info.url = normalized_url
                        window_info.domain = extract_domain_from_url(normalized_url)
                
        return window_info
    
    def get_idle_time_seconds(self) -> float:
        """
        Get the system idle time in seconds using enhanced idle detector.
        
        Returns:
            float: Idle time in seconds, or 0.0 if unable to determine.
        """
        return self._idle_detector.get_idle_time_seconds()
    
    def get_idle_state(self) -> IdleState:
        """
        Get the current idle state.
        
        Returns:
            IdleState: Current idle state (ACTIVE, SHORT_IDLE, MEDIUM_IDLE, LONG_IDLE)
        """
        return self._idle_detector.get_current_state()
    
    def is_idle(self, threshold_seconds: float = None) -> bool:
        """
        Check if system is currently idle beyond threshold.
        
        Args:
            threshold_seconds: Custom threshold, or use short_idle_threshold if None
            
        Returns:
            bool: True if system is idle beyond threshold
        """
        return self._idle_detector.is_idle(threshold_seconds)
    
    def is_active(self) -> bool:
        """
        Check if system is currently active (not idle).
        
        Returns:
            bool: True if system is active
        """
        return self._idle_detector.is_active()
    
    def start_idle_monitoring(self):
        """Start continuous idle state monitoring."""
        self._idle_detector.start_monitoring()
    
    def stop_idle_monitoring(self):
        """Stop idle state monitoring."""
        self._idle_detector.stop_monitoring()
    
    def add_idle_callback(self, callback: Callable[[IdleEvent], None]):
        """
        Add a callback for idle state changes.
        
        Args:
            callback: Function to call when idle state changes
        """
        self._idle_detector.add_state_change_callback(callback)
        self._idle_callbacks.append(callback)
    
    def remove_idle_callback(self, callback: Callable[[IdleEvent], None]):
        """
        Remove an idle state change callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        self._idle_detector.remove_state_change_callback(callback)
        if callback in self._idle_callbacks:
            self._idle_callbacks.remove(callback)
    
    def get_idle_statistics(self) -> Dict[str, Any]:
        """
        Get idle detection statistics.
        
        Returns:
            Dict[str, Any]: Statistics including active/idle time, percentages, etc.
        """
        return self._idle_detector.get_statistics()
    
    def get_recent_idle_periods(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get idle periods from the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List[Dict[str, Any]]: List of idle periods with start/end times and durations
        """
        return self._idle_detector.get_recent_idle_periods(hours)
        
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
