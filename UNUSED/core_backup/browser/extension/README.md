# Browser Extension Integration

This directory contains components for browser extension integration in the Focus Guard application. The integration includes tab server, process management, and extension management functionality. The extension approach is used for browser tab monitoring and control instead of Chrome DevTools Protocol (CDP) due to security considerations.

## Architecture

The browser extension integration consists of the following components:

### 1. Tab Server (`tab_server.py` and `tab_server_v2.py`)

The tab server provides a REST API for communication with browser extensions. It handles:
- Tab data collection from connected browsers
- Extension connection status tracking
- Command sending to browser extensions (e.g., closing tabs)
- Tab closing endpoint for extension communication

### 2. Process Manager (`process_manager.py`)

The process manager handles the lifecycle of the tab server process:
- Starting and stopping the tab server process
- Monitoring the process status
- Auto-restarting the process if it crashes
- Providing status information

### 3. Extension Manager (`manager.py`)

The extension manager handles browser extension installation and management:
- Detecting installed browsers
- Installing extensions for different browser types
- Checking if extensions are installed
- Verifying extension connections with the tab server

### 4. Integration (`integration.py`)

The integration module provides a unified interface for all extension-related functionality:
- Initializing and coordinating all components
- Ensuring the tab server is running
- Installing and verifying extensions
- Providing tab data and command functionality

## Usage Examples

### Basic Integration Setup

```python
from core_v2.browser.extension.integration import get_extension_integration
from core_v2.browser.models.browser import BrowserType

# Get the extension integration (automatically starts the tab server)
integration = get_extension_integration()

# Install the extension for Chrome
integration.install_extension(BrowserType.CHROME)

# Verify the extension connection
if integration.verify_extension_connection(BrowserType.CHROME):
    print("Chrome extension is connected!")

# Get all open tabs
tabs = integration.get_all_tabs()
for tab in tabs:
    print(f"Tab: {tab['title']} - {tab['url']}")

# Get the active tab
active_tab = integration.get_active_tab()
if active_tab:
    print(f"Active tab: {active_tab['title']}")

# Close a tab (using browser extension approach)
integration.close_tab(tab_id="123", window_id="456", browser_name="chrome")
```

### Using Helper Functions

```python
from core_v2.browser.extension.integration import (
    install_browser_extension,
    verify_extension_connection,
    get_all_browser_tabs,
    get_active_browser_tab,
    close_browser_tab
)
from core_v2.browser.models.browser import BrowserType

# Install the extension for Chrome
install_browser_extension(BrowserType.CHROME)

# Verify the extension connection
if verify_extension_connection(BrowserType.CHROME):
    print("Chrome extension is connected!")

# Get all open tabs
tabs = get_all_browser_tabs()
for tab in tabs:
    print(f"Tab: {tab['title']} - {tab['url']}")

# Get the active tab
active_tab = get_active_browser_tab()
if active_tab:
    print(f"Active tab: {active_tab['title']}")

# Close a tab (using browser extension approach)
close_browser_tab(tab_id="123", window_id="456", browser_name="chrome")
```

## Integration with Domain Blocking

To integrate with domain blocking functionality:

```python
from core_v2.browser.extension.integration import get_extension_integration
from core_v2.browser.models.browser import BrowserType
from core_v2.models import Category

# Get the extension integration
integration = get_extension_integration()

# Get all tabs
tabs = integration.get_all_tabs()

# Close tabs in blocked categories
for tab in tabs:
    domain = tab.get('domain')
    if domain and is_domain_in_category(domain, Category.SOCIAL_MEDIA):
        integration.close_tab(tab['id'], tab['windowId'], tab['browser'])
        print(f"Closed blocked tab: {tab['title']}")
```

## Error Handling

The integration components include robust error handling and logging:

```python
import logging
from core_v2.browser.extension.integration import get_extension_integration

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get the extension integration
integration = get_extension_integration()

# Try to get tabs with error handling
try:
    tabs = integration.get_all_tabs()
    print(f"Found {len(tabs)} tabs")
except Exception as e:
    print(f"Error getting tabs: {e}")
    # Try restarting the tab server
    integration.restart_tab_server()
```

## Platform-Specific Considerations

The integration handles platform-specific differences automatically:

- **Windows**: Uses appropriate process creation flags and termination methods
- **macOS/Linux**: Uses standard POSIX signals for process management

## Extension Installation

Extension installation varies by browser:

- **Chrome/Brave/Edge**: Uses the `--load-extension` flag for development
- **Firefox**: Opens the add-ons page for manual installation
- **Safari**: Requires App Store installation (not fully automated)

For production use, extensions should be packaged and distributed through the respective browser stores.

## Tab Closing Implementation

The tab closing functionality uses the browser extension approach instead of Chrome DevTools Protocol (CDP) for the following reasons:

1. **Security**: CDP requires enabling remote debugging mode which causes security warnings on many websites
2. **Compatibility**: The extension approach works across all supported browsers
3. **User Experience**: No security warnings are shown to users

### Extension Message Protocol for Tab Closing

Tab closing uses a message format with:
- Action: `close_tab`
- Data: Contains `tabId`, `windowId`, `url`, `domain`, and `reason`

### Implementation Components

1. **Browser Extension**: The extension's background.js handles tab close commands via chrome.tabs.remove()
2. **Tab Server**: Provides a tab closing endpoint in tab_server_v2.py
3. **Browser Integration**: The close_tab method in browser_integration_v2.py sends commands to the extension
4. **Tab Blocker**: Uses the browser integration instead of CDP for closing tabs
