"""
Tab model definitions.

This module defines data models for browser tab-related entities.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, Optional
from datetime import datetime


class TabEvent(Enum):
    """Types of tab events."""
    CREATED = auto()
    UPDATED = auto()
    ACTIVATED = auto()
    REMOVED = auto()
    REPLACED = auto()
    MOVED = auto()


@dataclass
class Tab:
    """Represents a browser tab."""
    id: int
    window_id: int
    url: str
    title: str
    browser_id: str
    domain: Optional[str] = None
    favicon: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['Tab']:
        """Create a Tab instance from a dictionary.
        
        Args:
            data: Dictionary containing tab data
            
        Returns:
            Optional[Tab]: New Tab instance or None if data is invalid
        """
        try:
            # Extract the domain from the URL if not provided
            domain = data.get("domain")
            if not domain and "url" in data:
                from urllib.parse import urlparse
                try:
                    parsed_url = urlparse(data["url"])
                    domain = parsed_url.netloc
                except Exception:
                    domain = None
            
            # Create timestamps if provided as strings
            created_at = data.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    created_at = None
            
            updated_at = data.get("updated_at")
            if isinstance(updated_at, str):
                try:
                    updated_at = datetime.fromisoformat(updated_at)
                except ValueError:
                    updated_at = None
            
            return cls(
                id=data.get("id") or data.get("tabId", 0),
                window_id=data.get("windowId") or data.get("window_id", 0),
                url=data.get("url", ""),
                title=data.get("title", ""),
                browser_id=data.get("browserId") or data.get("browser_id", "unknown"),
                domain=domain,
                favicon=data.get("favIconUrl") or data.get("favicon"),
                created_at=created_at or datetime.now(),
                updated_at=updated_at or datetime.now(),
                is_active=data.get("active", False),
                metadata=data
            )
        except Exception:
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Tab instance to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the Tab
        """
        return {
            "id": self.id,
            "windowId": self.window_id,
            "url": self.url,
            "title": self.title,
            "browserId": self.browser_id,
            "domain": self.domain,
            "favIconUrl": self.favicon,
            "active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
