# Chrome/Edge Tab Closing Integration Plan

## Overview

This document outlines the implementation plan for integrating real Chrome/Edge tab closing functionality into the Focus Guard browser tab blocker. The implementation will use the Chrome DevTools Protocol (CDP) to connect to the browser's debugging interface and close tabs programmatically.

## Components

### 1. Chrome DevTools Protocol Client

**File:** `chrome_devtools_client.py`

This module will handle the low-level communication with Chrome's debugging interface:

- Connect to Chrome's remote debugging port
- Send CDP commands to list tabs, close tabs, etc.
- Handle WebSocket communication with the CDP

### 2. Browser Tab Controller

**File:** `browser_tab_controller.py`

This module will provide a high-level interface for controlling browser tabs:

- Find Chrome/Edge instances and their debugging ports
- Connect to multiple browser instances if needed
- Map between FocusGuard tab IDs and Chrome tab IDs
- Close specific tabs by URL or ID
- Support different browsers (Chrome, Edge, etc.)

### 3. Integration with Existing Blocker

**File:** `browser_tab_blocker.py` (update)

Updates to the existing tab blocker:

- Replace the placeholder tab closing method with actual implementation
- Connect to the Browser Tab Controller
- Handle browser-specific errors and edge cases

## Implementation Steps

### Phase 1: Chrome DevTools Protocol Client

1. Create a basic CDP client that can:
   - Connect to Chrome's debugging port (default: 9222)
   - List all open tabs
   - Close a tab by its ID
   - Handle connection errors and retries

2. Implement WebSocket communication for CDP commands
   - Use `websocket-client` library for WebSocket communication
   - Handle JSON message formatting and parsing
   - Implement basic command/response pattern

### Phase 2: Browser Tab Controller

1. Implement browser detection
   - Find running Chrome/Edge instances
   - Determine if debugging is enabled
   - Launch Chrome with debugging if needed

2. Create tab management functionality
   - List all tabs across all browser instances
   - Match tabs by URL or domain
   - Close tabs with proper error handling

3. Implement browser-specific adaptations
   - Support Chrome-specific parameters
   - Support Edge-specific parameters
   - Allow for future browser extensions

### Phase 3: Integration and Testing

1. Update `browser_tab_blocker.py`
   - Replace placeholder with actual tab closing
   - Add configuration for debugging ports
   - Handle browser-specific errors

2. Create test cases
   - Test with Chrome
   - Test with Edge
   - Test with multiple browser instances

3. Update demos
   - Create a real-world demo with actual browser control
   - Document usage and limitations

## Technical Requirements

### Dependencies

- `websocket-client`: For WebSocket communication with CDP
- `requests`: For HTTP communication with CDP endpoints
- `psutil`: For process detection and management

### Chrome/Edge Configuration

Chrome/Edge must be launched with remote debugging enabled:

```
chrome.exe --remote-debugging-port=9222
```

or

```
msedge.exe --remote-debugging-port=9222
```

### Security Considerations

- Only connect to localhost debugging ports
- Implement proper error handling for security-related errors
- Document security implications for users

## Timeline

1. Chrome DevTools Protocol Client: 1-2 days
2. Browser Tab Controller: 2-3 days
3. Integration and Testing: 1-2 days

Total estimated time: 4-7 days

## Future Enhancements

- Firefox support via WebExtension API
- Safari support (if applicable)
- Browser extension fallback for cases where CDP is not available
- User configuration for browser-specific settings

python -m PyInstaller focus_guard_native_host.spec