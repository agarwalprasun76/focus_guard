# Browser Detection & WebExtension MV3 Integration Plan

## Overview

This document outlines the plan for integrating the browser detection and webextension_mv3 components from the legacy `core` module into the new modular `core_v2` architecture. The goal is to preserve the existing functionality while improving modularity, maintainability, and testability.

Unlike other components that require significant refactoring, the browser extension integration is already a complex, well-functioning system that took considerable effort to develop. Therefore, this plan focuses on **minimal rewriting** and instead emphasizes proper integration with the core_v2 architecture.

## Current Architecture

The current browser detection and extension system consists of several interconnected components:

1. **WebExtension MV3**
   - Browser extension using Manifest V3
   - Background script for tab monitoring and communication
   - Native messaging host for communication with the application

2. **Browser Integration**
   - `browser_integration_v2.py`: Main interface for browser integration
   - `tab_server_v2.py`: HTTP server for receiving browser tab data
   - `process_manager_v2.py`: Manages browser processes
   - `tab_tracker_integration_v2.py`: Integrates with the tab tracking system

3. **Browser Detection**
   - Detects browser windows and processes
   - Provides information about active browsers

4. **CDP (Chrome DevTools Protocol) Components**
   - Alternative implementation using CDP for development/testing
   - Not used in production due to security concerns

## Identified Opportunities for Improvement

1. **Modular Integration**
   - Integrate with core_v2 architecture without significant rewriting
   - Maintain backward compatibility for dependent components

2. **Cleaner Interfaces**
   - Provide well-defined interfaces for other core_v2 components
   - Reduce direct dependencies on implementation details

3. **Extension Management**
   - Improve extension installation and update processes
   - Better error handling for extension-related issues

4. **Browser Usage Tracking Improvements**
   - Replace the current file-based usage tracking with a more efficient, structured solution
   - Implement a queryable storage format for browser activity data
   - Optimize storage requirements with better data organization and compression
   - Provide interfaces for analyzing browser usage patterns

5. **Documentation**
   - Comprehensive documentation of the integration points
   - Clear usage examples for other components

## Integration Strategy

We will use an **adapter pattern** to integrate the existing browser detection and extension components with core_v2:

1. **Core Adapter Layer**
   - Create adapters that expose core_v2-compatible interfaces
   - Delegate to existing implementation under the hood

2. **Minimal Refactoring**
   - Keep existing functionality intact
   - Only refactor where necessary for integration

3. **Clean Dependencies**
   - Update import paths to follow core_v2 conventions
   - Use dependency injection where appropriate

4. **Incremental Migration**
   - Start with the integration layer
   - Gradually improve internal components over time

## Directory Structure

```
core_v2/
  browser/
    __init__.py                  # Package exports
    interfaces.py                # Core interfaces for browser integration
    adapter.py                   # Adapter to legacy implementation
    
    extension/
      __init__.py                # Package exports
      manager.py                 # Extension installation and management
      messaging.py               # Communication with extension
      
    detection/
      __init__.py                # Package exports
      browser_detector.py        # Browser detection functionality
      window_detector.py         # Browser window detection
      
    integration/
      __init__.py                # Package exports
      tab_tracker.py             # Tab tracking functionality
      tab_blocker.py             # Tab blocking functionality
      
    models/
      __init__.py                # Package exports
      browser.py                 # Browser model classes
      tab.py                     # Tab model classes
      
    usage/
      __init__.py                # Package exports
      tracker.py                 # Browser usage tracking functionality
      storage.py                 # Storage management for usage data
      analyzer.py                # Usage data analysis utilities
```

## Legacy Code Preservation

The existing implementation in `core/browser_detection/` will be preserved with minimal changes:

```
core/
  browser_detection/
    webextension_mv3/            # Existing extension (unchanged)
    browser_integration/         # Existing integration (minor updates)
    ...                          # Other existing components
```

## Browser Usage Tracking System

The browser extension currently tracks browser usage through a simple file-based logging system. This section outlines a plan to improve this system for better efficiency, queryability, and storage optimization.

### Current Implementation

1. **File-Based Storage**
   - Daily log files with date-based filenames (`focusguard_tab_log_YYYY-MM-DD.txt`)
   - Debug logs in separate files (`focusguard_debug_YYYY-MM-DD.log`)
   - Tab snapshots stored as JSON files (`tabs_snapshot_YYYY-MM-DD.json`)
   - Basic log rotation (deleting logs older than 3 days)

2. **Data Format**
   - Tab logs stored as plain text with key-value pairs
   - Snapshots stored as nested JSON objects
   - No structured schema or indexing

3. **Limitations**
   - Inefficient storage format (plain text/JSON)
   - Limited queryability (requires parsing entire files)
   - No aggregation or analysis capabilities
   - Potential for large file sizes with high browser activity
   - No compression or optimization

### Proposed Improvements

1. **Structured Storage Format**
   - Replace plain text logs with a structured format (SQLite or optimized JSON)
   - Define clear schemas for different types of usage data
   - Implement proper indexing for efficient queries

2. **Storage Optimization**
   - Implement data compression for historical records
   - Use incremental updates instead of full snapshots
   - Implement efficient storage and retrieval algorithms
   - Optimize storage paths and organization

3. **Data Management**
   - Configurable retention policies
   - Automatic aggregation of historical data
   - Scheduled cleanup and optimization
   - Data export and backup capabilities

4. **Analysis Capabilities**
   - Provide interfaces for querying usage patterns
   - Support for common analytics queries
   - Integration with the domain classification system
   - Time-series analysis of browser usage

### Implementation Approach

1. **Storage Backend**
   - Primary option: SQLite database for structured, queryable storage
     - Advantages: Built-in indexing, SQL queries, transaction support
     - Disadvantages: Requires SQLite dependency, potential for database corruption
   - Alternative option: Optimized JSON with indexing
     - Advantages: No additional dependencies, simpler implementation
     - Disadvantages: Less efficient queries, more complex implementation for indexing

2. **Data Models**
   - `BrowserSession`: Represents a browser session with start/end times
   - `TabEvent`: Records tab creation, updates, and closures
   - `DomainVisit`: Aggregates time spent on specific domains
   - `UsageSummary`: Daily/weekly summaries of browser usage

3. **API Design**
   - `UsageTracker`: Records browser and tab events
   - `UsageStorage`: Manages persistent storage of usage data
   - `UsageAnalyzer`: Provides query and analysis capabilities
   - `UsageExporter`: Exports usage data in various formats

### Code Example: Usage Tracker Interface

```python
# core_v2/browser/usage/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta

from core_v2.browser.models.browser import Browser
from core_v2.browser.models.tab import Tab

class UsageTrackerInterface(ABC):
    """Interface for tracking browser usage."""
    
    @abstractmethod
    def record_browser_session(self, browser: Browser, start_time: datetime) -> str:
        """Record the start of a browser session.
        
        Args:
            browser: Browser instance
            start_time: Session start time
            
        Returns:
            str: Session ID
        """
        pass
    
    @abstractmethod
    def end_browser_session(self, session_id: str, end_time: datetime) -> None:
        """Record the end of a browser session.
        
        Args:
            session_id: Session ID returned by record_browser_session
            end_time: Session end time
        """
        pass
    
    @abstractmethod
    def record_tab_event(self, tab: Tab, event_type: str, timestamp: datetime) -> None:
        """Record a tab event.
        
        Args:
            tab: Tab instance
            event_type: Type of event (created, updated, closed, etc.)
            timestamp: Event timestamp
        """
        pass
    
    @abstractmethod
    def record_domain_visit(self, domain: str, duration_seconds: float, timestamp: datetime) -> None:
        """Record time spent on a domain.
        
        Args:
            domain: Domain name
            duration_seconds: Duration in seconds
            timestamp: Visit timestamp
        """
        pass

class UsageStorageInterface(ABC):
    """Interface for storing browser usage data."""
    
    @abstractmethod
    def initialize_storage(self) -> None:
        """Initialize the storage backend."""
        pass
    
    @abstractmethod
    def store_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Store an event in the storage backend.
        
        Args:
            event_type: Type of event
            event_data: Event data
        """
        pass
    
    @abstractmethod
    def query_events(self, event_type: str, start_time: datetime, end_time: datetime,
                    filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query events from the storage backend.
        
        Args:
            event_type: Type of events to query
            start_time: Start time for the query
            end_time: End time for the query
            filters: Additional filters for the query
            
        Returns:
            List[Dict[str, Any]]: List of matching events
        """
        pass
    
    @abstractmethod
    def get_usage_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get a summary of browser usage for a time period.
        
        Args:
            start_time: Start time for the summary
            end_time: End time for the summary
            
        Returns:
            Dict[str, Any]: Usage summary
        """
        pass
    
    @abstractmethod
    def cleanup_old_data(self, older_than: datetime) -> int:
        """Clean up data older than a specified time.
        
        Args:
            older_than: Remove data older than this time
            
        Returns:
            int: Number of records removed
        """
        pass
```

### Code Example: SQLite Implementation

```python
# core_v2/browser/usage/storage.py
import os
import sqlite3
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta

from core_v2.browser.usage.interfaces import UsageStorageInterface

class SQLiteUsageStorage(UsageStorageInterface):
    """SQLite implementation of UsageStorageInterface."""
    
    def __init__(self, db_path: str = None):
        """Initialize the SQLite storage.
        
        Args:
            db_path: Path to the SQLite database file
        """
        if db_path is None:
            from core_v2.utils.paths import get_data_dir
            db_path = os.path.join(get_data_dir(), "browser_usage.db")
        
        self.db_path = db_path
        self.conn = None
    
    def initialize_storage(self) -> None:
        """Initialize the storage backend."""
        self.conn = sqlite3.connect(self.db_path)
        
        # Create tables if they don't exist
        with self.conn:
            # Browser sessions table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS browser_sessions (
                    id TEXT PRIMARY KEY,
                    browser_id TEXT,
                    browser_name TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Tab events table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tab_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tab_id INTEGER,
                    window_id INTEGER,
                    browser_id TEXT,
                    url TEXT,
                    domain TEXT,
                    title TEXT,
                    event_type TEXT,
                    timestamp TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Domain visits table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS domain_visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT,
                    duration_seconds REAL,
                    timestamp TIMESTAMP,
                    browser_id TEXT,
                    tab_id INTEGER
                )
            """)
            
            # Create indexes for common queries
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tab_events_domain ON tab_events(domain)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tab_events_timestamp ON tab_events(timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_domain_visits_domain ON domain_visits(domain)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_domain_visits_timestamp ON domain_visits(timestamp)")
    
    def store_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Store an event in the storage backend."""
        if self.conn is None:
            self.initialize_storage()
        
        with self.conn:
            if event_type == "browser_session":
                self.conn.execute(
                    "INSERT INTO browser_sessions VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        event_data["id"],
                        event_data["browser_id"],
                        event_data["browser_name"],
                        event_data["start_time"].isoformat(),
                        event_data.get("end_time", None),
                        json.dumps(event_data.get("metadata", {}))
                    )
                )
            elif event_type == "tab_event":
                self.conn.execute(
                    "INSERT INTO tab_events (tab_id, window_id, browser_id, url, domain, title, event_type, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_data["tab_id"],
                        event_data["window_id"],
                        event_data["browser_id"],
                        event_data["url"],
                        event_data.get("domain", ""),
                        event_data.get("title", ""),
                        event_data["event_type"],
                        event_data["timestamp"].isoformat(),
                        json.dumps(event_data.get("metadata", {}))
                    )
                )
            elif event_type == "domain_visit":
                self.conn.execute(
                    "INSERT INTO domain_visits (domain, duration_seconds, timestamp, browser_id, tab_id) VALUES (?, ?, ?, ?, ?)",
                    (
                        event_data["domain"],
                        event_data["duration_seconds"],
                        event_data["timestamp"].isoformat(),
                        event_data.get("browser_id", ""),
                        event_data.get("tab_id", 0)
                    )
                )
```

### Migration Strategy

1. **Phase 1: Parallel Logging**
   - Implement the new storage system alongside the existing one
   - Log to both systems to ensure data continuity
   - Validate the new system's functionality and performance

2. **Phase 2: Data Migration**
   - Develop tools to migrate historical data to the new format
   - Implement data validation and verification
   - Provide fallback mechanisms during migration

3. **Phase 3: Full Transition**
   - Switch to the new system as the primary storage
   - Deprecate the old logging system
   - Update dependent components to use the new interfaces

### Benefits

1. **Performance**
   - Reduced disk usage through optimized storage
   - Faster queries for usage analysis
   - Better scalability for high-volume browser activity

2. **Functionality**
   - Rich query capabilities for usage patterns
   - Better integration with other components
   - Support for advanced analytics

3. **Maintainability**
   - Cleaner code structure with well-defined interfaces
   - Better error handling and recovery
   - Easier extension for future requirements

## Detailed Implementation Plan

### Phase 1: Core Interfaces and Models

1. **Define Core Interfaces**
   - Create `browser/interfaces.py` with:
     - `BrowserDetectorInterface`: For detecting browsers
     - `TabTrackerInterface`: For tracking browser tabs
     - `TabBlockerInterface`: For blocking tabs
     - `ExtensionManagerInterface`: For managing extensions

2. **Create Data Models**
   - Create `browser/models/browser.py` with:
     - `Browser` dataclass: Represents a browser instance
     - `BrowserType` enum: Chrome, Firefox, Edge, etc.
   - Create `browser/models/tab.py` with:
     - `Tab` dataclass: Represents a browser tab
     - `TabEvent` enum: Created, Updated, Removed, etc.

### Phase 2: Adapter Layer

1. **Browser Detection Adapter**
   - Create `browser/adapter.py` with:
     - `LegacyBrowserDetectorAdapter`: Adapts legacy browser detection
     - `LegacyTabTrackerAdapter`: Adapts legacy tab tracking
     - `LegacyTabBlockerAdapter`: Adapts legacy tab blocking

2. **Extension Management Adapter**
   - Create `browser/extension/manager.py` with:
     - `LegacyExtensionManagerAdapter`: Adapts legacy extension management
     - Extension installation and update functionality

### Phase 3: Integration Points

1. **Tab Tracking Integration**
   - Create `browser/integration/tab_tracker.py` with:
     - `TabTracker` class: Provides core_v2 compatible interface
     - Event handling for tab events
     - Integration with domain classification

2. **Tab Blocking Integration**
   - Create `browser/integration/tab_blocker.py` with:
     - `TabBlocker` class: Provides core_v2 compatible interface
     - Integration with alert system and distraction detection

### Phase 4: Minimal Legacy Updates

1. **Update Import Paths**
   - Modify legacy code to use core_v2 imports where appropriate
   - Update dependencies to use core_v2 components

2. **Add Integration Hooks**
   - Add hooks in legacy code for core_v2 integration
   - Ensure backward compatibility

## Code Examples

### Core Interfaces

```python
# core_v2/browser/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable

from core_v2.browser.models.browser import Browser
from core_v2.browser.models.tab import Tab, TabEvent

class BrowserDetectorInterface(ABC):
    """Interface for detecting browsers and their windows."""
    
    @abstractmethod
    def get_active_browsers(self) -> List[Browser]:
        """Get a list of active browser instances.
        
        Returns:
            List[Browser]: List of active browser instances
        """
        pass
    
    @abstractmethod
    def get_active_browser_window(self) -> Optional[Browser]:
        """Get the currently active browser window.
        
        Returns:
            Optional[Browser]: Active browser window or None if no browser is active
        """
        pass

class TabTrackerInterface(ABC):
    """Interface for tracking browser tabs."""
    
    @abstractmethod
    def get_all_tabs(self) -> List[Tab]:
        """Get all open tabs across all browsers.
        
        Returns:
            List[Tab]: List of all open tabs
        """
        pass
    
    @abstractmethod
    def get_active_tab(self) -> Optional[Tab]:
        """Get the currently active tab.
        
        Returns:
            Optional[Tab]: Active tab or None if no tab is active
        """
        pass
    
    @abstractmethod
    def register_tab_event_handler(self, event_type: TabEvent, handler: Callable[[Tab], None]) -> None:
        """Register a handler for tab events.
        
        Args:
            event_type: Type of tab event to handle
            handler: Function to call when the event occurs
        """
        pass

class TabBlockerInterface(ABC):
    """Interface for blocking browser tabs."""
    
    @abstractmethod
    def close_tab(self, tab: Tab, reason: str = None) -> bool:
        """Close a browser tab.
        
        Args:
            tab: Tab to close
            reason: Reason for closing the tab
            
        Returns:
            bool: True if the tab was closed successfully
        """
        pass
    
    @abstractmethod
    def block_domain(self, domain: str, duration_seconds: int = None) -> bool:
        """Block a domain from being accessed.
        
        Args:
            domain: Domain to block
            duration_seconds: Duration of the block in seconds, or None for permanent
            
        Returns:
            bool: True if the domain was blocked successfully
        """
        pass

class ExtensionManagerInterface(ABC):
    """Interface for managing browser extensions."""
    
    @abstractmethod
    def is_extension_installed(self, browser_type: str) -> bool:
        """Check if the extension is installed for a browser type.
        
        Args:
            browser_type: Type of browser to check
            
        Returns:
            bool: True if the extension is installed
        """
        pass
    
    @abstractmethod
    def install_extension(self, browser_type: str) -> bool:
        """Install the extension for a browser type.
        
        Args:
            browser_type: Type of browser to install for
            
        Returns:
            bool: True if the extension was installed successfully
        """
        pass
```

### Data Models

```python
# core_v2/browser/models/browser.py
from dataclasses import dataclass
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
    metadata: Dict[str, Any] = None
```

```python
# core_v2/browser/models/tab.py
from dataclasses import dataclass
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
    created_at: datetime = None
    updated_at: datetime = None
    is_active: bool = False
    metadata: Dict[str, Any] = None
```

### Adapter Implementation

```python
# core_v2/browser/adapter.py
from typing import List, Dict, Any, Optional, Callable

from core_v2.browser.interfaces import BrowserDetectorInterface, TabTrackerInterface, TabBlockerInterface
from core_v2.browser.models.browser import Browser, BrowserType
from core_v2.browser.models.tab import Tab, TabEvent

# Import legacy components
from core.browser_detection.browser_integration.browser_integration_v2 import get_browser_integration, is_extension_connected, get_all_tabs, get_active_tab, close_tab

class LegacyBrowserDetectorAdapter(BrowserDetectorInterface):
    """Adapter for legacy browser detection."""
    
    def get_active_browsers(self) -> List[Browser]:
        """Get a list of active browser instances."""
        # Use legacy implementation to get browser data
        browser_integration = get_browser_integration()
        if not browser_integration:
            return []
            
        # Convert legacy browser data to Browser objects
        browsers = []
        browser_data = browser_integration.get_browser_data()
        
        for browser_id, data in browser_data.items():
            browser_type = self._map_browser_type(data.get("browser_name", ""))
            browser = Browser(
                id=browser_id,
                type=browser_type,
                name=data.get("browser_name", "Unknown"),
                process_id=data.get("pid", 0),
                window_id=data.get("window_id"),
                window_title=data.get("window_title"),
                executable_path=data.get("executable_path"),
                version=data.get("version"),
                metadata=data
            )
            browsers.append(browser)
            
        return browsers
    
    def get_active_browser_window(self) -> Optional[Browser]:
        """Get the currently active browser window."""
        browsers = self.get_active_browsers()
        # Find the active browser (if any)
        for browser in browsers:
            if browser.metadata and browser.metadata.get("is_active", False):
                return browser
        return None
        
    def _map_browser_type(self, browser_name: str) -> BrowserType:
        """Map legacy browser name to BrowserType enum."""
        name_lower = browser_name.lower()
        if "chrome" in name_lower:
            return BrowserType.CHROME
        elif "firefox" in name_lower:
            return BrowserType.FIREFOX
        elif "edge" in name_lower:
            return BrowserType.EDGE
        elif "safari" in name_lower:
            return BrowserType.SAFARI
        elif "opera" in name_lower:
            return BrowserType.OPERA
        elif "brave" in name_lower:
            return BrowserType.BRAVE
        else:
            return BrowserType.UNKNOWN

class LegacyTabTrackerAdapter(TabTrackerInterface):
    """Adapter for legacy tab tracking."""
    
    def __init__(self):
        self._event_handlers = {event_type: [] for event_type in TabEvent}
        
    def get_all_tabs(self) -> List[Tab]:
        """Get all open tabs across all browsers."""
        # Use legacy implementation to get tab data
        legacy_tabs = get_all_tabs()
        if not legacy_tabs:
            return []
            
        # Convert legacy tab data to Tab objects
        tabs = []
        for tab_data in legacy_tabs:
            tab = self._convert_tab_data(tab_data)
            if tab:
                tabs.append(tab)
                
        return tabs
    
    def get_active_tab(self) -> Optional[Tab]:
        """Get the currently active tab."""
        # Use legacy implementation to get active tab data
        active_tab_data = get_active_tab()
        if not active_tab_data:
            return None
            
        return self._convert_tab_data(active_tab_data)
    
    def register_tab_event_handler(self, event_type: TabEvent, handler: Callable[[Tab], None]) -> None:
        """Register a handler for tab events."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)
            
    def _convert_tab_data(self, tab_data: Dict[str, Any]) -> Optional[Tab]:
        """Convert legacy tab data to a Tab object."""
        try:
            return Tab(
                id=tab_data.get("id", 0),
                window_id=tab_data.get("windowId", 0),
                url=tab_data.get("url", ""),
                title=tab_data.get("title", ""),
                browser_id=tab_data.get("browserId", "unknown"),
                domain=tab_data.get("domain"),
                favicon=tab_data.get("favIconUrl"),
                is_active=tab_data.get("active", False),
                metadata=tab_data
            )
        except Exception:
            return None

class LegacyTabBlockerAdapter(TabBlockerInterface):
    """Adapter for legacy tab blocking."""
    
    def close_tab(self, tab: Tab, reason: str = None) -> bool:
        """Close a browser tab."""
        # Convert Tab object to legacy format
        tab_info = {
            "tabId": tab.id,
            "windowId": tab.window_id,
            "url": tab.url,
            "domain": tab.domain,
            "reason": reason
        }
        
        # Use legacy implementation to close the tab
        return close_tab(tab_info)
    
    def block_domain(self, domain: str, duration_seconds: int = None) -> bool:
        """Block a domain from being accessed."""
        # Use legacy implementation to block the domain
        browser_integration = get_browser_integration()
        if not browser_integration:
            return False
            
        return browser_integration.block_domain(domain, duration_seconds)
```

### Integration Example

```python
# core_v2/browser/integration/tab_tracker.py
from typing import List, Dict, Any, Optional, Callable
import threading
import time

from core_v2.browser.interfaces import TabTrackerInterface
from core_v2.browser.models.tab import Tab, TabEvent
from core_v2.browser.adapter import LegacyTabTrackerAdapter
from core_v2.domain.models import Domain

class TabTracker:
    """Tracks browser tabs and provides domain information."""
    
    def __init__(self, tab_tracker_adapter: TabTrackerInterface = None):
        """Initialize the tab tracker.
        
        Args:
            tab_tracker_adapter: Adapter for tab tracking functionality
        """
        self.adapter = tab_tracker_adapter or LegacyTabTrackerAdapter()
        self._event_handlers = {event_type: [] for event_type in TabEvent}
        self._active_tabs = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        
        # Register for tab events from the adapter
        for event_type in TabEvent:
            self.adapter.register_tab_event_handler(event_type, self._handle_tab_event)
    
    def start(self) -> bool:
        """Start tracking tabs.
        
        Returns:
            bool: True if started successfully
        """
        if self._running:
            return True
            
        self._running = True
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
        return True
    
    def stop(self) -> None:
        """Stop tracking tabs."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
    
    def get_all_tabs(self) -> List[Tab]:
        """Get all open tabs."""
        return self.adapter.get_all_tabs()
    
    def get_active_tab(self) -> Optional[Tab]:
        """Get the currently active tab."""
        return self.adapter.get_active_tab()
    
    def get_tabs_by_domain(self, domain: str) -> List[Tab]:
        """Get all tabs for a specific domain.
        
        Args:
            domain: Domain to filter by
            
        Returns:
            List[Tab]: List of tabs matching the domain
        """
        tabs = self.get_all_tabs()
        return [tab for tab in tabs if tab.domain == domain]
    
    def register_tab_event_handler(self, event_type: TabEvent, handler: Callable[[Tab], None]) -> None:
        """Register a handler for tab events."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)
    
    def _handle_tab_event(self, tab: Tab) -> None:
        """Handle a tab event from the adapter."""
        with self._lock:
            # Update our internal state
            if tab.id in self._active_tabs:
                old_tab = self._active_tabs[tab.id]
                event_type = TabEvent.UPDATED
                if tab.is_active and not old_tab.is_active:
                    event_type = TabEvent.ACTIVATED
                self._active_tabs[tab.id] = tab
            else:
                event_type = TabEvent.CREATED
                self._active_tabs[tab.id] = tab
                
            # Notify handlers
            for handler in self._event_handlers.get(event_type, []):
                try:
                    handler(tab)
                except Exception:
                    pass
    
    def _tracking_loop(self) -> None:
        """Background thread for tracking tabs."""
        while self._running:
            try:
                # Get current tabs
                current_tabs = {tab.id: tab for tab in self.adapter.get_all_tabs()}
                
                with self._lock:
                    # Find removed tabs
                    for tab_id, tab in list(self._active_tabs.items()):
                        if tab_id not in current_tabs:
                            # Tab was removed
                            for handler in self._event_handlers.get(TabEvent.REMOVED, []):
                                try:
                                    handler(tab)
                                except Exception:
                                    pass
                            del self._active_tabs[tab_id]
                    
                    # Update active tabs
                    self._active_tabs = current_tabs
            except Exception:
                pass
                
            # Sleep before next update
            time.sleep(1.0)
```

## Testing Strategy

### Unit Tests

1. **Interface Tests**
   - Test the core interfaces with mock implementations
   - Verify adapter pattern correctly delegates to legacy code

2. **Model Tests**
   - Test the data models for proper serialization/deserialization
   - Verify model conversions between legacy and core_v2 formats

3. **Integration Tests**
   - Test the integration points with other core_v2 components
   - Verify proper event propagation

### Manual Tests

1. **Extension Installation**
   - Verify extension installation process
   - Test browser detection and extension management

2. **Tab Tracking**
   - Verify tab events are properly tracked
   - Test domain classification integration

3. **Tab Blocking**
   - Verify tab blocking functionality
   - Test integration with alert system

## Implementation Timeline

### Week 1: Foundation and Core Components

1. **Days 1-2: Core Interfaces and Models**
   - Create directory structure
   - Implement core interfaces
   - Implement data models

2. **Days 3-4: Adapter Layer**
   - Implement browser detection adapter
   - Implement tab tracker adapter
   - Implement tab blocker adapter

3. **Days 5-7: Integration Points**
   - Implement tab tracking integration
   - Implement tab blocking integration
   - Implement usage tracking system
   - Create basic tests

### Week 2: Testing and Refinement

1. **Days 8-9: Unit Tests**
   - Write comprehensive unit tests
   - Fix bugs and edge cases

2. **Days 10-11: Integration Tests**
   - Write integration tests
   - Test with other core_v2 components

3. **Days 12-14: Documentation and Examples**
   - Create detailed documentation
   - Write usage examples
   - Final testing and refinement

## Migration Strategy

1. **Adapter Pattern**
   - Use adapters to bridge between core_v2 and legacy code
   - Minimize changes to existing functionality

2. **Gradual Adoption**
   - Start using the new interfaces in new features
   - Gradually migrate existing code to use the new interfaces

3. **Compatibility Layer**
   - Ensure backward compatibility for dependent code
   - Provide migration guides for dependent components

## Conclusion

This integration plan provides a pragmatic approach to incorporating the browser detection and webextension_mv3 components into the core_v2 architecture. By using the adapter pattern, we can preserve the existing functionality while providing clean interfaces for other core_v2 components.

The plan emphasizes minimal rewriting of the existing code, recognizing that the browser extension integration is already a complex, well-functioning system that took considerable effort to develop. Instead, it focuses on proper integration with the core_v2 architecture through well-defined interfaces and adapters.

By following this plan, we will achieve a modular, maintainable integration of the browser detection and extension components with the core_v2 architecture, while preserving the hard-won functionality of the existing implementation.
