"""
Cross-platform utility functions for getting active window/app info.
"""
from typing import Optional, Dict
import sys
from datetime import datetime
import subprocess

try:
    import win32gui
except ImportError:
    win32gui = None
try:
    import win32process
except ImportError:
    win32process = None
try:
    import psutil
except ImportError:
    psutil = None

def get_window_info(hwnd):
    """Return info about a window handle (hwnd) if visible and not tiny, else None."""
    if sys.platform != "win32" or win32gui is None or win32process is None or psutil is None:
        return None
    if not win32gui.IsWindowVisible(hwnd):
        return None
    rect = win32gui.GetWindowRect(hwnd)
    if rect[2] - rect[0] < 100 or rect[3] - rect[1] < 50:
        # Ignore tiny windows (toolbars, etc.)
        return None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        process = psutil.Process(pid)
        app_name = process.name()
    except Exception:
        app_name = "unknown"
    window_title = win32gui.GetWindowText(hwnd)
    class_name = win32gui.GetClassName(hwnd)
    # Filter out desktop/background windows
    if class_name in ("Progman", "WorkerW") or (not window_title and app_name.lower() == "explorer.exe"):
        return None
    area = (rect[2] - rect[0]) * (rect[3] - rect[1])
    return {
        "hwnd": hwnd,
        "app_name": app_name,
        "window_title": window_title,
        "rect": rect,
        "area": area
    }

def get_screen_area():
    """Return the area (in pixels) of the primary screen (Windows only)."""
    if sys.platform != "win32" or win32gui is None:
        return None
    # Get screen width and height
    try:
        import win32api
        width = win32api.GetSystemMetrics(0)
        height = win32api.GetSystemMetrics(1)
        return width * height
    except Exception:
        return None

def enumerate_top_windows(top_region=200):
    """Return a list of window info dicts for windows at the top of the screen (Windows only)."""
    if sys.platform != "win32" or win32gui is None:
        return []
    windows = []
    def callback(hwnd, extra):
        info = get_window_info(hwnd)
        if info:
            left, top, right, bottom = info["rect"]
            if top <= top_region:
                windows.append(info)
    win32gui.EnumWindows(callback, None)
    return windows

def get_active_window_info() -> Optional[Dict[str, str]]:
    """
    Return info about the currently active window/app.
    On Windows, returns a dict with keys: app_name, window_title, pid, timestamp.
    On Linux (X11), uses wmctrl and psutil to get the same info.
    Returns None if unable to retrieve info.
    Raises NotImplementedError on unsupported OS.
    """
    if sys.platform == "win32":
        try:
            import win32gui
            import win32process
            import psutil
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            app_name = process.name()
            timestamp = datetime.now().isoformat()
            return {
                "app_name": app_name,
                "window_title": window_title,
                "pid": str(pid),
                "timestamp": timestamp
            }
        except Exception as e:
            print(f"[DEBUG][Windows] get_active_window_info exception: {e}")
            return None
    elif sys.platform.startswith("linux"):
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
            print(f"[DEBUG][Linux] get_active_window_info exception: {e}")
            return None
    else:
        raise NotImplementedError("get_active_window_info is only implemented for Windows and Linux (X11).")
