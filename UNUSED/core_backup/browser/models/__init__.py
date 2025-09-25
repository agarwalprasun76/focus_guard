"""
Browser models package.

This package contains data models for browser-related entities.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from core_v2.browser.models.tab import Tab, TabEvent

# Rename Tab to BrowserTab for clarity in imports
BrowserTab = Tab


@dataclass
class BrowserInfo:
    """Information about a browser instance."""
    name: str
    version: str
    executable_path: Optional[str] = None
    is_running: bool = False
    has_extension: bool = False
    extension_enabled: bool = False
    tabs_count: int = 0
    windows_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrowserInfo':
        """Create a BrowserInfo instance from a dictionary.
        
        Args:
            data: Dictionary containing browser data
            
        Returns:
            BrowserInfo: New BrowserInfo instance
        """
        return cls(
            name=data.get("name", ""),
            version=data.get("version", ""),
            executable_path=data.get("executable_path"),
            is_running=data.get("is_running", False),
            has_extension=data.get("has_extension", False),
            extension_enabled=data.get("extension_enabled", False),
            tabs_count=data.get("tabs_count", 0),
            windows_count=data.get("windows_count", 0),
            metadata=data.get("metadata", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the BrowserInfo instance to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the BrowserInfo
        """
        return {
            "name": self.name,
            "version": self.version,
            "executable_path": self.executable_path,
            "is_running": self.is_running,
            "has_extension": self.has_extension,
            "extension_enabled": self.extension_enabled,
            "tabs_count": self.tabs_count,
            "windows_count": self.windows_count,
            "metadata": self.metadata
        }


__all__ = ['Tab', 'BrowserTab', 'TabEvent', 'BrowserInfo']