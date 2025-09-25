"""
Data models for activity monitoring.

This module defines the core data models used by the activity monitoring system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from core_v2.domain.models import URL, Domain


@dataclass
class WindowInfo:
    """
    Information about a window or application.
    
    This class represents information about a window or application, including
    its title, process name, and other metadata.
    """
    app_name: str
    window_title: str
    pid: str
    timestamp: datetime = field(default_factory=datetime.now)
    hwnd: Optional[int] = None
    rect: Optional[tuple] = None
    area: Optional[int] = None
    percent: Optional[float] = None
    url: Optional[URL] = None
    domain: Optional[Domain] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowInfo':
        """
        Create a WindowInfo object from a dictionary.
        
        Args:
            data: Dictionary containing window information.
            
        Returns:
            WindowInfo: A new WindowInfo object.
        """
        # Convert timestamp string to datetime if needed
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = datetime.now()
        elif timestamp is None:
            timestamp = datetime.now()
            
        # Create WindowInfo object with basic fields
        window_info = cls(
            app_name=data.get('app_name', 'unknown'),
            window_title=data.get('window_title', ''),
            pid=str(data.get('pid', 0)),
            timestamp=timestamp,
            hwnd=data.get('hwnd'),
            rect=data.get('rect'),
            area=data.get('area'),
            percent=data.get('percent')
        )
        
        # Add URL and domain if available
        url_str = data.get('url')
        if url_str:
            from core_v2.utils.domain_utils import create_url_from_string
            url = create_url_from_string(url_str)
            window_info.url = url
            window_info.domain = url.domain
            
        return window_info
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert WindowInfo to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the WindowInfo.
        """
        result = {
            'app_name': self.app_name,
            'window_title': self.window_title,
            'pid': self.pid,
            'timestamp': self.timestamp.isoformat(),
        }
        
        if self.hwnd is not None:
            result['hwnd'] = self.hwnd
        if self.rect is not None:
            result['rect'] = self.rect
        if self.area is not None:
            result['area'] = self.area
        if self.percent is not None:
            result['percent'] = self.percent
        if self.url is not None:
            result['url'] = str(self.url)
        if self.domain is not None:
            result['domain'] = str(self.domain)
            
        return result


@dataclass
class ActivityEvent:
    """
    A timestamped record of user activity.
    
    This class represents a single activity event, such as a window activation
    or browser tab change.
    """
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    window_info: Optional[WindowInfo] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ActivityEvent to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the ActivityEvent.
        """
        result = {
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata.copy(),
        }
        
        if self.window_info:
            result['window_info'] = self.window_info.to_dict()
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActivityEvent':
        """
        Create an ActivityEvent object from a dictionary.
        
        Args:
            data: Dictionary containing activity event data.
            
        Returns:
            ActivityEvent: A new ActivityEvent object.
        """
        # Convert timestamp string to datetime if needed
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = datetime.now()
        elif timestamp is None:
            timestamp = datetime.now()
        
        # Create window_info if available
        window_info = None
        window_info_data = data.get('window_info')
        if window_info_data:
            window_info = WindowInfo.from_dict(window_info_data)
        
        return cls(
            event_type=data.get('event_type', 'unknown'),
            timestamp=timestamp,
            window_info=window_info,
            metadata=data.get('metadata', {})
        )
