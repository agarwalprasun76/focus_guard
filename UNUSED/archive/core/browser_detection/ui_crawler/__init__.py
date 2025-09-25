# focus_guard/core/browser_detection/__init__.py
from typing import List, Dict, Any
import platform
from .windows_improved import WindowsBrowserDetector
from .base import BrowserDetector, BrowserInfo

def get_detector() -> BrowserDetector:
    """Get the appropriate browser detector for the current platform."""
    system = platform.system().lower()
    if system == 'windows':
        return WindowsBrowserDetector()
    elif system == 'darwin':  # macOS
        # Will be implemented later
        raise NotImplementedError("macOS support coming soon")
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")

def get_browser_windows() -> List[BrowserInfo]:
    """Get browser windows using the appropriate detector for the current platform."""
    return get_detector().get_browser_windows()