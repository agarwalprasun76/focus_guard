"""
Windows-specific implementation of session monitoring.

This module provides the Windows-specific implementation for detecting
user session events (login, logout, lock, unlock) using Win32 API.
"""

import sys
import time
import logging
import threading
import ctypes
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime

from focus_guard.core.activity.platform.session_monitor import SessionMonitor, SessionEvent


class WindowsSessionMonitor(SessionMonitor):
    """
    Windows-specific implementation of session monitoring.
    
    This class provides Windows-specific implementations for detecting
    user session events using Win32 API and Windows Management Instrumentation (WMI).
    """
    
    # Windows session change constants
    WTS_SESSION_LOCK = 0x7
    WTS_SESSION_UNLOCK = 0x8
    WTS_SESSION_LOGON = 0x5
    WTS_SESSION_LOGOFF = 0x6
    
    def __init__(self):
        """Initialize the Windows session monitor."""
        super().__init__()
        
        # Last known session state
        self.last_session_state = None
        
        # Initialize WMI connection
        self._init_wmi()
    
    def _init_wmi(self):
        """Initialize Windows Management Instrumentation connection."""
        try:
            import wmi
            self.wmi_conn = wmi.WMI()
            self.logger.info("WMI connection initialized")
        except ImportError:
            self.logger.warning("WMI module not available. Some session detection features will be limited.")
            self.wmi_conn = None
        except Exception as e:
            self.logger.error(f"Error initializing WMI: {e}")
            self.wmi_conn = None
    
    def _monitoring_loop(self):
        """
        Main monitoring loop that runs in a separate thread.
        
        This method polls for session state changes using multiple detection methods:
        1. Win32 API for session state
        2. WMI for user session events
        3. GetLastInputInfo for idle detection
        """
        self.logger.info("Windows session monitoring loop started")
        
        # Initial state check
        self._check_current_session_state()
        
        while self.running:
            try:
                # Check session state
                self._check_current_session_state()
                
                # Check for idle state (could indicate screen lock)
                self._check_idle_state()
                
                # Sleep for a bit to avoid high CPU usage
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in session monitoring loop: {e}")
                time.sleep(5)  # Sleep longer on error
    
    def _check_current_session_state(self):
        """Check the current session state and notify on changes."""
        try:
            # Get current session state
            session_state = self._get_session_state()
            
            # If state changed, notify listeners
            if session_state != self.last_session_state and session_state is not None:
                if session_state == "Locked":
                    self.notify_listeners(SessionEvent.LOCK, {"timestamp": datetime.now().isoformat()})
                elif session_state == "Unlocked" and self.last_session_state == "Locked":
                    self.notify_listeners(SessionEvent.UNLOCK, {"timestamp": datetime.now().isoformat()})
                elif session_state == "LoggedOff":
                    self.notify_listeners(SessionEvent.LOGOUT, {"timestamp": datetime.now().isoformat()})
                elif session_state == "LoggedOn" and self.last_session_state == "LoggedOff":
                    self.notify_listeners(SessionEvent.LOGIN, {"timestamp": datetime.now().isoformat()})
                
                self.last_session_state = session_state
        except Exception as e:
            self.logger.error(f"Error checking session state: {e}")
    
    def _get_session_state(self) -> Optional[str]:
        """
        Get the current session state.
        
        Returns:
            Optional[str]: Session state as string ("Locked", "Unlocked", "LoggedOn", "LoggedOff")
                          or None if it cannot be determined.
        """
        try:
            # Try using WMI first if available
            if self.wmi_conn:
                for os in self.wmi_conn.Win32_OperatingSystem():
                    if os.NumberOfUsers == 0:
                        return "LoggedOff"
                    else:
                        # Check if screen is locked
                        if self._is_workstation_locked():
                            return "Locked"
                        else:
                            return "Unlocked"
            
            # Fallback to Win32 API
            if self._is_workstation_locked():
                return "Locked"
            else:
                # Check if anyone is logged in
                if self._get_active_user_name():
                    return "Unlocked"
                else:
                    return "LoggedOff"
        except Exception as e:
            self.logger.error(f"Error getting session state: {e}")
            return None
    
    def _is_workstation_locked(self) -> bool:
        """
        Check if the workstation is locked.
        
        Returns:
            bool: True if the workstation is locked, False otherwise.
        """
        try:
            import ctypes
            from ctypes.wintypes import DWORD
            
            # OpenInputDesktop will fail if workstation is locked
            hDesktop = ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_SWITCHDESKTOP
            if hDesktop == 0:  # NULL handle means locked
                return True
            else:
                ctypes.windll.user32.CloseDesktop(hDesktop)
                return False
        except Exception:
            # If we can't determine, assume not locked
            return False
    
    def _get_active_user_name(self) -> Optional[str]:
        """
        Get the name of the active user.
        
        Returns:
            Optional[str]: Username of the active user, or None if no user is logged in.
        """
        try:
            import ctypes
            from ctypes.wintypes import DWORD
            
            username_size = DWORD(257)  # UNLEN + 1
            username = ctypes.create_unicode_buffer(username_size.value)
            
            if ctypes.windll.advapi32.GetUserNameW(username, ctypes.byref(username_size)):
                return username.value
            else:
                return None
        except Exception:
            return None
    
    def _check_idle_state(self):
        """
        Check if the system is idle (no user input for a long time).
        
        This can be an additional indicator of a locked workstation.
        """
        try:
            idle_time = self._get_idle_time()
            
            # If idle for more than 5 minutes and not already marked as locked,
            # double-check if the workstation is locked
            if idle_time > 300000 and self.last_session_state != "Locked":  # 5 minutes in milliseconds
                if self._is_workstation_locked():
                    self.notify_listeners(SessionEvent.LOCK, {"timestamp": datetime.now().isoformat()})
                    self.last_session_state = "Locked"
        except Exception as e:
            self.logger.error(f"Error checking idle state: {e}")
    
    def _get_idle_time(self) -> int:
        """
        Get the system idle time in milliseconds.
        
        Returns:
            int: Idle time in milliseconds.
        """
        try:
            import ctypes
            
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', ctypes.c_uint),
                    ('dwTime', ctypes.c_uint),
                ]
            
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
            
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
                millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                return millis
            else:
                return 0
        except Exception:
            return 0
    
    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if Windows session monitoring is supported on the current system.
        
        Returns:
            bool: True if this implementation is supported, False otherwise.
        """
        if sys.platform != "win32":
            return False
            
        try:
            import ctypes
            return True
        except ImportError:
            return False


# Factory function to create the appropriate session monitor for the current platform
def create_session_monitor() -> Optional[SessionMonitor]:
    """
    Create a platform-appropriate session monitor.
    
    Returns:
        Optional[SessionMonitor]: A session monitor instance for the current platform,
                                 or None if no supported implementation is available.
    """
    if WindowsSessionMonitor.is_supported():
        return WindowsSessionMonitor()
    
    # Add other platform implementations here when available
    # elif LinuxSessionMonitor.is_supported():
    #     return LinuxSessionMonitor()
    # elif MacOSSessionMonitor.is_supported():
    #     return MacOSSessionMonitor()
    
    return None
