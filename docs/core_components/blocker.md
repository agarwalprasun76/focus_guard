# FocusGuard Blocker Module

## Overview

The FocusGuard Blocker Module is a comprehensive system for detecting and blocking distracting content across browsers. It provides functionality to identify and close browser tabs based on domain categories, URL patterns, and custom rules. The module is designed with a flexible architecture that supports both browser extension-based and Chrome DevTools Protocol (CDP) approaches for tab management.

## Key Components

### 1. Domain Blocker (`domain_blocker.py`)

Core functionality for determining if a domain should be blocked based on various policies:

- **Domain Classification**: Categorizes domains (social, entertainment, productivity, etc.)
- **Whitelist/Blacklist**: Maintains lists of explicitly allowed or blocked domains
- **Category-Based Blocking**: Blocks entire categories of websites (e.g., social media)
- **Approved-Only Mode**: When enabled, only whitelisted domains are allowed

```python
from core.blocker.domain_blocker import should_block, block_reason

# Check if a domain should be blocked
if should_block("facebook.com", block_categories=["social"]):
    print("Facebook is blocked")

# Get the reason for blocking
reason = block_reason("youtube.com", block_categories=["entertainment"])
print(f"YouTube is blocked because it's categorized as: {reason}")
```

### 2. Browser Tab Blocker (`browser_tab_blocker.py`)

Handles the actual closing of browser tabs when they match blocking criteria:

- **Tab Detection**: Identifies browser tabs that should be blocked
- **Tab Closing**: Closes tabs using either browser extension or CDP
- **Blocking Logic**: Applies domain blocking rules to browser tabs
- **Extension Integration**: Uses browser extension for secure tab closing (recommended)
- **CDP Fallback**: Optional fallback to Chrome DevTools Protocol for development/testing

```python
from core.blocker.browser_tab_blocker import BrowserTabBlocker

# Create a blocker that blocks social media and entertainment sites
blocker = BrowserTabBlocker(
    block_categories=["social", "entertainment"],
    approved_only=False,
    use_extension=True,  # Use browser extension (recommended)
    use_cdp_fallback=False  # Disable CDP for production
)

# Check if a tab should be blocked
tab_info = {
    "tab_id": 123,
    "window_id": 1,
    "url": "https://www.youtube.com/watch?v=12345",
    "domain": "youtube.com",
    "title": "Funny Cat Videos"
}

if blocker.should_block_tab(tab_info):
    # Close the tab
    blocker.close_browser_tab(
        tab_info["tab_id"],
        tab_info["window_id"],
        tab_info["url"],
        tab_info["domain"],
        "blocked_entertainment"
    )
```

### 3. Browser Block Manager (`browser_block_manager.py`)

Coordinates blocking operations and provides a high-level interface:

- **Signal Processing**: Receives blocking signals from the coordinator
- **Queue Management**: Queues blocking operations to be processed asynchronously
- **Thread Safety**: Handles blocking operations in a separate thread
- **Status Reporting**: Provides status information about blocking operations

```python
from core.blocker.browser_block_manager import BrowserBlockManager

# Create a manager
manager = BrowserBlockManager(
    block_categories=["social", "entertainment"],
    approved_only=False
)

# Start the manager (begins processing the block queue)
manager.start()

# Queue a tab to be blocked
tab_info = {
    "tab_id": 123,
    "window_id": 1,
    "url": "https://www.facebook.com",
    "domain": "facebook.com",
    "reason": "productivity_session"
}
manager.queue_tab_block(tab_info)

# Add or remove block categories dynamically
manager.add_block_category("news")
manager.remove_block_category("productivity")

# Enable or disable approved-only mode
manager.set_approved_only_mode(True)

# Stop the manager when done
manager.stop()
```

### 4. Browser Tab Controller (`browser_tab_controller.py`)

Low-level interface for Chrome DevTools Protocol (CDP) operations:

- **Browser Detection**: Finds Chrome/Edge instances with debugging enabled
- **Tab Management**: Lists and closes tabs using CDP
- **Connection Handling**: Manages WebSocket connections to browser debugging interfaces

```python
from core.blocker.browser_tab_controller import BrowserTabController

# Create a controller (auto-detects browsers with debugging enabled)
controller = BrowserTabController(auto_detect=True)

# Get all open tabs
tabs = controller.get_all_tabs()

# Close a specific tab
for tab in tabs:
    if "facebook" in tab.get("url", ""):
        controller.close_tab(tab)
        break

# Clean up connections when done
controller.close_all_connections()
```

### 5. Chrome DevTools Client (`chrome_devtools_client.py`)

Direct client for Chrome DevTools Protocol:

- **CDP Communication**: Handles low-level protocol communication
- **WebSocket Management**: Maintains connections to browser debugging interfaces
- **Command Execution**: Sends CDP commands to browsers

> **Note**: This component is primarily used internally by the Browser Tab Controller and is not typically used directly.

## Tab Closing Approaches

The blocker module supports two approaches for closing browser tabs:

### 1. Browser Extension Approach (Recommended for Production)

Uses the FocusGuard browser extension to close tabs:

- **Advantages**:
  - No security warnings (doesn't require remote debugging mode)
  - Works with standard browser security model
  - More reliable across different sites
  
- **Implementation**:
  - Extension receives close commands via HTTP polling
  - Uses `chrome.tabs.remove()` API to close tabs
  - Communicates with FocusGuard application via tab server

### 2. Chrome DevTools Protocol Approach (Development/Testing)

Uses Chrome's remote debugging protocol to close tabs:

- **Advantages**:
  - Works without requiring extension installation
  - Useful for development and testing
  
- **Disadvantages**:
  - Requires enabling remote debugging mode (security risk)
  - Causes security warnings on many websites
  - Less reliable on some secure sites

## Usage Examples

### Basic Blocking Setup

```python
from core.blocker.browser_tab_blocker import BrowserTabBlocker

# Create a blocker with default settings
blocker = BrowserTabBlocker(
    block_categories=["social", "entertainment"],
    use_extension=True,  # Use browser extension (recommended)
    use_cdp_fallback=False  # Disable CDP for production
)

# Handle a block signal (e.g., from user interface)
block_signal = {
    "tab_id": 123,
    "window_id": 1,
    "url": "https://www.youtube.com/watch?v=12345",
    "domain": "youtube.com",
    "reason": "focus_session"
}
blocker.handle_tab_block_signal(block_signal)
```

### Using the Block Manager for Asynchronous Blocking

```python
from core.blocker.browser_block_manager import BrowserBlockManager

# Create and start the manager
manager = BrowserBlockManager(block_categories=["social"])
manager.start()

# Queue tabs for blocking (will be processed in background thread)
manager.queue_tab_block({
    "tab_id": 123,
    "window_id": 1,
    "url": "https://www.facebook.com",
    "domain": "facebook.com"
})

# Get current status
status = manager.get_status()
print(f"Blocking is {'active' if status['running'] else 'inactive'}")
print(f"Categories being blocked: {status['block_categories']}")

# Stop when done
manager.stop()
```

### Running the Demo

The module includes a demo script to showcase its functionality:

```bash
# Navigate to the demos directory
cd focus_guard/demos/blocker

# Run the demo
python demo_chrome_tab_blocker.py
```

The demo will:
1. Detect browsers with the FocusGuard extension or CDP debugging enabled
2. List all open tabs
3. Demonstrate tab closing on a selected tab
4. Show the block manager in action

## Configuration Options

### Browser Tab Blocker

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `block_categories` | List[str] | None | Categories to block (e.g., "social", "entertainment") |
| `approved_only` | bool | False | If True, only whitelisted domains are allowed |
| `use_extension` | bool | True | Use browser extension for tab closing |
| `use_cdp_fallback` | bool | False | Allow CDP fallback when extension isn't available |
| `auto_detect_browsers` | bool | True | Auto-detect browsers with debugging enabled |

### Browser Block Manager

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `block_categories` | List[str] | None | Categories to block |
| `approved_only` | bool | False | If True, only whitelisted domains are allowed |
| `log_dir` | str | None | Directory to store log files |

## Architecture

The blocker module follows a layered architecture:

1. **Domain Logic Layer** (`domain_blocker.py`)
   - Core decision logic for determining if domains should be blocked

2. **Tab Control Layer** (`browser_tab_blocker.py`, `browser_tab_controller.py`)
   - Handles the mechanics of detecting and closing tabs
   - Implements both extension-based and CDP-based approaches

3. **Management Layer** (`browser_block_manager.py`)
   - Coordinates blocking operations
   - Provides high-level interface for the rest of the application

4. **Protocol Layer** (`chrome_devtools_client.py`)
   - Handles low-level communication with browser debugging interfaces

## Recent Updates

### July 2025 Updates

- **Fixed Tab Server URL Parsing**: Resolved an issue where the tab server was not correctly handling URL query parameters in API endpoints, causing 404 errors when the extension tried to fetch commands.
- **Improved Extension-Server Communication**: Enhanced the reliability of command fetching and acknowledgment between the browser extension and tab server.
- **Added Detailed Error Logging**: Implemented more comprehensive logging for unmatched paths to aid in debugging.
- **Added Server Shutdown Delay**: Added a delay before server shutdown to ensure the extension has time to process pending commands.

## Future Enhancements

- **Application Blocking**: Extend blocking capabilities to desktop applications
- **Firefox Support**: Add support for Firefox via WebExtension API
- **Safari Support**: Add support for Safari (if applicable)
- **Machine Learning**: Implement ML-based classification of websites
- **Time-Based Rules**: Allow blocking based on time of day or duration
- **Reporting**: Generate reports on blocked content and productivity metrics

## Troubleshooting

### Common Issues

1. **Tabs not being detected**
   - Ensure the FocusGuard extension is installed and connected
   - For CDP: Make sure Chrome/Edge is running with remote debugging enabled

2. **Tabs not being closed**
   - Check extension permissions (requires "tabs" permission)
   - Verify that the tab server is running and accessible
   - Ensure the tab server correctly handles URL query parameters in API endpoints
   - For CDP: Some secure sites may block CDP commands

3. **Security Warnings**
   - This is expected when using CDP approach (remote debugging)
   - Switch to extension-based approach for production use

4. **Extension unable to fetch commands**
   - Verify the tab server correctly parses URL paths with query parameters
   - Check browser console for "Failed to fetch" errors
   - Ensure server endpoints like `/api/command?browser=Chrome` are properly handled

### Logging

The blocker module uses Python's logging framework. Logs are stored in:
- `%LOCALAPPDATA%\FocusGuard\browser_tab_blocker.log`
- `%LOCALAPPDATA%\FocusGuard\browser_block_manager.log`

You can adjust logging levels for more detailed information:

```python
import logging
logging.getLogger("browser_tab_blocker").setLevel(logging.DEBUG)
```
