# Browser Detection & WebExtension MV3 Integration

This module provides a modular implementation of browser detection, tab tracking, tab blocking, and extension management functionality for the Focus Guard application.

## Architecture

The architecture follows the principles outlined in the master implementation plan, emphasizing:

- Interface-based design
- Dependency injection
- Platform abstraction
- Testability
- Event-based communication

### Directory Structure

```
core_v2/browser/
├── __init__.py
├── interfaces.py           # Core interfaces
├── adapter.py              # Implementation of interfaces
├── models/                 # Data models
│   ├── __init__.py
│   ├── browser.py          # Browser model
│   └── tab.py              # Tab model
├── integration/            # Integration modules
│   ├── __init__.py
│   ├── tab_tracker.py      # Tab tracking implementation
│   └── tab_blocker.py      # Tab blocking implementation
├── extension/              # Extension management
│   ├── __init__.py
│   └── manager.py          # Extension manager implementation
└── usage/                  # Usage tracking
    ├── __init__.py
    └── tracker.py          # Usage tracker implementation
```

## Core Interfaces

The module is built around the following core interfaces:

### BrowserDetectorInterface

Responsible for detecting active browser instances and windows.

```python
class BrowserDetectorInterface(ABC):
    @abstractmethod
    def get_active_browsers(self) -> List[Browser]:
        """Get a list of active browser instances."""
        pass
    
    @abstractmethod
    def get_active_browser_window(self) -> Optional[Browser]:
        """Get the currently active browser window."""
        pass
```

### TabTrackerInterface

Responsible for tracking browser tabs and tab events.

```python
class TabTrackerInterface(ABC):
    @abstractmethod
    def get_all_tabs(self) -> List[Tab]:
        """Get all open tabs across all browsers."""
        pass
    
    @abstractmethod
    def get_active_tab(self) -> Optional[Tab]:
        """Get the currently active tab."""
        pass
    
    @abstractmethod
    def register_tab_event_handler(self, event_type: TabEvent, handler: Callable[[Tab], None]) -> None:
        """Register a handler for tab events."""
        pass
    
    @abstractmethod
    def get_tabs_by_domain(self, domain: str) -> List[Tab]:
        """Get all tabs for a specific domain."""
        pass
```

### TabBlockerInterface

Responsible for blocking domains and closing tabs.

```python
class TabBlockerInterface(ABC):
    @abstractmethod
    def close_tab(self, tab: Tab, reason: str = None) -> bool:
        """Close a browser tab."""
        pass
    
    @abstractmethod
    def block_domain(self, domain: str, duration_seconds: int = None) -> bool:
        """Block a domain from being accessed."""
        pass
```

### ExtensionManagerInterface

Responsible for managing browser extensions.

```python
class ExtensionManagerInterface(ABC):
    @abstractmethod
    def is_extension_installed(self, browser_type: BrowserType) -> bool:
        """Check if the extension is installed for a browser type."""
        pass
    
    @abstractmethod
    def install_extension(self, browser_type: BrowserType) -> bool:
        """Install the extension for a browser type."""
        pass
    
    @abstractmethod
    def update_extension(self, browser_type: BrowserType) -> bool:
        """Update the extension for a browser type."""
        pass
```

### UsageTrackerInterface

Responsible for tracking browser usage patterns.

```python
class UsageTrackerInterface(ABC):
    @abstractmethod
    def track_active_tab(self, tab: Tab) -> None:
        """Track the active tab."""
        pass
    
    @abstractmethod
    def track_browser_session(self, browser: Browser, is_active: bool) -> None:
        """Track a browser session."""
        pass
    
    @abstractmethod
    def get_domain_usage(self, domain: str, days: int = 7) -> Dict[str, float]:
        """Get usage statistics for a domain."""
        pass
    
    @abstractmethod
    def get_top_domains(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the top domains by usage."""
        pass
```

## Data Models

### Browser

Represents a browser instance.

```python
@dataclass
class Browser:
    id: str
    type: BrowserType
    name: str
    process_id: int
    window_id: Optional[int] = None
    window_title: Optional[str] = None
    executable_path: Optional[str] = None
    version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Tab

Represents a browser tab.

```python
@dataclass
class Tab:
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
```

## Integration with Browser Extensions

The tab tracking and blocking functionality integrates with browser extensions using a simple HTTP-based protocol. The tab server provides endpoints for:

- Getting all tabs (`/api/tabs`)
- Getting the active tab (`/api/active_tab`)
- Checking extension connection status (`/api/status`)
- Sending commands to the extension (`/api/command`)
- Closing tabs
- Blocking domains

### Extension Installation

The extension can be installed programmatically using the `ExtensionInstaller` class in `core_v2/browser/extension/installer.py`. This class provides methods for:

- Starting and stopping the tab server
- Installing the extension for detected browsers
- Checking extension connection status
- Verifying installation

A command-line utility is also available at `examples/install_extension_systematically.py` that provides a user-friendly interface for installing and verifying the extension. See `examples/README_EXTENSION_INSTALLATION.md` for detailed instructions.

## Usage

### Basic Usage

```python
from core_v2.browser.adapter import BrowserDetector, TabTracker, TabBlocker
from core_v2.browser.extension.manager import BrowserExtensionManager
from core_v2.browser.usage.tracker import BrowserUsageTracker

# Create instances
browser_detector = BrowserDetector()
tab_tracker = TabTracker()
tab_blocker = TabBlocker()
extension_manager = BrowserExtensionManager()
usage_tracker = BrowserUsageTracker()

# Get active browsers
browsers = browser_detector.get_active_browsers()

# Get all tabs
tabs = tab_tracker.get_all_tabs()

# Get active tab
active_tab = tab_tracker.get_active_tab()

# Block a domain
tab_blocker.block_domain("example.com", 3600)  # Block for 1 hour

# Close a tab
if active_tab:
    tab_blocker.close_tab(active_tab, reason="Blocked domain")

# Track usage
usage_tracker.track_active_tab(active_tab)

# Get usage statistics
domain_usage = usage_tracker.get_domain_usage("example.com")
top_domains = usage_tracker.get_top_domains()
```

### Advanced Usage with Integration Classes

```python
from core_v2.browser.integration.tab_tracker import BrowserTabTracker
from core_v2.browser.integration.tab_blocker import BrowserTabBlocker
from core_v2.browser.models.tab import TabEvent

# Create instances
tab_tracker = BrowserTabTracker()
tab_blocker = BrowserTabBlocker()

# Start tracking tabs
tab_tracker.start()

# Register event handlers
def on_tab_created(tab):
    print(f"Tab created: {tab.url}")

def on_tab_removed(tab):
    print(f"Tab removed: {tab.url}")

tab_tracker.register_tab_event_handler(TabEvent.CREATED, on_tab_created)
tab_tracker.register_tab_event_handler(TabEvent.REMOVED, on_tab_removed)

# Block a domain and close all tabs for that domain
tab_blocker.block_domain("example.com")
tabs = tab_tracker.get_tabs_by_domain("example.com")
for tab in tabs:
    tab_blocker.close_tab(tab, reason="Blocked domain")

# Stop tracking tabs
tab_tracker.stop()
```

## Testing

The module includes unit and integration tests to verify the functionality of the interfaces and implementations. To run the tests:

```
python -m unittest discover -s tests/core_v2/browser
```

## Extension Integration

The browser extension integration follows the approach outlined in the browser_detection_webextension_mv3_integration_plan, using browser extensions instead of Chrome DevTools Protocol (CDP) for tab closing functionality. This approach avoids security warnings that occur when using CDP, which requires enabling remote debugging mode.

The extension message protocol uses a simple JSON format:

```json
{
  "action": "close_tab",
  "data": {
    "tabId": 123,
    "windowId": 456,
    "url": "https://example.com",
    "domain": "example.com",
    "reason": "Blocked domain"
  }
}
```

## Extension Architecture

The browser extension integration follows a layered architecture:

1. **Browser Extension**: Implemented as a WebExtension MV3 extension that monitors tabs and communicates with the tab server
2. **Tab Server**: A lightweight HTTP server that receives tab data from extensions and provides an API for the application
3. **Browser Integration**: Classes that connect the tab server to the Focus Guard application
4. **Activity Monitoring**: Integration with the activity monitoring system to track browser usage

### Key Components

- `core/browser_detection/browser_integration/tab_server_v2.py`: HTTP server for extension communication (to be migrated to core_v2)
- `core_v2/browser/integration/browser_integration.py`: Bridge between tab server and application
- `core_v2/browser/integration/tab_tracker.py`: Tracks tabs and tab events
- `core_v2/browser/integration/tab_blocker.py`: Handles tab closing and domain blocking
- `core_v2/activity/browser/extension_integration.py`: Integrates with the activity monitoring system
- `core_v2/browser/extension/installer.py`: Manages extension installation and verification

## Future Enhancements

- Add support for more browser types (Firefox, Safari)
- Enhance usage tracking with more detailed statistics
- Improve tab closing reliability across different browsers
- Add support for browser profiles
- Implement domain-specific blocking rules
