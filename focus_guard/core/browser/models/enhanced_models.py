"""
Enhanced browser models with more descriptive attribute names.

This module provides enhanced versions of the browser and tab models
with more descriptive attribute names for improved code readability.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

from focus_guard.core.browser.models.browser import Browser, BrowserType
from focus_guard.core.browser.models.tab import Tab, TabEvent


@dataclass
class EnhancedBrowser:
    """Enhanced browser model with more descriptive attribute names."""
    browser_id: str
    browser_type: BrowserType
    browser_name: str
    process_id: int
    window_id: Optional[int] = None
    window_title: Optional[str] = None
    executable_path: Optional[str] = None
    version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_browser(cls, browser: Browser) -> 'EnhancedBrowser':
        """Create an EnhancedBrowser from a Browser instance."""
        return cls(
            browser_id=browser.id,
            browser_type=browser.type,
            browser_name=browser.name,
            process_id=browser.process_id,
            window_id=browser.window_id,
            window_title=browser.window_title,
            executable_path=browser.executable_path,
            version=browser.version,
            metadata=browser.metadata
        )
    
    def to_browser(self) -> Browser:
        """Convert to a Browser instance."""
        return Browser(
            id=self.browser_id,
            type=self.browser_type,
            name=self.browser_name,
            process_id=self.process_id,
            window_id=self.window_id,
            window_title=self.window_title,
            executable_path=self.executable_path,
            version=self.version,
            metadata=self.metadata
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedBrowser':
        """Create an EnhancedBrowser from a dictionary."""
        browser = Browser.from_dict(data)
        return cls.from_browser(browser)


@dataclass
class EnhancedTab:
    """Enhanced tab model with more descriptive attribute names."""
    tab_id: int
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
    def from_tab(cls, tab: Tab) -> 'EnhancedTab':
        """Create an EnhancedTab from a Tab instance."""
        return cls(
            tab_id=tab.id,
            window_id=tab.window_id,
            url=tab.url,
            title=tab.title,
            browser_id=tab.browser_id,
            domain=tab.domain,
            favicon=tab.favicon,
            created_at=tab.created_at,
            updated_at=tab.updated_at,
            is_active=tab.is_active,
            metadata=tab.metadata
        )
    
    def to_tab(self) -> Tab:
        """Convert to a Tab instance."""
        return Tab(
            id=self.tab_id,
            window_id=self.window_id,
            url=self.url,
            title=self.title,
            browser_id=self.browser_id,
            domain=self.domain,
            favicon=self.favicon,
            created_at=self.created_at,
            updated_at=self.updated_at,
            is_active=self.is_active,
            metadata=self.metadata
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['EnhancedTab']:
        """Create an EnhancedTab from a dictionary."""
        tab = Tab.from_dict(data)
        if tab:
            return cls.from_tab(tab)
        return None


class EnhancedBrowserDetector:
    """Adapter for BrowserDetector that uses enhanced models."""
    
    def __init__(self, detector):
        self._detector = detector
    
    def get_active_browsers(self) -> List[EnhancedBrowser]:
        """Get active browsers."""
        browsers = self._detector.get_active_browsers()
        return [EnhancedBrowser.from_browser(browser) for browser in browsers]
    
    def get_browser_by_id(self, browser_id: str) -> Optional[EnhancedBrowser]:
        """Get browser by ID."""
        browser = self._detector.get_browser_by_id(browser_id)
        if browser:
            return EnhancedBrowser.from_browser(browser)
        return None


class EnhancedTabTracker:
    """Adapter for TabTracker that uses enhanced models."""
    
    def __init__(self, tracker):
        self._tracker = tracker
        self._event_handlers = {
            TabEvent.CREATED: [],
            TabEvent.UPDATED: [],
            TabEvent.REMOVED: [],
            TabEvent.ACTIVATED: [],
            TabEvent.REPLACED: [],
            TabEvent.MOVED: []
        }
        
        # Register handlers for the underlying tracker
        for event_type in TabEvent:
            self._tracker.register_tab_event_handler(
                event_type, 
                lambda tab, event=event_type: self._handle_tab_event(event, tab)
            )
    
    def _handle_tab_event(self, event_type: TabEvent, tab: Tab):
        """Handle tab events from the underlying tracker."""
        enhanced_tab = EnhancedTab.from_tab(tab)
        for handler in self._event_handlers.get(event_type, []):
            handler(enhanced_tab)
    
    def start(self):
        """Start tab tracking."""
        if hasattr(self._tracker, "start"):
            self._tracker.start()
    
    def stop(self):
        """Stop tab tracking."""
        if hasattr(self._tracker, "stop"):
            self._tracker.stop()
    
    def get_all_tabs(self) -> List[EnhancedTab]:
        """Get all tabs."""
        tabs = self._tracker.get_all_tabs()
        return [EnhancedTab.from_tab(tab) for tab in tabs]
    
    def get_active_tab(self) -> Optional[EnhancedTab]:
        """Get active tab."""
        tab = self._tracker.get_active_tab()
        if tab:
            return EnhancedTab.from_tab(tab)
        return None
    
    def register_tab_event_handler(self, event_type: TabEvent, handler):
        """Register tab event handler."""
        self._event_handlers[event_type].append(handler)


class EnhancedTabBlocker:
    """Adapter for TabBlocker that uses enhanced models."""
    
    def __init__(self, blocker):
        self._blocker = blocker
    
    def block_domain(self, domain: str, expiration_time=None) -> bool:
        """Block a domain."""
        return self._blocker.block_domain(domain, expiration_time)
    
    def unblock_domain(self, domain: str) -> bool:
        """Unblock a domain."""
        return self._blocker.unblock_domain(domain)
    
    def is_domain_blocked(self, domain: str) -> bool:
        """Check if a domain is blocked."""
        return self._blocker.is_domain_blocked(domain)
    
    def close_tab(self, tab: EnhancedTab, reason: str = None) -> bool:
        """Close a tab."""
        return self._blocker.close_tab(tab.to_tab(), reason)
    
    def close_tabs_by_domain(self, domain: str, reason: str = None) -> bool:
        """Close tabs by domain."""
        return self._blocker.close_tabs_by_domain(domain, reason)
