# Alert System Refactoring Plan

## Overview

This document outlines the plan for refactoring the alert system from the legacy `core` module into the new modular `core_v2` architecture. The goal is to create a more maintainable, testable, and extensible alert system while preserving existing functionality and ensuring cross-platform compatibility.

## Current Architecture

The current alert system is organized as follows:

1. **AlertSystem Class**
   - Main controller that manages multiple alert providers
   - Implements alert history tracking and escalation logic
   - Handles cooldown periods between alerts

2. **AlertProvider Base Class**
   - Abstract base class for all alert providers
   - Defines the common interface for sending alerts

3. **Concrete Alert Providers**
   - PopupAlertProvider: Shows visual popup alerts using platform-specific methods
   - SoundAlertProvider: Plays sound alerts with configurable volume and repetition
   - DesktopNotificationProvider: Uses native OS notification systems
   - WebhookAlertProvider: Sends alerts to configurable webhook endpoints
   - EmailAlertProvider: Sends email notifications for alerts
   - AppBlockerProvider: Can temporarily block distracting applications

4. **Platform-Specific Code**
   - Platform detection and specific implementations are embedded within each provider
   - Windows, macOS, and Linux implementations are mixed within the provider classes

## Identified Opportunities for Improvement

1. **Separation of Platform-Specific Code**
   - Current implementation mixes platform-specific code within provider classes
   - Need to separate platform concerns from provider functionality

2. **Modular Architecture**
   - Move to a more modular design with clear separation of concerns
   - Improve testability through better abstraction

3. **Extensibility**
   - Make it easier to add new alert providers
   - Simplify adding support for new platforms

4. **Consistency with core_v2**
   - Align with the architectural patterns used in core_v2
   - Use similar patterns for cross-platform support as in the activity monitor

5. **Code Duplication**
   - Reduce duplication of platform-specific code across providers
   - Create reusable platform utilities

## Refactoring Strategy

We will refactor the alert system using a layered architecture:

1. **Core Layer**
   - Platform-agnostic alert system logic
   - Provider registration and management
   - Alert history and escalation logic

2. **Provider Layer**
   - Abstract provider interfaces
   - Concrete provider implementations
   - Platform-agnostic provider logic

3. **Platform Layer**
   - Platform-specific implementations
   - Factory for selecting appropriate platform implementation
   - Stub implementations for unsupported platforms

## Directory Structure

```
core_v2/
  alert/
    __init__.py                  # Package exports
    alert_system.py              # Main alert system class
    models.py                    # Data models for alerts
    
    providers/
      __init__.py                # Provider registration
      base.py                    # Base provider classes
      popup.py                   # Popup alert provider
      sound.py                   # Sound alert provider
      desktop_notification.py    # Desktop notification provider
      webhook.py                 # Webhook alert provider
      email.py                   # Email alert provider
      app_blocker.py             # App blocker provider
      
    platform/
      __init__.py                # Platform factory
      base.py                    # Platform interface
      windows.py                 # Windows-specific implementations
      macos.py                   # macOS-specific implementations
      linux.py                   # Linux-specific implementations
      android.py                 # Android stub implementation
      ios.py                     # iOS stub implementation
      stub.py                    # Fallback implementation
      
    utils/
      __init__.py
      config.py                  # Configuration utilities
      history.py                 # Alert history management
      escalation.py              # Escalation strategy utilities
```

## Detailed Implementation Plan

### Phase 1: Foundation

1. **Core Data Models**
   - Create `alert/models.py` with:
     - `AlertLevel` enum (NORMAL, WARNING, CRITICAL)
     - `AlertInfo` dataclass for alert metadata
     - `AlertHistoryEntry` for tracking alert history

2. **Platform Interface**
   - Create `alert/platform/base.py` with:
     - `PlatformAlertInterface` abstract base class
     - Required methods: `show_notification()`, `play_sound()`, `is_supported()`
     - Documentation for platform implementers

3. **Platform Factory**
   - Create `alert/platform/__init__.py` with:
     - Platform detection logic
     - Factory method to instantiate the appropriate implementation
     - Fallback mechanism for unsupported platforms

4. **Provider Base Classes**
   - Create `alert/providers/base.py` with:
     - `AlertProvider` abstract base class
     - Common provider functionality
     - Platform-agnostic provider logic

### Phase 2: Platform Implementations

1. **Windows Implementation (Primary Focus)**
   - Create `alert/platform/windows.py` with:
     - `WindowsAlertPlatform` class implementing the platform interface
     - PowerShell-based notification methods
     - Windows sound playback
     - Windows-specific utilities

2. **Other Platform Implementations**
   - Create basic implementations for other platforms:
     - `alert/platform/macos.py`: AppleScript-based notifications
     - `alert/platform/linux.py`: Linux notification systems
     - `alert/platform/android.py`: Stub implementation
     - `alert/platform/ios.py`: Stub implementation
     - `alert/platform/stub.py`: Fallback implementation

3. **Platform Utilities**
   - Implement shared utilities for platform-specific code
   - Create helpers for common operations across platforms

### Phase 3: Provider Implementations

1. **Popup Alert Provider**
   - Create `alert/providers/popup.py` with:
     - `PopupAlertProvider` class
     - Platform-agnostic popup logic
     - Integration with platform-specific implementations

2. **Sound Alert Provider**
   - Create `alert/providers/sound.py` with:
     - `SoundAlertProvider` class
     - Platform-agnostic sound alert logic
     - Integration with platform-specific implementations

3. **Desktop Notification Provider**
   - Create `alert/providers/desktop_notification.py` with:
     - `DesktopNotificationProvider` class
     - Platform-agnostic notification logic
     - Integration with platform-specific implementations

4. **Other Providers**
   - Create remaining providers:
     - `alert/providers/webhook.py`
     - `alert/providers/email.py`
     - `alert/providers/app_blocker.py`

### Phase 4: Alert System Core

1. **Alert System Class**
   - Create `alert/alert_system.py` with:
     - `AlertSystem` class
     - Provider registration and management
     - Alert history tracking
     - Escalation logic
     - Configuration management

2. **Utility Classes**
   - Create utility classes for:
     - Configuration management
     - Alert history persistence
     - Escalation strategy implementation

3. **Package Integration**
   - Create `alert/__init__.py` with:
     - Public API exports
     - Convenience functions
     - Default configurations

## Code Examples

### Platform Interface

```python
# core_v2/alert/platform/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class PlatformAlertInterface(ABC):
    """Abstract base class for platform-specific alert functionality."""
    
    @abstractmethod
    def show_notification(self, title: str, message: str, level: str, options: Dict[str, Any] = None) -> bool:
        """Show a platform-native notification.
        
        Args:
            title: Title of the notification
            message: Content of the notification
            level: Alert level ("normal", "warning", "critical")
            options: Additional platform-specific options
            
        Returns:
            bool: True if notification was shown successfully
        """
        pass
    
    @abstractmethod
    def play_sound(self, sound_type: str, options: Dict[str, Any] = None) -> bool:
        """Play a sound alert.
        
        Args:
            sound_type: Type of sound to play ("alert", "warning", "critical")
            options: Additional options like volume, repeat count
            
        Returns:
            bool: True if sound was played successfully
        """
        pass
    
    @classmethod
    @abstractmethod
    def is_supported(cls) -> bool:
        """Check if this platform implementation is supported on the current system.
        
        Returns:
            bool: True if all dependencies and system requirements are met
        """
        pass
```

### Platform Factory

```python
# core_v2/alert/platform/__init__.py
from typing import Type, List
from core_v2.alert.platform.base import PlatformAlertInterface
from core_v2.alert.platform.stub import StubAlertPlatform

def get_platform_implementation() -> PlatformAlertInterface:
    """Factory function to get the appropriate platform implementation."""
    # Try each implementation in order of preference
    implementations: List[Type[PlatformAlertInterface]] = []
    
    # Import all available implementations
    try:
        from core_v2.alert.platform.windows import WindowsAlertPlatform
        implementations.append(WindowsAlertPlatform)
    except ImportError:
        pass
        
    try:
        from core_v2.alert.platform.macos import MacOSAlertPlatform
        implementations.append(MacOSAlertPlatform)
    except ImportError:
        pass
        
    try:
        from core_v2.alert.platform.linux import LinuxAlertPlatform
        implementations.append(LinuxAlertPlatform)
    except ImportError:
        pass
    
    # Find the first supported implementation
    for impl in implementations:
        if impl.is_supported():
            return impl()
    
    # Fall back to stub implementation
    return StubAlertPlatform()
```

### Windows Platform Implementation

```python
# core_v2/alert/platform/windows.py
import os
import sys
import subprocess
import tempfile
from typing import Dict, Any, Optional
from core_v2.alert.platform.base import PlatformAlertInterface

class WindowsAlertPlatform(PlatformAlertInterface):
    """Windows-specific implementation of alert functionality."""
    
    def show_notification(self, title: str, message: str, level: str, options: Dict[str, Any] = None) -> bool:
        """Show a Windows notification using PowerShell."""
        options = options or {}
        
        # Get styling based on alert level
        bg_color, fg_color, sound, icon = self._get_alert_style(level)
        
        # Create PowerShell script
        script = self._create_windows_popup_script(
            title, message, options.get("app_name", "FocusGuard"),
            bg_color, fg_color, sound, icon,
            options.get("window_rect")
        )
        
        # Run the script
        return self._run_powershell_script(script)
    
    def play_sound(self, sound_type: str, options: Dict[str, Any] = None) -> bool:
        """Play a sound alert on Windows."""
        options = options or {}
        volume = options.get("volume", 0.8)
        repeat_count = options.get("repeat_count", 1)
        
        # Map sound_type to actual sound file or system sound
        sound_map = {
            "normal": "SystemAsterisk",
            "warning": "SystemExclamation",
            "critical": "SystemHand"
        }
        sound = sound_map.get(sound_type, "SystemAsterisk")
        
        try:
            # Use PowerShell to play system sounds
            script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            for ($i = 0; $i -lt {repeat_count}; $i++) {{
                [System.Media.SystemSounds]::{sound}.Play()
                if ($i -lt {repeat_count - 1}) {{ Start-Sleep -Milliseconds 500 }}
            }}
            """
            return self._run_powershell_script(script)
        except Exception:
            return False
    
    @classmethod
    def is_supported(cls) -> bool:
        """Check if Windows implementation is supported."""
        if sys.platform != "win32":
            return False
            
        try:
            # Check if PowerShell is available
            subprocess.run(
                ["powershell", "-Command", "echo 'PowerShell is available'"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
            
    # Private helper methods
    def _get_alert_style(self, level: str) -> tuple:
        """Get styling properties based on alert level."""
        styles = {
            "normal": ("#1E90FF", "white", "SystemAsterisk", "Information"),
            "warning": ("#FFA500", "black", "SystemExclamation", "Warning"),
            "critical": ("#FF0000", "white", "SystemHand", "Error")
        }
        return styles.get(level, styles["normal"])
        
    def _create_windows_popup_script(self, title, message, app_name, bg_color, fg_color, sound, icon, window_rect=None):
        """Create a PowerShell script for Windows notification."""
        # Implementation details...
        
    def _run_powershell_script(self, script: str) -> bool:
        """Run a PowerShell script and return success status."""
        # Implementation details...
```

### Alert Provider Base Class

```python
# core_v2/alert/providers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core_v2.alert.platform import get_platform_implementation

class AlertProvider(ABC):
    """Base class for all alert providers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the alert provider.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.platform = get_platform_implementation()
    
    @abstractmethod
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """Send an alert.
        
        Args:
            window_info: Information about the window causing the distraction
            message: Alert message
            level: Alert level ("normal", "warning", or "critical")
            
        Returns:
            bool: True if alert was successfully sent
        """
        pass
        
    def get_name(self) -> str:
        """Get the name of the alert provider."""
        return self.__class__.__name__
```

### Popup Alert Provider

```python
# core_v2/alert/providers/popup.py
import time
import threading
from typing import Dict, Any, Optional
from core_v2.alert.providers.base import AlertProvider

class PopupAlertProvider(AlertProvider):
    """Shows popup alerts using platform-specific methods."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        super().__init__(config)
        self.popup_duration = self.config.get("popup_duration", 10)  # seconds
        self.overlay_on_distraction = self.config.get("overlay_on_distraction", False)
        self.active_alerts = []
        self.recent_alerts = {}  # Track recent alerts to prevent duplicates
        
    def send_alert(self, window_info: Dict[str, Any], message: str, level: str = "normal") -> bool:
        """Show a popup alert."""
        if not self.enabled:
            return False
            
        app_name = window_info.get("app_name", "Unknown App")
        
        # Check for duplicate alerts
        current_time = time.time()
        alert_key = f"{app_name}-{level}"
        
        if alert_key in self.recent_alerts:
            last_alert_time = self.recent_alerts[alert_key]
            time_since_last = current_time - last_alert_time
            
            # If we've shown this exact alert recently, skip it
            if time_since_last < self.popup_duration:
                return True
        
        # Track this alert to prevent duplicates
        self.recent_alerts[alert_key] = current_time
        
        # Start popup in a separate thread to avoid blocking
        thread = threading.Thread(
            target=self._show_popup,
            args=(window_info, message, level),
            daemon=True
        )
        thread.start()
        return True
        
    def _show_popup(self, window_info: Dict[str, Any], message: str, level: str):
        """Show a popup using platform-specific methods."""
        app_name = window_info.get("app_name", "Unknown App")
        title = f"FocusGuard Alert - {level.capitalize()}"
        
        # Create options dictionary for platform implementation
        options = {
            "app_name": app_name,
            "duration": self.popup_duration
        }
        
        # Add window position if overlay_on_distraction is enabled
        if self.overlay_on_distraction and "rect" in window_info:
            options["window_rect"] = window_info["rect"]
            
        # Track this alert
        alert_id = f"{app_name}-{time.time()}"
        self.active_alerts.append(alert_id)
        
        # Show notification using platform implementation
        try:
            self.platform.show_notification(title, message, level, options)
        except Exception:
            pass
            
        # Remove from active alerts after duration
        if self.popup_duration > 0:
            time.sleep(self.popup_duration)
            if alert_id in self.active_alerts:
                self.active_alerts.remove(alert_id)
```

### Alert System Class

```python
# core_v2/alert/alert_system.py
from typing import Dict, Any, List, Optional
import time
from datetime import datetime, timedelta
from core_v2.alert.providers.base import AlertProvider
from core_v2.alert.providers.popup import PopupAlertProvider
from core_v2.alert.providers.sound import SoundAlertProvider
from core_v2.alert.providers.desktop_notification import DesktopNotificationProvider
from core_v2.alert.utils.history import AlertHistoryManager

class AlertSystem:
    """
    Main alert system that manages multiple alert providers and escalation strategies.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        providers: Optional[List[AlertProvider]] = None
    ):
        """Initialize the alert system."""
        self.config = config or {}
        self.providers = providers or []
        self.escalation_levels = ["normal", "warning", "critical"]
        self.cooldown_period = self.config.get("cooldown_period", 60)  # seconds
        self.escalation_threshold = self.config.get("escalation_threshold", 3)
        self.escalation_window = self.config.get("escalation_window", 300)  # seconds
        
        # Initialize history manager
        self.history_manager = AlertHistoryManager(self.config.get("history_file"))
        
        # Initialize default providers if none provided
        if not self.providers:
            self._init_default_providers()
            
    def _init_default_providers(self):
        """Initialize default alert providers."""
        self.providers = [
            DesktopNotificationProvider(self.config.get("desktop_notification", {})),
            SoundAlertProvider(self.config.get("sound_alert", {}))
        ]
        
        # Add popup provider
        popup_config = self.config.get("popup_alert", {})
        if popup_config.get("enabled", True):
            self.providers.append(PopupAlertProvider(popup_config))
            
        # Add other providers based on configuration
        # ...
    
    def alert(self, window_info: Dict[str, Any], message: str) -> bool:
        """Send an alert through all enabled providers with automatic escalation."""
        # Skip if we're in cooldown for this app
        app_name = window_info.get("app_name", "Unknown App")
        if self._is_in_cooldown(app_name):
            return False
            
        # Determine alert level based on history
        level = self._determine_alert_level(app_name)
        
        # Track this alert in history
        self._track_alert(app_name)
        
        # Send alerts through all providers
        success = False
        for provider in self.providers:
            if provider.send_alert(window_info, message, level):
                success = True
                
        return success
    
    # Other methods for alert history, escalation, etc.
    # ...
```

## Testing Strategy

### Unit Tests

1. **Platform Interface Tests**
   - Test the platform interface with mock implementations
   - Verify correct platform selection based on the current OS

2. **Provider Tests**
   - Test each provider in isolation with mock platform implementations
   - Verify provider configuration and behavior

3. **Alert System Tests**
   - Test alert system with mock providers
   - Verify escalation logic, cooldown periods, and history tracking

### Integration Tests

1. **Provider-Platform Integration**
   - Test providers with actual platform implementations
   - Verify correct interaction between providers and platforms

2. **End-to-End Tests**
   - Test the complete alert system with real providers and platforms
   - Verify alerts are displayed correctly on the current platform

### Platform-Specific Tests

1. **Windows Tests**
   - Test Windows-specific notification methods
   - Verify PowerShell script generation and execution

2. **macOS Tests**
   - Test AppleScript-based notifications
   - Verify sound playback on macOS

3. **Linux Tests**
   - Test Linux notification systems
   - Verify sound playback on Linux

## Implementation Timeline

### Week 1: Foundation and Core Components

1. **Days 1-2: Core Structure**
   - Create directory structure
   - Implement data models
   - Set up platform interface and factory

2. **Days 3-4: Windows Platform Implementation**
   - Implement Windows-specific notification methods
   - Port existing PowerShell-based code
   - Implement Windows sound playback

3. **Days 5-7: Provider Base Classes**
   - Implement AlertProvider base class
   - Create basic provider implementations
   - Set up testing infrastructure

### Week 2: Provider Implementations and Integration

1. **Days 8-9: Complete Provider Implementations**
   - Implement all alert providers
   - Port existing provider logic
   - Ensure platform independence

2. **Days 10-11: Alert System Core**
   - Implement AlertSystem class
   - Port alert history and escalation logic
   - Implement configuration management

3. **Days 12-14: Testing and Refinement**
   - Write comprehensive tests
   - Fix bugs and edge cases
   - Optimize performance

### Week 3: Platform Extensions and Documentation

1. **Days 15-16: Other Platform Implementations**
   - Implement macOS and Linux support
   - Create stub implementations for mobile platforms
   - Test cross-platform functionality

2. **Days 17-18: Documentation and Examples**
   - Create detailed documentation
   - Write usage examples
   - Document extension points

3. **Days 19-21: Final Integration and Migration**
   - Integrate with other core_v2 components
   - Set up migration path from legacy code
   - Final testing and refinement

## Migration Strategy

1. **Parallel Implementation**
   - Implement the new alert system in core_v2 while keeping the original in core
   - Ensure all functionality is preserved in the new implementation

2. **Gradual Adoption**
   - Start using the new alert system in new features
   - Gradually migrate existing code to use the new system

3. **Deprecation Plan**
   - Mark the original alert system as deprecated
   - Provide migration guides for dependent code
   - Set a timeline for complete migration

4. **Testing and Verification**
   - Ensure the new implementation passes all existing tests
   - Create new tests specific to the new architecture
   - Verify cross-platform functionality

## Platform Extension Guide

To add support for a new platform in the future, follow these steps:

1. **Create a new implementation file**:
   ```
   core_v2/alert/platform/new_platform.py
   ```

2. **Implement the PlatformAlertInterface**:
   ```python
   from core_v2.alert.platform.base import PlatformAlertInterface
   
   class NewPlatformAlertInterface(PlatformAlertInterface):
       def show_notification(self, title, message, level, options=None):
           # Implementation
           pass
           
       def play_sound(self, sound_type, options=None):
           # Implementation
           pass
           
       @classmethod
       def is_supported(cls):
           # Check if this platform is supported
           return True  # If all requirements are met
   ```

3. **Add platform detection to the factory**:
   ```python
   # In core_v2/alert/platform/__init__.py
   try:
       from core_v2.alert.platform.new_platform import NewPlatformAlertInterface
       implementations.append(NewPlatformAlertInterface)
   except ImportError:
       pass
   ```

4. **Create platform-specific tests**:
   ```
   tests/core_v2/alert/platform/test_new_platform.py
   ```

5. **Document platform-specific requirements**:
   - Required dependencies
   - System permissions
   - API limitations
   - Platform-specific behaviors

## Conclusion

This refactoring plan provides a comprehensive approach to integrating the alert system with the core_v2 architecture, with a focus on Windows for the initial implementation but designed for extensibility to other platforms in the future. By following this plan, we will create a more modular, maintainable, and extensible alert system that can be easily extended to support additional platforms with minimal refactoring.
