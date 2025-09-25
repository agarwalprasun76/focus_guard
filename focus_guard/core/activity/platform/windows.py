"""
Windows-specific implementation of activity monitoring.

This module provides the Windows-specific implementation of the PlatformActivityMonitor
interface using win32gui, win32process, and psutil.
"""

from typing import Optional, Dict, Any, List
import sys
from datetime import datetime

from focus_guard.core.activity.platform.base import PlatformActivityMonitor


class WindowsActivityMonitor(PlatformActivityMonitor):
    """
    Windows-specific implementation of activity monitoring.
    
    This class provides Windows-specific implementations of the methods defined
    in the PlatformActivityMonitor interface using win32gui, win32process, and psutil.
    """
    
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently active window on Windows.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the
                                     active window, or None if no window is active
                                     or information cannot be retrieved.
        """
        try:
            import win32gui
            import win32process
            import psutil
            
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            
            # Skip desktop/background windows
            class_name = win32gui.GetClassName(hwnd)
            if class_name in ("Progman", "WorkerW") or (not window_title and class_name == "Shell_TrayWnd"):
                return None
                
            # Get process information
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                app_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "unknown"
                
            # Get window rect
            rect = win32gui.GetWindowRect(hwnd)
            area = (rect[2] - rect[0]) * (rect[3] - rect[1])
            
            timestamp = datetime.now().isoformat()
            
            return {
                "app_name": app_name,
                "window_title": window_title,
                "pid": str(pid),
                "timestamp": timestamp,
                "hwnd": hwnd,
                "rect": rect,
                "area": area
            }
        except Exception as e:
            print(f"[DEBUG][Windows] get_active_window exception: {e}")
            return None
    
    def get_top_windows(self, top_region: int = 200) -> List[Dict[str, Any]]:
        """
        Get information about visible windows at the top of the screen on Windows.
        
        Args:
            top_region: Maximum distance from the top of the screen (in pixels)
                       to consider windows.
                       
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about
                                 visible windows.
        """
        if not self.is_supported():
            return []
            
        try:
            import win32gui
            
            windows = []
            
            def callback(hwnd, extra):
                if not win32gui.IsWindowVisible(hwnd):
                    return
                    
                rect = win32gui.GetWindowRect(hwnd)
                # Skip tiny windows (toolbars, etc.)
                if rect[2] - rect[0] < 100 or rect[3] - rect[1] < 50:
                    return
                    
                # Skip windows not in the top region
                if rect[1] > top_region:
                    return
                    
                # Skip desktop/background windows
                class_name = win32gui.GetClassName(hwnd)
                if class_name in ("Progman", "WorkerW") or (not win32gui.GetWindowText(hwnd) and class_name == "Shell_TrayWnd"):
                    return
                    
                window_info = self._get_window_info(hwnd)
                if window_info:
                    # Calculate percentage of screen area
                    screen_area = self._get_screen_area()
                    if screen_area and window_info.get('area', 0):
                        window_info['percent'] = window_info['area'] / screen_area
                    else:
                        window_info['percent'] = 0
                        
                    windows.append(window_info)
                    
            win32gui.EnumWindows(callback, None)
            return windows
        except Exception as e:
            print(f"[DEBUG][Windows] get_top_windows exception: {e}")
            return []
    
    def _get_window_info(self, hwnd) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific window handle.
        
        Args:
            hwnd: Window handle.
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the
                                     window, or None if information cannot be retrieved.
        """
        try:
            import win32gui
            import win32process
            import psutil
            
            if not win32gui.IsWindowVisible(hwnd):
                return None
                
            window_title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            area = (rect[2] - rect[0]) * (rect[3] - rect[1])
            
            # Get process information
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                app_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "unknown"
                
            timestamp = datetime.now().isoformat()
            
            return {
                "app_name": app_name,
                "window_title": window_title,
                "pid": str(pid),
                "timestamp": timestamp,
                "hwnd": hwnd,
                "rect": rect,
                "area": area
            }
        except Exception:
            return None
    
    def _get_screen_area(self) -> Optional[int]:
        """
        Get the area of the primary screen in pixels.
        
        Returns:
            Optional[int]: Screen area in pixels, or None if it cannot be retrieved.
        """
        try:
            import win32api
            width = win32api.GetSystemMetrics(0)
            height = win32api.GetSystemMetrics(1)
            return width * height
        except Exception:
            return None
    
    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if Windows implementation is supported on the current system.
        
        Returns:
            bool: True if this implementation is supported, False otherwise.
        """
        if sys.platform != "win32":
            return False
            
        try:
            import win32gui
            import win32process
            import psutil
            return True
        except ImportError:
            return False
