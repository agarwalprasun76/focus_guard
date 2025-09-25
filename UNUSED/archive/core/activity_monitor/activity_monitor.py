"""
ActivityMonitor: Cross-platform interface for monitoring active applications and windows.
"""
from typing import Optional
from utils.cross_platform import get_active_window_info

class ActivityMonitor:
    def get_active_window(self) -> Optional[dict]:
        """Return info about the currently active window/app."""
        return get_active_window_info()

    def get_top_windows(self, top_region: int = 1000) -> list:
        """Return a list of visible windows on the screen (within top_region px from top), each with a 'percent' key for visible area."""
        from utils.cross_platform import enumerate_top_windows, get_screen_area
        # Use a larger top_region to capture more windows
        windows = enumerate_top_windows(top_region=top_region)
        screen_area = get_screen_area()
        
        # Add PID to each window for easier matching
        for w in windows:
            area = w.get('area', 0)
            w['percent'] = (area / screen_area) if screen_area and area else 0
            # Add PID if not already present
            if 'pid' not in w and 'hwnd' in w:
                try:
                    import win32process
                    _, pid = win32process.GetWindowThreadProcessId(w['hwnd'])
                    w['pid'] = pid
                except Exception:
                    pass
        return windows
