"""
Linux-specific implementation of activity monitoring.

This module provides the Linux-specific implementation of the PlatformActivityMonitor
interface using X11 utilities (wmctrl, xprop) and psutil.
"""

from typing import Optional, Dict, Any, List
import sys
from datetime import datetime
import subprocess

from focus_guard.core.activity.platform.base import PlatformActivityMonitor


class LinuxActivityMonitor(PlatformActivityMonitor):
    """
    Linux-specific implementation of activity monitoring.
    
    This class provides Linux-specific implementations of the methods defined
    in the PlatformActivityMonitor interface using X11 utilities and psutil.
    """
    
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently active window on Linux.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing information about the
                                     active window, or None if no window is active
                                     or information cannot be retrieved.
        """
        try:
            # Get the active window ID
            win_id = subprocess.check_output([
                "xprop", "-root", "_NET_ACTIVE_WINDOW"
            ]).decode()
            
            # Parse window id from output
            if "window id #" in win_id:
                win_id = win_id.strip().split()[-1]
            else:
                win_id = win_id.strip().split()[-1]
                
            if win_id == "0x0":
                return None
                
            # Get window list with PID and title
            wmctrl_out = subprocess.check_output([
                "wmctrl", "-lp"
            ]).decode().splitlines()
            
            # Find the window line
            for line in wmctrl_out:
                parts = line.split()
                if len(parts) < 5:
                    continue
                if parts[0].lower() == win_id.lower():
                    pid = int(parts[2])
                    window_title = " ".join(parts[4:])
                    
                    # Get process name
                    import psutil
                    try:
                        process = psutil.Process(pid)
                        app_name = process.name()
                    except Exception:
                        app_name = "unknown"
                        
                    timestamp = datetime.now().isoformat()
                    
                    return {
                        "app_name": app_name,
                        "window_title": window_title,
                        "pid": str(pid),
                        "timestamp": timestamp
                    }
            return None
        except Exception as e:
            print(f"[DEBUG][Linux] get_active_window exception: {e}")
            return None
    
    def get_top_windows(self, top_region: int = 200) -> List[Dict[str, Any]]:
        """
        Get information about visible windows at the top of the screen on Linux.
        
        Args:
            top_region: Maximum distance from the top of the screen (in pixels)
                       to consider windows.
                       
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing information about
                                 visible windows.
        """
        # TODO: Implement Linux-specific top windows detection
        # This is a stub implementation that returns an empty list
        print("[DEBUG][Linux] get_top_windows not fully implemented yet")
        return []
    
    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if Linux implementation is supported on the current system.
        
        Returns:
            bool: True if this implementation is supported, False otherwise.
        """
        if not sys.platform.startswith("linux"):
            return False
            
        try:
            # Check for required utilities
            subprocess.check_call(["which", "wmctrl"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.check_call(["which", "xprop"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Check for psutil
            import psutil
            
            return True
        except (ImportError, subprocess.CalledProcessError):
            return False
