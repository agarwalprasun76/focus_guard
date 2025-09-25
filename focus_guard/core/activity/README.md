# Activity Monitor Module

## Overview
The Activity Monitor module provides a platform-abstracted way to monitor user activity across different operating systems. It tracks active windows, top-level windows, and integrates with browser extensions to provide detailed information about browser tabs.

## Architecture

### Core Components

#### Models (`models.py`)
- `WindowInfo`: Represents information about a window including app name, window title, process ID, and optional browser-specific data like URL and domain.
- `ActivityEvent`: Represents a user activity event with event type, timestamp, associated window info, and metadata.

#### Activity Monitor (`monitor.py`)
- `ActivityMonitor`: Main class that provides a unified interface for activity monitoring across platforms.
- Integrates with platform-specific implementations and browser monitoring.
- Provides methods to get active window info, top windows, and create activity events.

### Platform Abstraction

#### Base Interface (`platform/base.py`)
- `PlatformActivityMonitor`: Abstract base class defining the interface for platform-specific implementations.
- Required methods: `get_active_window()`, `get_top_windows(top_region)`, `is_supported()`.

#### Platform Factory (`platform/__init__.py`)
- `get_platform_implementation()`: Factory function that detects and instantiates the appropriate platform-specific implementation.

#### Platform Implementations
- `WindowsActivityMonitor` (`platform/windows.py`): Windows implementation using win32gui, win32process, and psutil.
- `LinuxActivityMonitor` (`platform/linux.py`): Linux implementation using X11 utilities and psutil (partially implemented).
- `MacOSActivityMonitor` (`platform/macos.py`): macOS implementation (stub).

### Browser Integration

#### Browser Tab Monitor (`browser/tab_monitor.py`)
- `BrowserTabMonitor`: Provides methods to get information about browser tabs.
- Methods: `get_active_tab()`, `get_all_tabs()`, `get_tabs_by_browser()`, `get_tabs_by_domain()`.

#### Browser Extension Integration (`browser/extension_integration.py`)
- `BrowserExtensionIntegration`: Communicates with browser extensions to get tab data.
- Provides caching with TTL and fallback mechanisms.
- Methods: `get_active_tab()`, `get_all_tabs()`, `close_tab()`.

## Usage

### Basic Usage

```python
from core_v2.activity import ActivityMonitor, WindowInfo, ActivityEvent

# Create an activity monitor
monitor = ActivityMonitor()

# Get the currently active window
active_window = monitor.get_active_window()
if active_window:
    print(f"Active window: {active_window.app_name} - {active_window.window_title}")
    if active_window.url:
        print(f"URL: {active_window.url}")

# Get top-level windows
top_windows = monitor.get_top_windows(top_region=300)  # Only consider windows in top 300 pixels
for window in top_windows:
    print(f"Window: {window.app_name} - {window.window_title} ({window.percent:.1%})")

# Create an activity event
event = monitor.create_activity_event("window_activated", {"duration": 60})
print(f"Event: {event.event_type} at {event.timestamp}")
```

### Platform-Specific Implementation

```python
from core_v2.activity.platform import get_platform_implementation

# Get the platform-specific implementation directly
platform_monitor = get_platform_implementation()

# Use platform-specific methods
active_window_data = platform_monitor.get_active_window()
print(f"Active window data: {active_window_data}")
```

### Browser Tab Monitoring

```python
from core_v2.activity.browser import BrowserTabMonitor

# Create a browser tab monitor
tab_monitor = BrowserTabMonitor()

# Get the active tab
active_tab = tab_monitor.get_active_tab()
if active_tab:
    print(f"Active tab: {active_tab['title']} - {active_tab['url']}")

# Get all tabs
all_tabs = tab_monitor.get_all_tabs()
print(f"Total tabs: {len(all_tabs)}")

# Get tabs for a specific browser
chrome_tabs = tab_monitor.get_tabs_by_browser("chrome")
print(f"Chrome tabs: {len(chrome_tabs)}")

# Get tabs for a specific domain
social_tabs = tab_monitor.get_tabs_by_domain("facebook.com")
print(f"Social media tabs: {len(social_tabs)}")
```

## Future Work

### Browser Extension Integration
The current browser integration components are stubs that need to be connected to the actual browser extension system. This will be implemented as part of the browser extension port to core_v2.

### Platform Support
- Linux implementation needs to be completed, particularly the top windows detection.
- macOS implementation is currently a stub and needs to be fully implemented.

### Testing
- Integration tests with real browser extensions need to be implemented once the browser extension is ported to core_v2.

## Dependencies
- Windows: win32gui, win32process, psutil
- Linux: X11 utilities (wmctrl, xprop), psutil
- macOS: TBD
- Browser integration: core_v2.browser.integration (to be implemented)




