# Browser Integration Module

## Overview

The Browser Integration module provides accurate tracking of browser tabs and their productivity status by directly connecting with browser extensions. This module significantly improves the accuracy of distraction detection by identifying exactly which tab is active in a browser window, rather than relying solely on window title parsing.

## Architecture

The Browser Integration module consists of the following components:

### 1. Tab Server (`tab_server.py`)

- HTTP server that receives tab information from browser extensions
- Runs on localhost with a configurable port (default: 5000)
- Provides endpoints for tab data submission and status checks
- Thread-safe storage of tab data
- Singleton pattern for application-wide access

### 2. Tab Tracker Integration (`tab_tracker_integration.py`)

- Bridges the Tab Server and BrowserTabTracker
- Syncs tab data from extensions to the core tracking system
- Runs a background thread for continuous synchronization
- Provides methods to get all tabs and the active tab
- Singleton pattern for application-wide access

### 3. Tab Monitor (`tab_monitor.py`)

- Main module for monitoring and displaying browser tabs
- Integrates with browser extensions when available
- Falls back to window title parsing when extensions are not available
- Provides detailed tab information including URLs, domains, and productivity status
- Command-line interface for debugging and monitoring

### 4. Browser Extension

- Microsoft Edge extension (compatible with Chromium-based browsers)
- Sends tab information to the Tab Server
- Identifies the active tab in each browser window
- Provides accurate URL and title information

### 5. Log Parser Components

- **Tab Data Parser**: Parses browser tab snapshot data from JSON files
- **Log Activity Parser**: Analyzes debug logs to extract tab activity over time
- **Enhanced Log Parser**: Correlates browser tab activity with foreground application logs for accurate focus time tracking

## Integration with Distraction Detector

The Browser Integration module enhances the Distraction Detector by:

1. Providing accurate information about the active tab in each browser window
2. Enabling domain-based productivity classification
3. Reducing false positives in distraction detection
4. Improving the user experience by minimizing unnecessary alerts

## Usage

### Command Line Interface

```bash
# Run the tab monitor with default settings
python scripts/list_browser_tabs.py

# Run with debug output
python scripts/list_browser_tabs.py --debug

# Run and stop the server after execution
python scripts/list_browser_tabs.py --stop-server
```

### Programmatic Usage

```python
from core.browser_integration.tab_monitor import monitor_tabs

# Get tab information
tab_info = monitor_tabs(debug=True)

# Access tab data
active_tab = tab_info["active_tab"]
all_tabs = tab_info["extension_tabs"]
using_extension = tab_info["using_extension"]

# Check if active tab is productive
if active_tab and active_tab["is_productive"]:
    print(f"Currently on productive tab: {active_tab['title']}")
```

## Browser Extension Installation

1. Open Microsoft Edge and navigate to `edge://extensions/`
2. Enable 'Developer mode' in the bottom-left corner
3. Click 'Load unpacked' and select the folder: `browser_extension/focus_guard_extension`
4. The extension should appear with the FocusGuard (FG) icon

## Extension Compatibility

- **Microsoft Edge**: Fully supported and tested
- **Google Chrome**: Compatible but requires manual installation
- **Firefox**: Not currently supported (future development)
- **Safari**: Not currently supported (future development)

## Log Parsing and Analysis

The Browser Integration module includes robust log parsing capabilities to analyze browser activity and correlate it with foreground application data.

### Tab Data Parser

- Parses browser tab snapshot data from JSON files
- Supports both v0 and current snapshot formats
- Extracts tab information including URL, title, and active status
- Handles browser-specific metadata

### Log Activity Parser

- Analyzes debug logs to extract tab activity over time
- Handles non-standard JSON formatting in log files (single quotes, escaped backslashes)
- Calculates active time for each tab and domain
- Provides summaries and analytics of browser usage

### Enhanced Log Parser

- Correlates browser tab activity with foreground application logs
- Distinguishes between browser-active time and true foreground time
- Provides accurate focus time metrics by domain and tab
- Shows significant accuracy improvements over browser-only tracking
- Handles timestamp matching between different log sources

### Log File Rotation

- Log files are rotated daily (new file per calendar day)
- Naming convention: `focusguard_debug_YYYY-MM-DD.log` and `activity_log_YYYY-MM-DD.log`
- Prevents excessive file sizes and improves manageability
- Enables date-based analysis and reporting

### Demo Scripts

The following demo scripts are available in the `demos/browser_integration/` directory:

- `demo_tab_parser.py`: Demonstrates parsing of tab snapshot data
- `demo_log_activity.py`: Demonstrates parsing of debug logs for tab activity
- `demo_enhanced_log_parser.py`: Demonstrates correlation of browser and activity logs

## Data Flow

1. Browser extension monitors tabs and identifies the active tab
2. Extension sends tab data to the Tab Server via HTTP
3. Tab Tracker Integration syncs this data to the BrowserTabTracker
4. Distraction Detector uses this information to determine if the active tab is productive
5. Alert System generates alerts based on this determination

## Future Enhancements

- Firefox and Safari extension support
- Tab history tracking for better context awareness
- Tab grouping and session management
- Productivity analytics dashboard
- Automatic classification learning from user behavior

## Dependencies

- Python 3.6+
- HTTP server capabilities
- Browser extension permissions for tab access
- Cross-platform window enumeration (for fallback mode)

## Troubleshooting

### Common Issues

1. **Extension not connecting**:
   - Ensure the Tab Server is running
   - Check for firewall blocking localhost connections
   - Verify the extension is properly installed

2. **Incorrect tab detection**:
   - Enable debug mode to see detailed information
   - Check if the browser is supported
   - Verify that the extension has the necessary permissions

3. **Performance issues**:
   - Adjust the sync interval in Tab Tracker Integration
   - Limit the number of tabs being tracked
   - Check for other processes using the same port

## Code Examples

### Getting Active Tab Information

```python
from core.distraction_detector.browser_tracker import BrowserTabTracker

tracker = BrowserTabTracker()
active_tab = tracker.get_active_tab_info()

print(f"Active Tab: {active_tab['title']}")
print(f"Domain: {active_tab['domain']}")
print(f"Productive: {'Yes' if active_tab['is_productive'] else 'No'}")
```

### Checking if Current Browser Window is Productive

```python
from core.distraction_detector.distraction_detector import DistractionDetector
from core.cross_platform.cross_platform import get_active_window_info

detector = DistractionDetector(allowed_apps=['code.exe'])
window = get_active_window_info()

if window['app_name'].lower() in ['chrome.exe', 'msedge.exe', 'firefox.exe']:
    is_distracted = detector.is_distracted(window)
    print(f"Current browser window is {'productive' if not is_distracted else 'distracting'}")
```
