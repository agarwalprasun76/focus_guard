"""Windows browser detection implementation."""
import ctypes
import re
import win32gui
import win32con
import win32process
import psutil
from typing import Dict, List, Optional, Set, Tuple, Callable, Any
from ctypes import wintypes

from ..base import BrowserDetector, BrowserInfo, TabInfo

# Constants for Windows API
GWL_STYLE = -16
WS_VISIBLE = 0x10000000
WS_MINIMIZE = 0x20000000
WS_MAXIMIZE = 0x01000000
WS_EX_TOOLWINDOW = 0x00000080

# Define WNDENUMPROC type for EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

class WindowsBrowserDetector(BrowserDetector):
    """Windows implementation of browser detection using Windows API."""
    
    def __init__(self):
        # Map of process names to (browser_name, handler_function)
        self.browser_map = {
            'chrome.exe': ('Chrome', self._get_chrome_tabs),
            'msedge.exe': ('Edge', self._get_edge_tabs),
            'firefox.exe': ('Firefox', self._get_generic_tabs),
            'browser.exe': ('Edge', self._get_edge_tabs),
            'msedgewebview2.exe': ('Edge', self._get_edge_tabs),
        }
    
    def _get_all_child_windows(self, parent_hwnd: int) -> List[int]:
        """Get all child windows of the given parent window."""
        children = []
        
        def enum_child_windows_callback(hwnd: int, _: int) -> bool:
            children.append(hwnd)
            return True
            
        # Use the Windows API directly for better control
        ctypes.windll.user32.EnumChildWindows(
            parent_hwnd, 
            WNDENUMPROC(enum_child_windows_callback), 
            0
        )
        return children
    
    def _is_browser_main_window(self, hwnd: int) -> bool:
        """Check if the window is a main browser window."""
        try:
            # Get window class name and style
            class_name = win32gui.GetClassName(hwnd).lower()
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            
            # Skip tool windows and windows without title
            if ex_style & win32con.WS_EX_TOOLWINDOW:
                return False
                
            # Check for browser window class names
            browser_classes = ['chrome_widgetwin_1', 'edgechrome_widgetwin_1', 'mozilla']
            if any(cls in class_name for cls in browser_classes):
                return True
                
            # Check window title and style
            title = win32gui.GetWindowText(hwnd)
            if not title.strip():
                return False
                
            # Check if window has a title bar and is sizable
            has_titlebar = style & win32con.WS_CAPTION
            is_sizable = style & win32con.WS_THICKFRAME
            
            return has_titlebar and is_sizable
            
        except Exception as e:
            if __debug__:
                print(f"Error in _is_browser_main_window: {e}")
            return False
    
    def _is_visible_window(self, hwnd: int) -> bool:
        """Check if the window is visible and not a tool window."""
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return False
                
            # Skip tool windows
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex_style & win32con.WS_EX_TOOLWINDOW:
                return False
                
            # Skip windows that are not in the taskbar
            if not win32gui.GetWindow(hwnd, win32con.GW_OWNER):
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                if not (style & win32con.WS_VISIBLE):
                    return False
                    
            return True
            
        except Exception as e:
            if __debug__:
                print(f"Error in _is_visible_window: {e}")
            return False
    
    def _get_chrome_tabs(self, hwnd: int, window_text: str) -> List[TabInfo]:
        """Extract tab information from a Chrome window."""
        tabs = []
        try:
            # First check the main window
            if window_text and window_text not in ['New Tab', 'New Tab - Google Chrome', 'Google Chrome']:
                # Clean up the title (remove " - Google Chrome" suffix if present)
                title = window_text
                if title.endswith(' - Google Chrome'):
                    title = title[:-17]
                    
                tabs.append(TabInfo(
                    title=title,
                    url=f"chrome://tab/{hwnd}",
                    window_handle=hwnd
                ))
            
            # Also check child windows for additional tabs
            for child_hwnd in self._get_all_child_windows(hwnd):
                try:
                    child_text = win32gui.GetWindowText(child_hwnd)
                    if child_text and child_text not in ['New Tab', 'New Tab - Google Chrome', 'Google Chrome']:
                        title = child_text
                        if title.endswith(' - Google Chrome'):
                            title = title[:-17]
                            
                        tabs.append(TabInfo(
                            title=title,
                            url=f"chrome://tab/{child_hwnd}",
                            window_handle=child_hwnd
                        ))
                except Exception:
                    continue
                    
        except Exception as e:
            if __debug__:
                print(f"Error getting Chrome tab info: {e}")
                
        return tabs
    
    def _get_edge_tabs(self, hwnd: int, window_text: str) -> List[TabInfo]:
        """Extract tab information from an Edge window."""
        tabs = []
        try:
            # First check the main window
            if window_text and window_text not in ['New Tab', 'New Tab - Microsoft Edge', 'Microsoft Edge']:
                # Clean up the title (remove " - Microsoft Edge" suffix if present)
                title = window_text
                if title.endswith(' - Microsoft Edge'):
                    title = title[:-18]
                    
                tabs.append(TabInfo(
                    title=title,
                    url=f"edge://tab/{hwnd}",
                    window_handle=hwnd
                ))
            
            # Also check child windows for additional tabs
            for child_hwnd in self._get_all_child_windows(hwnd):
                try:
                    child_text = win32gui.GetWindowText(child_hwnd)
                    if child_text and child_text not in ['New Tab', 'New Tab - Microsoft Edge', 'Microsoft Edge']:
                        title = child_text
                        if title.endswith(' - Microsoft Edge'):
                            title = title[:-18]
                            
                        tabs.append(TabInfo(
                            title=title,
                            url=f"edge://tab/{child_hwnd}",
                            window_handle=child_hwnd
                        ))
                except Exception:
                    continue
                    
        except Exception as e:
            if __debug__:
                print(f"Error getting Edge tab info: {e}")
                
        return tabs
    
    def _get_generic_tabs(self, hwnd: int, window_text: str) -> List[TabInfo]:
        """Generic tab extractor for other browsers."""
        try:
            if not window_text or window_text.startswith('Default IME'):
                return []
                
            return [TabInfo(
                title=window_text,
                url=f"browser://tab/{hwnd}",
                window_handle=hwnd
            )]
        except Exception as e:
            if __debug__:
                print(f"Error in _get_generic_tabs: {e}")
            return []
    
    def get_browser_windows(self) -> List[BrowserInfo]:
        """Get all open browser windows and their tabs."""
        browser_instances: Dict[int, BrowserInfo] = {}
        processed_windows: Set[int] = set()
        
        def enum_windows_callback(hwnd: int, _: int) -> bool:
            try:
                if hwnd in processed_windows:
                    return True
                    
                # Skip if not a browser window and not visible
                if not self._is_browser_main_window(hwnd) and not self._is_visible_window(hwnd):
                    return True
                
                # Get window text and process info
                window_text = win32gui.GetWindowText(hwnd)
                if not window_text:
                    return True
                
                try:
                    # Get process info
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == 0:
                        return True
                        
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    
                    # Find matching browser
                    browser_info = None
                    for exe_name, (browser_name, handler_func) in self.browser_map.items():
                        if exe_name in process_name:
                            # Get or create browser instance
                            if pid not in browser_instances:
                                try:
                                    browser_instances[pid] = BrowserInfo(
                                        name=browser_name,
                                        pid=pid,
                                        path=process.exe(),
                                        tabs=[]
                                    )
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    return True
                                    
                            browser_info = browser_instances[pid]
                            break
                    
                    if not browser_info:
                        return True
                    
                    # Mark this window as processed
                    processed_windows.add(hwnd)
                    
                    # Get the appropriate handler
                    handler = self.browser_map.get(process_name, (None, self._get_generic_tabs))[1]
                    
                    # Get tabs using the handler
                    tabs = handler(hwnd, window_text) if handler else []
                    
                    if tabs:
                        browser_info.tabs.extend(tabs)
                    
                    # Also check child windows for additional tabs
                    for child_hwnd in self._get_all_child_windows(hwnd):
                        if child_hwnd not in processed_windows:
                            try:
                                child_text = win32gui.GetWindowText(child_hwnd)
                                if child_text:  # Only process if there's actual text
                                    child_tabs = handler(child_hwnd, child_text) if handler else []
                                    if child_tabs:
                                        browser_info.tabs.extend(child_tabs)
                                        processed_windows.add(child_hwnd)
                            except Exception as e:
                                if __debug__:
                                    print(f"Error processing child window {child_hwnd}: {e}")
                    
                    return True
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                    if __debug__:
                        print(f"Process error for window {hwnd}: {e}")
                    return True
                    
            except Exception as e:
                if __debug__:
                    import traceback
                    print(f"Error in enum_windows_callback: {e}")
                    print(traceback.format_exc())
                return True
        
        # Enumerate all top-level windows
        win32gui.EnumWindows(enum_windows_callback, None)
        
        # Return the list of browser instances
        return list(browser_instances.values())
