# Activity Monitor Refactoring Plan

## Overview

This document outlines the detailed plan for refactoring the activity monitor module in Focus Guard, integrating it with the new `core_v2` architecture. The goal is to create a more modular, maintainable, and extensible activity monitoring system while preserving the existing functionality.

## Current Architecture

The current activity monitor system consists of:

1. **ActivityMonitor Class** (`core/activity_monitor.py`): A high-level, OS-agnostic interface that provides methods for retrieving window information
2. **Cross-Platform Utilities** (`core/utils/cross_platform.py`): Low-level functions that implement OS-specific window detection
3. **Browser Integration** (if present): Integration with browser extensions for tab monitoring

## Identified Opportunities for Improvement

1. **Platform Abstraction**: Better separation of platform-specific code
2. **Domain Model Integration**: Leverage core_v2's domain models for URLs and domains
3. **Modular Design**: Clearer separation of concerns between components
4. **Testability**: Improved structure for unit and integration testing
5. **Browser Integration**: Cleaner interface with browser monitoring components

## Refactoring Strategy

We will create a new activity monitoring module in `core_v2` with a clean, modular architecture while preserving the existing functionality. The approach is:

1. Create a clean directory structure with clear separation of concerns
2. Define clean interfaces for all components
3. Port existing functionality to the new structure
4. Improve incrementally, focusing on modularity and testability

## Directory Structure

```
core_v2/
├── activity/
│   ├── __init__.py
│   ├── models.py         # Data models for activity information
│   ├── monitor.py        # Core monitoring functionality
│   ├── browser/          # Browser integration components
│   │   ├── __init__.py
│   │   ├── tab_monitor.py
│   │   └── extension_integration.py
│   └── platform/         # Platform-specific implementations
│       ├── __init__.py
│       ├── windows.py
│       ├── linux.py
│       └── macos.py
```

## Detailed Implementation Plan

### Phase 1: Foundation (Core Structure and Interfaces)

1. **Create Directory Structure**
   - Set up the `core_v2/activity` directory and subdirectories
   - Create empty `__init__.py` files for each package

2. **Define Core Activity Models**
   - Create `activity/models.py` with:
     - `WindowInfo` class for active window data
     - `ActivityEvent` class for timestamped activity records
     - Integration with core_v2's domain models (URL, Domain)

3. **Define Base Interfaces**
   - Create `activity/monitor.py` with:
     - `ActivityMonitor` interface for all activity monitoring
     - Platform detection and abstraction
     - Integration with browser monitoring

### Phase 2: Platform Abstraction and Implementation

1. **Platform Interface**
   - Create `activity/platform/base.py` with:
     - `PlatformActivityMonitor` abstract base class defining the interface
     - Required methods: `get_active_window()`, `get_top_windows()`, `is_supported()`
     - Documentation for platform implementers

2. **Platform Factory**
   - Create `activity/platform/__init__.py` with:
     - Platform detection logic
     - Factory method to instantiate the appropriate implementation
     - Fallback mechanism for unsupported platforms

3. **Windows Implementation (Primary Focus)**
   - Create `activity/platform/windows.py` with:
     - `WindowsActivityMonitor` class that implements the platform interface
     - Port existing Windows-specific code from `cross_platform.py`
     - Use `win32gui`, `win32process`, and `psutil` for window detection
     - Comprehensive implementation with all features

4. **Other Platform Stubs**
   - Create placeholder implementations for other platforms:
     - `activity/platform/linux.py`: Basic implementation with Linux-specific code
     - `activity/platform/macos.py`: Stub with clear TODOs and requirements
     - `activity/platform/android.py`: Stub with interface documentation
     - `activity/platform/ios.py`: Stub with interface documentation
   - Each stub should:
     - Implement the interface
     - Return appropriate error messages or empty results
     - Document requirements for full implementation

### Phase 3: Browser Integration

1. **Browser Tab Monitor**
   - Create `activity/browser/tab_monitor.py` with:
     - `BrowserTabMonitor` class for browser tab monitoring
     - Integration with browser extensions
     - Fallback to window title parsing when extensions are not available

2. **Extension Integration**
   - Create `activity/browser/extension_integration.py` with:
     - `ExtensionIntegration` class for communicating with browser extensions
     - Port existing extension integration code

### Phase 4: Integration with ActivityMonitor

1. **Enhance ActivityMonitor**
   - Update `activity/monitor.py` to:
     - Integrate with browser tab monitoring
     - Provide comprehensive window and tab information
     - Ensure cross-platform compatibility

2. **Create API**
   - Update `core_v2/api.py` to expose activity monitoring functionality
   - Ensure backward compatibility with existing code

## Code Examples

### Core Models

```python
# core_v2/activity/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from core_v2.domain.models import URL, Domain

@dataclass
class WindowInfo:
    """Information about an active window."""
    app_name: str
    window_title: str
    pid: int
    timestamp: datetime
    url: Optional[URL] = None
    domain: Optional[Domain] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowInfo':
        """Create a WindowInfo object from a dictionary."""
        # Implementation
        pass
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        # Implementation
        pass

@dataclass
class ActivityEvent:
    """A timestamped activity event."""
    window_info: WindowInfo
    event_type: str  # 'focus', 'blur', etc.
    duration: Optional[float] = None  # Duration in seconds
```

### Activity Monitor

```python
# core_v2/activity/monitor.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from core_v2.activity.models import WindowInfo
from core_v2.domain.models import URL, Domain
from core_v2.utils.domain_utils import create_url_from_string, create_domain_from_url

class ActivityMonitor:
    """Monitor user activity across applications and browser tabs."""
    
    def __init__(self):
        # Initialize platform-specific implementation
        self._platform_impl = self._get_platform_implementation()
        self._browser_monitor = None  # Initialized lazily
        
    def _get_platform_implementation(self):
        """Get the appropriate platform implementation.
        
        Uses a factory pattern to find and instantiate the first supported
        platform implementation. Falls back to a stub implementation that
        provides appropriate error messages if no supported implementation
        is found.
        """
        from core_v2.activity.platform import get_platform_implementation
        return get_platform_implementation()

# In core_v2/activity/platform/__init__.py
def get_platform_implementation():
    """Factory function to get the appropriate platform implementation."""
    # Try each implementation in order of preference
    implementations = []
    
    # Import all available implementations
    # Each one registers itself if available
    try:
        from core_v2.activity.platform.windows import WindowsActivityMonitor
        implementations.append(WindowsActivityMonitor)
    except ImportError:
        pass
        
    try:
        from core_v2.activity.platform.linux import LinuxActivityMonitor
        implementations.append(LinuxActivityMonitor)
    except ImportError:
        pass
        
    try:
        from core_v2.activity.platform.macos import MacOSActivityMonitor
        implementations.append(MacOSActivityMonitor)
    except ImportError:
        pass
    
    # Find the first supported implementation
    for impl in implementations:
        if impl.is_supported():
            return impl()
    
    # Fall back to stub implementation
    from core_v2.activity.platform.stub import StubActivityMonitor
    return StubActivityMonitor()
    
    def _get_browser_monitor(self):
        """Lazily initialize the browser monitor."""
        if self._browser_monitor is None:
            from core_v2.activity.browser.tab_monitor import BrowserTabMonitor
            self._browser_monitor = BrowserTabMonitor()
        return self._browser_monitor
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window."""
        window_data = self._platform_impl.get_active_window()
        if not window_data:
            return None
            
        # Create WindowInfo object
        window_info = WindowInfo(
            app_name=window_data['app_name'],
            window_title=window_data['window_title'],
            pid=window_data['pid'],
            timestamp=window_data.get('timestamp', datetime.now())
        )
        
        # Try to extract URL and domain if it's a browser
        if self._is_browser(window_info.app_name):
            # Try to get browser tab information
            browser_monitor = self._get_browser_monitor()
            active_tab = browser_monitor.get_active_tab()
            
            if active_tab and active_tab.get('url'):
                # Use tab information
                url_str = active_tab['url']
                url = create_url_from_string(url_str)
                window_info.url = url
                window_info.domain = url.domain
            else:
                # Fall back to window title parsing
                url_str = self._extract_url_from_title(window_info.window_title)
                if url_str:
                    url = create_url_from_string(url_str)
                    window_info.url = url
                    window_info.domain = url.domain
                
        return window_info
        
    def get_top_windows(self, top_region: int = 200) -> List[WindowInfo]:
        """Get visible windows at the top of the screen."""
        windows_data = self._platform_impl.get_top_windows(top_region)
        return [WindowInfo.from_dict(window_data) for window_data in windows_data]
        
    def _is_browser(self, app_name: str) -> bool:
        """Check if an application is a browser."""
        browsers = ['chrome', 'firefox', 'edge', 'safari', 'opera', 'brave']
        return any(browser in app_name.lower() for browser in browsers)
        
    def _extract_url_from_title(self, title: str) -> Optional[str]:
        """Extract URL from window title if possible."""
        # Implementation
        pass
```

### Platform Interface and Windows Implementation

```python
# core_v2/activity/platform/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class PlatformActivityMonitor(ABC):
    """Abstract base class for platform-specific activity monitoring."""
    
    @abstractmethod
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently active window.
        
        Returns:
            Dict with keys: app_name, window_title, pid, timestamp
            or None if information cannot be retrieved
        """
        pass
    
    @abstractmethod
    def get_top_windows(self, top_region: int = 200) -> List[Dict[str, Any]]:
        """Get visible windows at the top of the screen.
        
        Args:
            top_region: Maximum distance from top of screen in pixels
            
        Returns:
            List of window information dictionaries
        """
        pass
    
    @classmethod
    @abstractmethod
    def is_supported(cls) -> bool:
        """Check if this platform implementation is supported on the current system.
        
        Returns:
            True if all dependencies and system requirements are met
        """
        pass

# core_v2/activity/platform/windows.py
from typing import Optional, Dict, Any, List
import win32gui
import win32process
import psutil
from datetime import datetime
from core_v2.activity.platform.base import PlatformActivityMonitor

class WindowsActivityMonitor(PlatformActivityMonitor):
    """Windows-specific implementation of activity monitoring."""
    
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently active window on Windows."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            app_name = self._get_process_name(pid)
            window_title = win32gui.GetWindowText(hwnd)
            
            return {
                'app_name': app_name,
                'window_title': window_title,
                'pid': pid,
                'timestamp': datetime.now()
            }
        except Exception:
            return None
            
    def get_top_windows(self, top_region: int = 200) -> List[Dict[str, Any]]:
        """Get visible windows at the top of the screen on Windows."""
        # Implementation
        pass
        
    def _get_process_name(self, pid: int) -> str:
        """Get the process name from a process ID."""
        try:
            process = psutil.Process(pid)
            return process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "Unknown"
            
    @classmethod
    def is_supported(cls) -> bool:
        """Check if Windows implementation is supported."""
        try:
            import win32gui
            import win32process
            import psutil
            return True
        except ImportError:
            return False
```

### Browser Tab Monitor

```python
# core_v2/activity/browser/tab_monitor.py
from typing import Optional, Dict, Any, List
import json
import requests

class BrowserTabMonitor:
    """Monitor browser tabs across supported browsers."""
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        self.server_url = server_url
        
    def get_active_tab(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently active browser tab."""
        try:
            response = requests.get(f"{self.server_url}/active_tab", timeout=0.5)
            if response.status_code == 200:
                return response.json()
            return None
        except requests.RequestException:
            return None
        
    def get_all_tabs(self) -> List[Dict[str, Any]]:
        """Get information about all open browser tabs."""
        try:
            response = requests.get(f"{self.server_url}/tabs", timeout=0.5)
            if response.status_code == 200:
                return response.json()
            return []
        except requests.RequestException:
            return []
```

## Testing Strategy

### 1. Unit Tests

Create comprehensive unit tests for each component:

- **Models Tests**:
  - Test WindowInfo creation, conversion, and validation
  - Test ActivityEvent creation and properties

- **Platform Implementation Tests**:
  - Mock system calls for window detection
  - Test platform-specific functionality in isolation

- **Browser Integration Tests**:
  - Mock browser extension responses
  - Test tab information parsing and integration

### 2. Integration Tests

Test the integration between components:

- **ActivityMonitor with Platform Implementations**:
  - Test correct platform detection and initialization
  - Test window information retrieval across platforms

- **ActivityMonitor with Browser Integration**:
  - Test browser detection and tab information retrieval
  - Test fallback to window title parsing

### 3. Cross-Platform Tests

Ensure functionality across different operating systems:

- **Manual Testing**:
  - Test on Windows, Linux, and macOS
  - Verify window detection and browser integration

- **CI Testing**:
  - Use platform-specific mocks for automated testing
  - Ensure compatibility with all supported platforms

## Implementation Timeline

1. **Week 1: Foundation**
   - Create directory structure
   - Define core models and interfaces
   - Set up initial tests

2. **Week 2: Platform Implementations**
   - Implement Windows-specific functionality
   - Implement Linux-specific functionality
   - Implement macOS-specific functionality (if resources available)

3. **Week 3: Browser Integration**
   - Implement browser tab monitoring
   - Integrate with ActivityMonitor
   - Test browser detection and integration

4. **Week 4: Testing and Refinement**
   - Complete unit and integration tests
   - Refine implementation based on test results
   - Document API and usage examples

## Migration Strategy

1. **Parallel Implementation**:
   - Keep the original activity_monitor working
   - Implement the core_v2 version alongside it

2. **Gradual Adoption**:
   - Update dependent modules to use the new implementation
   - Use feature flags to control which implementation is active

3. **Deprecation Plan**:
   - Mark the original implementation as deprecated
   - Set a timeline for complete migration

## Platform Extension Guide

To add support for a new platform in the future, follow these steps:

1. **Create a new implementation file**:
   ```
   core_v2/activity/platform/new_platform.py
   ```

2. **Implement the PlatformActivityMonitor interface**:
   ```python
   from core_v2.activity.platform.base import PlatformActivityMonitor
   
   class NewPlatformActivityMonitor(PlatformActivityMonitor):
       def get_active_window(self):
           # Implementation
           pass
           
       def get_top_windows(self, top_region=200):
           # Implementation
           pass
           
       @classmethod
       def is_supported(cls):
           # Check if this platform is supported
           return True  # If all requirements are met
   ```

3. **Add platform detection to the factory**:
   ```python
   # In core_v2/activity/platform/__init__.py
   try:
       from core_v2.activity.platform.new_platform import NewPlatformActivityMonitor
       platform_implementations.append(NewPlatformActivityMonitor)
   except ImportError:
       pass
   ```

4. **Create platform-specific tests**:
   ```
   tests/core_v2/activity/platform/test_new_platform.py
   ```

5. **Document platform-specific requirements**:
   - Required dependencies
   - System permissions
   - API limitations
   - Platform-specific behaviors

## Conclusion

This refactoring plan provides a comprehensive approach to integrating the activity monitor with the core_v2 architecture, with a focus on Windows for the initial implementation but designed for extensibility to other platforms in the future. By following this plan, we will create a more modular, maintainable, and extensible activity monitoring system that can be easily extended to support additional platforms with minimal refactoring.



Remaining Work (Post-Browser Extension Port)
The following tasks have been deferred until after the browser extension is ported to core_v2:

1. Browser Integration Completion
Connect the activity monitor to the ported browser extension
Implement the 
BrowserIntegration
 class in core_v2.browser.integration
Update the 
BrowserExtensionIntegration
 class to use the real browser extension
Complete browser tab monitoring for Chrome and Edge
Implement tab closing functionality as described in the browser extension plan
2. Platform Implementation Completion
Complete the Linux implementation, particularly the top windows detection
Implement the macOS version with proper platform-specific APIs
Fix platform detection and factory implementation issues identified in tests
3. Testing Completion
Fix failing unit tests for platform implementations
Complete integration tests with real browser extension
Add platform-specific tests for Linux and macOS
Add end-to-end tests for the entire activity monitoring system
4. Documentation and Usage Examples
Complete API documentation
Add usage examples for common scenarios
Document integration patterns with other Focus Guard components
Update platform extension guide with lessons learned
5. Performance Optimization
Optimize window detection for better performance
Implement caching strategies for frequent queries
Benchmark and optimize browser integration
6. Integration with Other Core_v2 Components
Connect activity monitor to focus rules engine
Integrate with notification system
Connect to analytics and reporting components
