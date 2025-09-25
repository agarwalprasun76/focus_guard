"""
Browser model definitions.

This module defines data models for browser-related entities.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, Optional


class BrowserType(Enum):
    """Types of supported browsers."""
    CHROME = auto()
    FIREFOX = auto()
    EDGE = auto()
    SAFARI = auto()
    OPERA = auto()
    BRAVE = auto()
    UNKNOWN = auto()
    
    @classmethod
    def from_name(cls, browser_name: str) -> 'BrowserType':
        """Convert a browser name string to a BrowserType enum.
        
        Args:
            browser_name: Name of the browser
            
        Returns:
            BrowserType: Corresponding browser type enum
        """
        name_lower = browser_name.lower()
        if "chrome" in name_lower:
            return cls.CHROME
        elif "firefox" in name_lower:
            return cls.FIREFOX
        elif "edge" in name_lower:
            return cls.EDGE
        elif "safari" in name_lower:
            return cls.SAFARI
        elif "opera" in name_lower:
            return cls.OPERA
        elif "brave" in name_lower:
            return cls.BRAVE
        else:
            return cls.UNKNOWN


@dataclass
class Browser:
    """Represents a browser instance."""
    id: str
    type: BrowserType
    name: str
    process_id: int
    window_id: Optional[int] = None
    window_title: Optional[str] = None
    executable_path: Optional[str] = None
    version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Browser':
        """Create a Browser instance from a dictionary.
        
        Args:
            data: Dictionary containing browser data
            
        Returns:
            Browser: New Browser instance
        """
        browser_type = BrowserType.from_name(data.get("browser_name", ""))
        
        return cls(
            id=data.get("id", ""),
            type=browser_type,
            name=data.get("browser_name", "Unknown"),
            process_id=data.get("pid", 0),
            window_id=data.get("window_id"),
            window_title=data.get("window_title"),
            executable_path=data.get("executable_path"),
            version=data.get("version"),
            metadata=data
        )
