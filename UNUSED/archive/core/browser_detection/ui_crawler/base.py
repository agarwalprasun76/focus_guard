# focus_guard/core/browser_detection/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class TabInfo:
    title: str
    url: str
    active: bool = False
    window_handle: Any = None
    is_private: bool = False
    browser_name: str = ""
    source: str = ""  # e.g., 'cdp' or 'uia'

@dataclass
class BrowserInfo:
    name: str
    pid: int
    path: str
    tabs: List[TabInfo]

class BrowserDetector(ABC):
    """Base class for platform-specific browser detectors."""
    
    @abstractmethod
    def get_browser_windows(self) -> List[BrowserInfo]:
        """Get information about open browser windows and their tabs."""
        pass