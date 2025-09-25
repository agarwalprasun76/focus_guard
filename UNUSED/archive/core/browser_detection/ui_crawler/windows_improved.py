"""Windows browser detection using CDP and UI Automation."""
from typing import List, Dict, Any

from .browser_tab_info import BrowserTabDetector
from .base import BrowserDetector, BrowserInfo, TabInfo

class WindowsBrowserDetector(BrowserDetector):
    """Windows implementation of browser detection using CDP and UI Automation."""
    
    def __init__(self):
        self.detector = BrowserTabDetector()
    
    def get_browser_windows(self) -> List[BrowserInfo]:
        """Get all open browser windows and their tabs."""
        try:
            # Get browser info using our improved detector
            browser_infos = self.detector.get_browser_tabs()
            
            # Convert to the format expected by the base class
            result = []
            for browser in browser_infos:
                # Create TabInfo objects
                tabs = []
                for tab in browser.tabs:
                    tabs.append(TabInfo(
                        title=tab.title,
                        url=tab.url,
                        active=tab.active,
                        window_handle=tab.window_handle,
                        is_private=tab.is_private,
                        browser_name=tab.browser_name,
                        source=tab.source
                    ))
                
                # Create BrowserInfo object
                result.append(BrowserInfo(
                    name=browser.name,
                    pid=browser.pid,
                    path=browser.path,
                    tabs=tabs
                ))
            
            return result
            
        except Exception as e:
            if __debug__:
                print(f"Error in get_browser_windows: {e}")
                import traceback
                traceback.print_exc()
            return []

# For backward compatibility
WindowsBrowserDetector = WindowsBrowserDetector
