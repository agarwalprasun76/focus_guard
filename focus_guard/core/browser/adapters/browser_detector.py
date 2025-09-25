"""
Browser detection adapter implementation.

This module provides the default implementation of the BrowserDetectorInterface.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

from focus_guard.core.browser.interfaces import BrowserDetectorInterface
from focus_guard.core.browser.models.browser import Browser, BrowserType

logger = logging.getLogger(__name__)

class DefaultBrowserDetector(BrowserDetectorInterface):
    """Default implementation of the BrowserDetectorInterface.
    
    This implementation uses psutil to detect running browsers and active windows.
    """
    
    def __init__(self, cache_ttl: float = 2.0):
        """Initialize the browser detector.
        
        Args:
            cache_ttl: Time in seconds to cache browser detection results
        """
        self._browsers = {}
        self._last_update_time = 0
        self._cache_ttl = cache_ttl
    
    def get_active_browsers(self) -> List[Browser]:
        """Get a list of active browser instances."""
        self._update_browser_data()
        return list(self._browsers.values())
    
    def get_active_browser_window(self) -> Optional[Browser]:
        """Get the currently active browser window."""
        self._update_browser_data()
        for browser in self._browsers.values():
            if browser.metadata and browser.metadata.get("is_active", False):
                return browser
        return None
    
    def _update_browser_data(self) -> None:
        """Update browser data if cache is expired."""
        current_time = time.time()
        if current_time - self._last_update_time < self._cache_ttl:
            return
        
        try:
            import psutil
            
            # Clear existing browsers
            self._browsers = {}
            
            # Detect browsers
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name'].lower()
                    if any(b in name for b in ['chrome', 'firefox', 'edge', 'safari', 'opera', 'brave']):
                        browser_type = BrowserType.from_name(name)
                        browser_id = f"{name}-{proc.info['pid']}"
                        
                        self._browsers[browser_id] = Browser(
                            id=browser_id,
                            type=browser_type,
                            name=name,
                            process_id=proc.info['pid'],
                            metadata={
                                "detected_at": datetime.now().isoformat(),
                                "is_active": False  # Would need window focus detection
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except ImportError:
            logger.warning("psutil not available for browser detection")
        
        self._last_update_time = current_time
