# focus_guard/core/browser_detection/windows.py
import win32gui
import win32con
import win32process
import win32api
import psutil
import re
import ctypes
from ctypes import wintypes
from typing import Dict, List, Optional, Tuple, Any, Callable, Set
from ..base import BrowserDetector, BrowserInfo, TabInfo

# Constants for Windows API
GWL_STYLE = -16
WS_VISIBLE = 0x10000000
WS_MINIMIZE = 0x20000000
WS_MAXIMIZE = 0x01000000

# Define WNDENUMPROC type for EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

class WindowsBrowserDetector(BrowserDetector):
    """Windows implementation of browser detection using Windows API."""
    
    def __init__(self):
        # Constants for Windows API
        self.WS_EX_TOOLWINDOW = 0x00000080
        # Map of process names to (browser_name, handler_function)
        self.browser_map = {
            'chrome.exe': ('Chrome', None),  # None means use default handler
            'msedge.exe': ('Edge', self._get_edge_tabs),
            'firefox.exe': ('Firefox', None),
            'browser.exe': ('Edge', self._get_edge_tabs),
            'msedgewebview2.exe': ('Edge', self._get_edge_tabs),
        }
    
    def _get_browser_info(self, process: psutil.Process) -> tuple:
        """Get browser name and process info.
        
        Args:
            process: The process to check
            
        Returns:
            tuple: (browser_name, process_name, handler_func) or (None, None, None) if not a browser
        """
        try:
            process_name = process.name().lower()
            for exe_name, (browser_name, handler_func) in self.browser_map.items():
                if exe_name == process_name:
                    return browser_name, process_name, handler_func
            return None, None, None
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None, None, None
    
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
                
        return tabs if tabs else []
    
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
                
        return tabs if tabs else None
    
    def _get_browser_tabs(self, hwnd: int, process_name: str) -> List[TabInfo]:
        """Get tabs from a browser window."""
        try:
            # First try to get tabs from the main window
            title = win32gui.GetWindowText(hwnd)
            if title and not title.startswith('Data:'):  # Skip data URLs
                return [TabInfo(
                    title=title,
                    url=f"browser://tab/{hwnd}",
                    window_handle=hwnd
                )]
                
            # If no title in main window, try child windows
            tabs = []
            for child_hwnd in self._get_all_child_windows(hwnd):
                try:
                    child_title = win32gui.GetWindowText(child_hwnd)
                    if child_title and not child_title.startswith('Data:'):
                        tabs.append(TabInfo(
                            title=child_title,
                            url=f"browser://tab/{child_hwnd}",
                            window_handle=child_hwnd
                        ))
                except Exception:
                    continue
                    
            return tabs
            
        except Exception as e:
            if __debug__:
                print(f"Error getting tabs from window {hwnd}: {e}")
            return []

    def get_browser_windows(self) -> List[BrowserInfo]:
        """Get all open browser windows and their tabs."""
        browser_instances: Dict[int, BrowserInfo] = {}
        processed_windows: Set[int] = set()
        
        def enum_windows_callback(hwnd, _):
            try:
                if hwnd in processed_windows:
                    return True
                    
                # Get window class and title for debugging
                window_class = win32gui.GetClassName(hwnd)
                window_title = win32gui.GetWindowText(hwnd)
                
                # Skip if not a browser window and not visible
                if not self._is_browser_main_window(hwnd) and not self._is_visible_window(hwnd):
                    if __debug__:
                        print(f"\n--- Window {hwnd} ---")
                        print("Skipping: Not a browser window or visible")
                        print(f"Class: {window_class}")
                        print(f"Title: {window_title}")
                        print(f"Visible: {win32gui.IsWindowVisible(hwnd)}")
                        print(f"Style: {win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE):08x}")
                        print(f"ExStyle: {win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE):08x}")
                    return True
                    
                window_text = win32gui.GetWindowText(hwnd)
                if not window_text:
                    if __debug__:
                        print(f"\n--- Window {hwnd} ---")
                        print("Skipping: No window text")
                    return True
                    
                # Get the process ID and name
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == 0:
                        return True
                        
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    
                    # Check if it's a browser process
                    browser_info = None
                    for browser_name, (exe_name, handler_func) in self.browser_map.items():
                        if exe_name in process_name:
                            # Get or create browser instance
                            if pid not in browser_instances:
                                browser_instances[pid] = BrowserInfo(
                                    name=browser_name,
                                    pid=pid,
                                    path=process.exe(),
                                    tabs=[]
                                )
                            browser_info = browser_instances[pid]
                            break
                    
                    if not browser_info:
                        return True
                    
                    # Mark this window as processed
                    processed_windows.add(hwnd)
                    
                    # Get window title for tab detection
                    window_title = win32gui.GetWindowText(hwnd)
                    
                    # Use the appropriate handler for the browser
                    handler = self.browser_map[browser_info.name][1] or self._get_browser_tabs
                    
                    # Get tabs using the handler
                    if handler == self._get_chrome_tabs:
                        tabs = self._get_chrome_tabs(hwnd, window_title)
                    elif handler == self._get_edge_tabs:
                        tabs = self._get_edge_tabs(hwnd, window_title)
                    else:
                        tabs = handler(hwnd, process_name)
                    
                    if tabs:
                        browser_info.tabs.extend(tabs)
                    
                    # Also check child windows for additional tabs
                    for child_hwnd in self._get_all_child_windows(hwnd):
                        if child_hwnd not in processed_windows:
                            try:
                                child_title = win32gui.GetWindowText(child_hwnd)
                                if handler == self._get_chrome_tabs:
                                    child_tabs = self._get_chrome_tabs(child_hwnd, child_title)
                                elif handler == self._get_edge_tabs:
                                    child_tabs = self._get_edge_tabs(child_hwnd, child_title)
                                else:
                                    child_tabs = handler(child_hwnd, process_name)
                                
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
                
                # Get tabs using the handler
                if handler == self._get_chrome_tabs:
                    tabs = self._get_chrome_tabs(hwnd, window_title)
                elif handler == self._get_edge_tabs:
                    tabs = self._get_edge_tabs(hwnd, window_title)
                else:
                    tabs = handler(hwnd, process_name)
                
                if tabs:
                    browser_info.tabs.extend(tabs)
                
                # Also check child windows for additional tabs
                for child_hwnd in self._get_all_child_windows(hwnd):
                    if child_hwnd not in processed_windows:
                        try:
                            child_title = win32gui.GetWindowText(child_hwnd)
                            if handler == self._get_chrome_tabs:
                                child_tabs = self._get_chrome_tabs(child_hwnd, child_title)
                            elif handler == self._get_edge_tabs:
                                child_tabs = self._get_edge_tabs(child_hwnd, child_title)
                            else:
                                child_tabs = handler(child_hwnd, process_name)
                            
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
                    print(f"Unexpected error processing window {hwnd}: {e}")
                    print(traceback.format_exc())
                return True
            
        except Exception as e:
            if __debug__:
                import traceback
                print(f"Error in enum_windows_callback: {e}")
                print(traceback.format_exc())
        """
        try:
            # Get window class name and title for special handling
            class_name = win32gui.GetClassName(hwnd).lower()
            window_text = win32gui.GetWindowText(hwnd)
            
            # Debug information
            if __debug__:
                print(f"\n--- Window {hwnd} ---")
                print(f"Class: {class_name}")
                print(f"Title: {window_text}")
                print(f"Visible: {win32gui.IsWindowVisible(hwnd)}")
                print(f"Iconic: {win32gui.IsIconic(hwnd)}")
                print(f"Style: {win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE):08x}")
                print(f"ExStyle: {win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE):08x}")
            
            # Special handling for browser windows
            browser_keywords = ['chrome', 'edge', 'microsoftedge', 'mozilla']
            is_browser = any(keyword in class_name.lower() for keyword in browser_keywords)
            
            if is_browser:
                # For browser windows, we're more lenient
                # Only skip if the window is minimized
                if win32gui.IsIconic(hwnd):
                    if __debug__:
                        print("Skipping: Browser window is minimized")
                    return False
                return True
            
            # For non-browser windows, use standard visibility checks
            if not win32gui.IsWindowVisible(hwnd):
                if __debug__:
                    print("Skipping: Window is not visible")
                return False
            
            # Skip tool windows
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex_style & self.WS_EX_TOOLWINDOW:
                if __debug__:
                    print("Skipping: Tool window")
                return False
            
            # Skip windows that are not in the taskbar
            if not win32gui.GetWindow(hwnd, win32con.GW_OWNER):
                if not (win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE) & win32con.WS_VISIBLE):
                    if __debug__:
                        print("Skipping: Window not in taskbar and not visible")
                    return False
            
            if __debug__:
                print("Including window")
            return True
            
        except Exception as e:
            if __debug__:
                print(f"Error in _is_visible_window: {e}")
            return False
    
    def _is_browser_window(self, window_text: str, class_name: str = '') -> bool:
        """Check if the window is a main browser window.
        
        Args:
            window_text: The window title text
            class_name: The window class name (optional)
            
        Returns:
            bool: True if this is a browser window, False otherwise
        """
        # Check for browser window titles
        if any(x in window_text for x in [
            ' - Google Chrome', 
            ' - Microsoft Edge', 
            ' - Mozilla Firefox',
            ' - Brave',
            ' - Opera',
            ' - Vivaldi'
        ]):
            return True
            
        # Check for Edge browser windows (they might not always have the full title)
        if 'msedge' in class_name.lower() and window_text:
            return True
            
        return False