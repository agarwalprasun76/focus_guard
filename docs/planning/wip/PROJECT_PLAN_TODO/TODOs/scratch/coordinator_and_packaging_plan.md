# Focus Guard Coordinator and Packaging Plan

## Overview

This document outlines the plan for developing a comprehensive coordinator module that integrates all components of the Focus Guard application, along with a strategy for packaging the application into a distributable executable.

The coordinator will serve as the central orchestration point for the application, managing the lifecycle of all components, handling inter-component communication, and providing a unified interface for the UI layer. It represents the final step in the core_v2 refactoring effort, bringing together all the modular components into a cohesive application.

## Coordinator Architecture

### Core Principles

1. **Modular Design**: Each component should be loosely coupled and independently testable
2. **Dependency Injection**: Components should receive their dependencies through constructor parameters
3. **Interface-Based Communication**: Components should communicate through well-defined interfaces
4. **Configuration-Driven**: Component behavior should be configurable through the central configuration system
5. **Lifecycle Management**: The coordinator should manage the startup, shutdown, and health of all components
6. **Extensibility**: The system should be easily extensible with new components and features

### Directory Structure

```
core_v2/
├── coordinator/
│   ├── __init__.py
│   ├── focus_guard_coordinator.py    # Main coordinator implementation
│   ├── interfaces.py                 # Core interfaces for component integration
│   ├── lifecycle.py                  # Component lifecycle management
│   ├── health.py                     # Health monitoring and reporting
│   └── metrics.py                    # Performance metrics collection
```

### Component Integration Model

The coordinator will use a component-based architecture where each major subsystem is represented as a component with a well-defined lifecycle and interface:

```python
class Component(ABC):
    """Base interface for all coordinator-managed components."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the component name."""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the component. Return True if successful."""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """Start the component. Return True if successful."""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the component. Return True if successful."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Shutdown the component. Return True if successful."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get the component status."""
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if the component is healthy."""
        pass
```

### Main Coordinator Implementation

```python
class FocusGuardCoordinator:
    """
    Main coordinator for the Focus Guard application.
    
    Responsibilities:
    1. Initialize and manage all components
    2. Handle inter-component communication
    3. Manage component lifecycle
    4. Monitor component health
    5. Collect and report metrics
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        """Initialize the coordinator with a configuration manager."""
        self.config_manager = config_manager
        self.components: Dict[str, Component] = {}
        self.running = False
        self.logger = logging.getLogger("focus_guard.coordinator")
        
    async def initialize(self) -> bool:
        """Initialize the coordinator and all components."""
        # Create and register all components
        await self._register_components()
        
        # Initialize all components
        for name, component in self.components.items():
            try:
                success = await component.initialize()
                if not success:
                    self.logger.error(f"Failed to initialize component: {name}")
                    return False
            except Exception as e:
                self.logger.exception(f"Error initializing component {name}: {e}")
                return False
                
        return True
    
    async def start(self) -> bool:
        """Start the coordinator and all components."""
        if self.running:
            self.logger.warning("Coordinator is already running")
            return True
            
        # Start all components in the correct order
        for name, component in self._get_ordered_components():
            try:
                success = await component.start()
                if not success:
                    self.logger.error(f"Failed to start component: {name}")
                    await self._stop_started_components()
                    return False
            except Exception as e:
                self.logger.exception(f"Error starting component {name}: {e}")
                await self._stop_started_components()
                return False
                
        self.running = True
        return True
    
    async def stop(self) -> bool:
        """Stop the coordinator and all components."""
        if not self.running:
            self.logger.warning("Coordinator is not running")
            return True
            
        # Stop all components in reverse order
        success = await self._stop_started_components()
        self.running = False
        return success
    
    async def shutdown(self) -> bool:
        """Shutdown the coordinator and all components."""
        if self.running:
            await self.stop()
            
        # Shutdown all components
        for name, component in reversed(list(self.components.items())):
            try:
                await component.shutdown()
            except Exception as e:
                self.logger.exception(f"Error shutting down component {name}: {e}")
                
        self.components.clear()
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the coordinator and all components."""
        status = {
            "coordinator_running": self.running,
            "components": {}
        }
        
        for name, component in self.components.items():
            try:
                component_status = component.get_status()
                status["components"][name] = component_status
            except Exception as e:
                self.logger.exception(f"Error getting status for component {name}: {e}")
                status["components"][name] = {"error": str(e)}
                
        return status
    
    def is_healthy(self) -> bool:
        """Check if the coordinator and all components are healthy."""
        if not self.running:
            return False
            
        for name, component in self.components.items():
            try:
                if not component.is_healthy():
                    self.logger.warning(f"Component {name} is not healthy")
                    return False
            except Exception as e:
                self.logger.exception(f"Error checking health for component {name}: {e}")
                return False
                
        return True
    
    async def _register_components(self):
        """Create and register all components."""
        # Configuration component (always first)
        self.components["config"] = ConfigComponent(self.config_manager)
        
        # Activity monitoring
        activity_monitor = await self._create_activity_monitor()
        self.components["activity_monitor"] = activity_monitor
        
        # Browser detection and integration
        browser_integration = await self._create_browser_integration()
        self.components["browser_integration"] = browser_integration
        
        # Domain classification
        domain_classifier = await self._create_domain_classifier()
        self.components["domain_classifier"] = domain_classifier
        
        # Distraction detection
        distraction_detector = await self._create_distraction_detector(
            activity_monitor, 
            browser_integration,
            domain_classifier
        )
        self.components["distraction_detector"] = distraction_detector
        
        # Alert system
        alert_system = await self._create_alert_system()
        self.components["alert_system"] = alert_system
        
        # API server (if enabled)
        if self.config_manager.get("api_server.enabled", False):
            api_server = await self._create_api_server()
            self.components["api_server"] = api_server
    
    async def _create_activity_monitor(self) -> Component:
        """Create and configure the activity monitor component."""
        from core_v2.activity.monitor import ActivityMonitor
        from core_v2.activity.platform import get_platform_implementation
        
        platform_impl = get_platform_implementation()
        activity_monitor = ActivityMonitor(platform_impl)
        
        return ActivityMonitorComponent(activity_monitor)
    
    async def _create_browser_integration(self) -> Component:
        """Create and configure the browser integration component."""
        from core_v2.browser.integration import BrowserIntegration
        from core_v2.browser.tab_server import TabServer
        
        tab_server = TabServer()
        browser_integration = BrowserIntegration(tab_server)
        
        return BrowserIntegrationComponent(browser_integration, tab_server)
    
    async def _create_domain_classifier(self) -> Component:
        """Create and configure the domain classifier component."""
        from core_v2.classification.domain_classifier import StandardDomainClassifier
        
        domain_classifier = StandardDomainClassifier()
        
        return DomainClassifierComponent(domain_classifier)
    
    async def _create_distraction_detector(
        self,
        activity_monitor_component,
        browser_integration_component,
        domain_classifier_component
    ) -> Component:
        """Create and configure the distraction detector component."""
        from core_v2.distraction.detector import DistractionDetector
        
        detector = DistractionDetector(
            activity_monitor=activity_monitor_component.activity_monitor,
            browser_integration=browser_integration_component.browser_integration,
            domain_classifier=domain_classifier_component.domain_classifier
        )
        
        return DistractionDetectorComponent(detector)
    
    async def _create_alert_system(self) -> Component:
        """Create and configure the alert system component."""
        from core_v2.alert.system import AlertSystem
        from core_v2.alert.platform import get_platform_implementation
        
        platform_impl = get_platform_implementation()
        alert_system = AlertSystem(platform_impl)
        
        return AlertSystemComponent(alert_system)
    
    async def _create_api_server(self) -> Component:
        """Create and configure the API server component."""
        from core_v2.api.server import ApiServer
        
        api_server = ApiServer()
        
        return ApiServerComponent(api_server)
    
    def _get_ordered_components(self) -> List[Tuple[str, Component]]:
        """Get components in the order they should be started."""
        # Define the startup order
        order = [
            "config",
            "activity_monitor",
            "browser_integration",
            "domain_classifier",
            "distraction_detector",
            "alert_system",
            "api_server"  # Optional component
        ]
        
        # Return components in the correct order (if they exist)
        ordered_components = []
        for name in order:
            if name in self.components:
                ordered_components.append((name, self.components[name]))
                
        return ordered_components
    
    async def _stop_started_components(self) -> bool:
        """Stop all started components in reverse order."""
        ordered_components = self._get_ordered_components()
        success = True
        
        # Stop in reverse order
        for name, component in reversed(ordered_components):
            try:
                component_success = await component.stop()
                if not component_success:
                    self.logger.error(f"Failed to stop component: {name}")
                    success = False
            except Exception as e:
                self.logger.exception(f"Error stopping component {name}: {e}")
                success = False
                
        return success
```

## Component Implementations

Each major subsystem will be wrapped in a component implementation that adheres to the Component interface:

### Activity Monitor Component

```python
class ActivityMonitorComponent(Component):
    """Component wrapper for the activity monitor."""
    
    def __init__(self, activity_monitor):
        self.activity_monitor = activity_monitor
        self._running = False
        
    @property
    def name(self) -> str:
        return "activity_monitor"
    
    async def initialize(self) -> bool:
        """Initialize the activity monitor."""
        return True
    
    async def start(self) -> bool:
        """Start the activity monitor."""
        self.activity_monitor.start()
        self._running = True
        return True
    
    async def stop(self) -> bool:
        """Stop the activity monitor."""
        self.activity_monitor.stop()
        self._running = False
        return True
    
    async def shutdown(self) -> bool:
        """Shutdown the activity monitor."""
        if self._running:
            await self.stop()
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get the activity monitor status."""
        return {
            "running": self._running,
            "active_window": self.activity_monitor.get_active_window() if self._running else None
        }
    
    def is_healthy(self) -> bool:
        """Check if the activity monitor is healthy."""
        return self._running
```

Similar component wrappers will be implemented for each major subsystem.

## Inter-Component Communication

Components will communicate through several mechanisms:

1. **Direct Method Calls**: For synchronous operations where one component directly depends on another
2. **Event System**: For asynchronous notifications between components
3. **Shared State**: For data that needs to be accessed by multiple components

### Event System

```python
class EventType(Enum):
    """Types of events that can be published."""
    DISTRACTION_DETECTED = "distraction_detected"
    DISTRACTION_RESOLVED = "distraction_resolved"
    BROWSER_TAB_OPENED = "browser_tab_opened"
    BROWSER_TAB_CLOSED = "browser_tab_closed"
    ACTIVITY_CHANGED = "activity_changed"
    CONFIG_CHANGED = "config_changed"
    # ... other event types

class Event:
    """Event data container."""
    
    def __init__(self, event_type: EventType, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.datetime.now()

class EventListener(ABC):
    """Interface for event listeners."""
    
    @abstractmethod
    async def on_event(self, event: Event):
        """Handle an event."""
        pass

class EventBus:
    """Central event bus for inter-component communication."""
    
    def __init__(self):
        self.listeners: Dict[EventType, List[EventListener]] = {}
        
    def subscribe(self, event_type: EventType, listener: EventListener):
        """Subscribe a listener to an event type."""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)
        
    def unsubscribe(self, event_type: EventType, listener: EventListener):
        """Unsubscribe a listener from an event type."""
        if event_type in self.listeners and listener in self.listeners[event_type]:
            self.listeners[event_type].remove(listener)
            
    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        if event.event_type not in self.listeners:
            return
            
        for listener in self.listeners[event.event_type]:
            try:
                await listener.on_event(event)
            except Exception as e:
                logging.exception(f"Error in event listener: {e}")
```

## Application Packaging

### Packaging Strategy

The Focus Guard application will be packaged as a standalone executable using PyInstaller, which offers several advantages:

1. **Single-File Executable**: Creates a single .exe file that includes all dependencies
2. **Cross-Platform Support**: Can create executables for Windows, macOS, and Linux
3. **Hidden Console**: Can hide the console window for a better user experience
4. **Resource Bundling**: Can bundle resources like icons, sounds, and configuration files

### Packaging Considerations

1. **Dependencies Management**:
   - Ensure all dependencies are properly specified in requirements.txt with version pinning
   - Handle platform-specific dependencies using conditional imports
   - Test with a clean virtual environment to catch missing dependencies

2. **Configuration Handling**:
   - Determine where user configuration will be stored (e.g., user's home directory)
   - Include default configuration templates in the package
   - Implement first-run initialization for configuration

3. **Resource Management**:
   - Bundle all necessary resources (icons, sounds, etc.) with the application
   - Use relative paths for accessing resources within the package
   - Implement proper resource extraction for temporary files if needed

4. **Auto-Update Mechanism**:
   - Consider implementing an auto-update mechanism
   - Store version information in a consistent location
   - Provide update notifications to users

### Directory Structure for Packaging

```
packaging/
├── build_app.py           # Script to build the executable
├── focus_guard.spec       # PyInstaller spec file
├── hooks/                 # Custom PyInstaller hooks
│   └── hook-focus_guard.py
├── resources/             # Application resources
│   ├── icons/
│   │   └── focus_guard.ico
│   └── sounds/
│       └── alert.wav
└── installer/             # Installer configuration
    ├── focus_guard.nsi    # NSIS installer script (Windows)
    └── dmg_config.json    # DMG configuration (macOS)
```

### PyInstaller Configuration

The PyInstaller spec file will be configured to:

1. Include all necessary dependencies
2. Bundle application resources
3. Set the application icon
4. Hide the console window
5. Create a single-file executable

```python
# focus_guard.spec
block_cipher = None

a = Analysis(
    ['../core_v2/main.py'],
    pathex=['../'],
    binaries=[],
    datas=[
        ('../resources', 'resources'),
        ('../core_v2/config/templates', 'config/templates')
    ],
    hiddenimports=[
        'core_v2.activity.platform.windows',
        'core_v2.activity.platform.macos',
        'core_v2.activity.platform.linux',
        'core_v2.alert.platform.windows',
        'core_v2.alert.platform.macos',
        'core_v2.alert.platform.linux'
    ],
    hookspath=['hooks'],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    a.pure, 
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FocusGuard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='resources/icons/focus_guard.ico'
)
```

### Build Script

A Python script will automate the build process:

```python
#!/usr/bin/env python
"""
Build script for Focus Guard application.

This script builds the Focus Guard application using PyInstaller.
"""

import os
import sys
import shutil
import subprocess
import platform

def main():
    """Main build function."""
    # Determine the platform
    system = platform.system().lower()
    
    # Clean the build directory
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Run PyInstaller
    subprocess.run([
        'pyinstaller',
        '--clean',
        'focus_guard.spec'
    ], check=True)
    
    # Create installer (Windows)
    if system == 'windows':
        create_windows_installer()
    
    # Create DMG (macOS)
    elif system == 'darwin':
        create_macos_dmg()
    
    # Create AppImage (Linux)
    elif system == 'linux':
        create_linux_appimage()
    
    print("Build completed successfully!")

def create_windows_installer():
    """Create a Windows installer using NSIS."""
    # Check if NSIS is installed
    makensis_path = shutil.which('makensis')
    if not makensis_path:
        print("NSIS not found. Skipping installer creation.")
        return
    
    # Run NSIS
    subprocess.run([
        makensis_path,
        'installer/focus_guard.nsi'
    ], check=True)
    
    print("Windows installer created successfully!")

def create_macos_dmg():
    """Create a macOS DMG."""
    # Check if create-dmg is installed
    create_dmg_path = shutil.which('create-dmg')
    if not create_dmg_path:
        print("create-dmg not found. Skipping DMG creation.")
        return
    
    # Run create-dmg
    subprocess.run([
        create_dmg_path,
        '--volname', 'FocusGuard',
        '--volicon', 'resources/icons/focus_guard.icns',
        '--window-pos', '200', '120',
        '--window-size', '800', '400',
        '--icon-size', '100',
        '--icon', 'FocusGuard.app', '200', '190',
        '--hide-extension', 'FocusGuard.app',
        '--app-drop-link', '600', '190',
        'dist/FocusGuard.dmg',
        'dist/FocusGuard.app'
    ], check=True)
    
    print("macOS DMG created successfully!")

def create_linux_appimage():
    """Create a Linux AppImage."""
    # Check if appimagetool is installed
    appimagetool_path = shutil.which('appimagetool')
    if not appimagetool_path:
        print("appimagetool not found. Skipping AppImage creation.")
        return
    
    # Create AppDir structure
    appdir = 'dist/FocusGuard.AppDir'
    os.makedirs(f'{appdir}/usr/bin', exist_ok=True)
    os.makedirs(f'{appdir}/usr/share/applications', exist_ok=True)
    os.makedirs(f'{appdir}/usr/share/icons/hicolor/256x256/apps', exist_ok=True)
    
    # Copy executable
    shutil.copy('dist/FocusGuard', f'{appdir}/usr/bin/')
    
    # Create desktop file
    with open(f'{appdir}/usr/share/applications/focus_guard.desktop', 'w') as f:
        f.write("""[Desktop Entry]
Type=Application
Name=FocusGuard
Comment=Focus Guard Productivity Tool
Exec=FocusGuard
Icon=focus_guard
Categories=Utility;
""")
    
    # Copy icon
    shutil.copy('resources/icons/focus_guard.png', 
                f'{appdir}/usr/share/icons/hicolor/256x256/apps/focus_guard.png')
    
    # Create AppRun
    with open(f'{appdir}/AppRun', 'w') as f:
        f.write("""#!/bin/sh
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/FocusGuard" "$@"
""")
    os.chmod(f'{appdir}/AppRun', 0o755)
    
    # Run appimagetool
    subprocess.run([
        appimagetool_path,
        appdir,
        'dist/FocusGuard.AppImage'
    ], check=True)
    
    print("Linux AppImage created successfully!")

if __name__ == "__main__":
    main()
```

### Installer Configuration

#### Windows (NSIS)

```nsi
; focus_guard.nsi
!include "MUI2.nsh"

; General
Name "Focus Guard"
OutFile "FocusGuard-Setup.exe"
InstallDir "$PROGRAMFILES\Focus Guard"
InstallDirRegKey HKCU "Software\Focus Guard" ""

; Interface settings
!define MUI_ABORTWARNING
!define MUI_ICON "resources\icons\focus_guard.ico"
!define MUI_UNICON "resources\icons\focus_guard.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer sections
Section "Focus Guard" SecMain
  SetOutPath "$INSTDIR"
  
  ; Files
  File "dist\FocusGuard.exe"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  ; Start Menu
  CreateDirectory "$SMPROGRAMS\Focus Guard"
  CreateShortcut "$SMPROGRAMS\Focus Guard\Focus Guard.lnk" "$INSTDIR\FocusGuard.exe"
  CreateShortcut "$SMPROGRAMS\Focus Guard\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  
  ; Registry
  WriteRegStr HKCU "Software\Focus Guard" "" $INSTDIR
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Focus Guard" "DisplayName" "Focus Guard"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Focus Guard" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Focus Guard" "DisplayIcon" "$INSTDIR\FocusGuard.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Focus Guard" "Publisher" "Focus Guard Team"
  
  ; Autostart (optional)
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Focus Guard" "$INSTDIR\FocusGuard.exe"
SectionEnd

; Uninstaller section
Section "Uninstall"
  ; Remove files
  Delete "$INSTDIR\FocusGuard.exe"
  Delete "$INSTDIR\Uninstall.exe"
  
  ; Remove directories
  RMDir "$INSTDIR"
  
  ; Remove Start Menu items
  Delete "$SMPROGRAMS\Focus Guard\Focus Guard.lnk"
  Delete "$SMPROGRAMS\Focus Guard\Uninstall.lnk"
  RMDir "$SMPROGRAMS\Focus Guard"
  
  ; Remove registry keys
  DeleteRegKey HKCU "Software\Focus Guard"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Focus Guard"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Focus Guard"
SectionEnd
```

## Implementation Plan

### Phase 1: Core Coordinator Implementation (Days 1-5)

1. Create the basic coordinator structure
   - Implement `Component` interface
   - Create `FocusGuardCoordinator` class
   - Implement lifecycle methods (initialize, start, stop, shutdown)
   - Add status and health monitoring

2. Implement the component interface and lifecycle management
   - Create base component implementations
   - Implement dependency resolution
   - Add startup/shutdown ordering
   - Implement error handling and recovery

3. Create the event system for inter-component communication
   - Implement `EventBus` class
   - Define core event types
   - Create subscription mechanism
   - Add async event handling

4. Implement configuration component integration
   - Create configuration component
   - Implement configuration change events
   - Add configuration validation
   - Create configuration migration utilities

### Phase 2: Component Integration (Days 6-15)

1. Integrate activity monitor component
   - Create `ActivityMonitorComponent` wrapper
   - Implement platform-specific initialization
   - Add activity event publishing
   - Implement window tracking

2. Integrate browser integration component
   - Create `BrowserIntegrationComponent` wrapper
   - Implement tab server management
   - Add extension verification
   - Implement tab event publishing

3. Integrate domain classifier component
   - Create `DomainClassifierComponent` wrapper
   - Implement classification caching
   - Add domain rule management
   - Implement classification event publishing

4. Integrate distraction detector component
   - Create `DistractionDetectorComponent` wrapper
   - Implement rule evaluation scheduling
   - Add distraction event publishing
   - Implement distraction state management

5. Integrate alert system component
   - Create `AlertSystemComponent` wrapper
   - Implement alert provider management
   - Add alert history tracking
   - Implement alert event publishing

6. Implement health monitoring and metrics collection
   - Create health check system
   - Implement performance metrics collection
   - Add diagnostic logging
   - Create status reporting API

### Phase 3: Packaging and Distribution (Days 16-20)

1. Set up PyInstaller configuration
   - Create spec file with proper imports
   - Configure resource bundling
   - Set up platform-specific options
   - Implement hidden imports handling

2. Create build scripts for all platforms
   - Implement Windows build script
   - Create macOS build script
   - Set up Linux build script
   - Add CI/CD integration

3. Implement installer configurations
   - Create NSIS script for Windows
   - Set up DMG configuration for macOS
   - Implement AppImage for Linux
   - Add installation verification

4. Test packaging and installation on all platforms
   - Create test matrix for OS versions
   - Implement automated testing
   - Add installation validation
   - Create uninstallation tests

5. Create documentation for packaging and distribution
   - Write developer documentation
   - Create user installation guide
   - Document troubleshooting steps
   - Add release process documentation

## Testing Strategy

### 1. Unit Tests

- **Component Tests**: Test individual component implementations
  - Verify lifecycle methods (initialize, start, stop, shutdown)
  - Test error handling and recovery
  - Validate status reporting

- **Event System Tests**: Test the event bus implementation
  - Verify event subscription and unsubscription
  - Test event publishing and delivery
  - Validate async event handling

- **Configuration Tests**: Test configuration integration
  - Verify configuration loading and validation
  - Test configuration change events
  - Validate configuration migration

### 2. Integration Tests

- **Component Integration Tests**: Test interactions between components
  - Verify dependency resolution
  - Test startup and shutdown ordering
  - Validate event communication

- **Mock Component Tests**: Test the coordinator with mock components
  - Create mock implementations of all components
  - Test coordinator lifecycle management
  - Validate error handling and recovery

### 3. System Tests

- **Full System Tests**: Test the complete application
  - Verify all components work together
  - Test real-world scenarios
  - Validate performance and resource usage

- **Platform-Specific Tests**: Test on different operating systems
  - Verify Windows-specific functionality
  - Test macOS-specific features
  - Validate Linux compatibility

### 4. Packaging Tests

- **Build Tests**: Test the packaging process
  - Verify PyInstaller configuration
  - Test resource bundling
  - Validate dependency inclusion

- **Installation Tests**: Test the installation process
  - Verify installer functionality
  - Test auto-start configuration
  - Validate uninstallation

- **Update Tests**: Test the update process
  - Verify version detection
  - Test update download and installation
  - Validate configuration preservation

## Problematic Areas & Improvements in Other Modules

Before finalizing the coordinator implementation, several issues in other modules should be addressed to ensure smooth integration and packaging. This section identifies potential problems and suggests improvements.

### 1. Browser Extension Integration

**Current Issues:**
- The browser extension integration relies on a complex system of tab servers and process managers that may not be properly integrated with the core_v2 architecture.
- The tab closing functionality currently uses Chrome DevTools Protocol (CDP) which causes security warnings on many websites.
- Error handling for extension installation and communication failures is limited.

**Improvements:**
- Implement tab closing functionality through the browser extension instead of CDP (as outlined in the memory about tab closing functionality).
- Enhance error handling with specific error types and recovery strategies.
- Add a health check system for extension connections with automatic reconnection attempts.
- Implement a more robust extension installation process with better user feedback.

### 2. Configuration System

**Current Issues:**
- The configuration system migration is complex and may have inconsistencies between legacy and new formats.
- Some components may still be using direct file access instead of the configuration system.

**Improvements:**
- Complete the configuration adapter layer to ensure all components use the new configuration system.
- Add validation for all configuration sections to prevent runtime errors.
- Implement a configuration migration tool to help users transition from legacy to new formats.
- Add configuration change events to notify components of relevant changes.

### 3. Activity Monitor

**Current Issues:**
- Platform-specific implementations may have inconsistencies across operating systems.
- Browser integration with the activity monitor may have race conditions or synchronization issues.

**Improvements:**
- Standardize the interface across all platform implementations.
- Add better error handling for platform-specific failures.
- Implement a caching layer to reduce platform API calls.
- Improve synchronization between browser data and window data.

### 4. Distraction Detector

**Current Issues:**
- Rule evaluation may be inefficient with redundant checks.
- Alert handling may not properly respect user preferences for notification frequency.

**Improvements:**
- Optimize rule evaluation with caching and early termination.
- Implement a more sophisticated cooldown system for alerts.
- Add user feedback mechanisms to improve rule accuracy over time.
- Enhance the rule configuration interface for better customization.

### 5. Alert System

**Current Issues:**
- Platform-specific alert implementations may have inconsistent behavior.
- Alert history management may lead to memory leaks if not properly bounded.

**Improvements:**
- Standardize alert appearance and behavior across platforms.
- Implement a proper bounded history with efficient storage.
- Add support for user acknowledgment and snoozing of alerts.
- Improve alert categorization for better filtering.

### 6. Cross-Cutting Concerns

**Current Issues:**
- Logging is inconsistent across modules.
- Error handling strategies vary between components.
- Test coverage is uneven across the codebase.

**Improvements:**
- Implement a unified logging strategy with consistent levels and formats.
- Standardize error handling with proper exception hierarchies.
- Increase test coverage, especially for integration points between components.
- Add telemetry for better understanding of user behavior and application performance.

## Implementation Roadmap

Based on the identified issues and improvements, here's a revised implementation roadmap for the coordinator and packaging:

### Phase 1: Module Improvements (Days 1-7)

1. Address critical issues in each module:
   - Implement browser extension tab closing functionality
   - Fix configuration system inconsistencies
   - Standardize platform-specific implementations
   - Optimize distraction detection rules
   - Improve alert system behavior

2. Enhance cross-cutting concerns:
   - Implement unified logging strategy
   - Standardize error handling
   - Add health check mechanisms

### Phase 2: Core Coordinator Implementation (Days 8-14)

1. Create the basic coordinator structure
2. Implement the component interface and lifecycle management
3. Create the event system for inter-component communication
4. Implement configuration component integration
5. Add health monitoring and metrics collection

### Phase 3: Component Integration (Days 15-21)

1. Integrate activity monitor component
2. Integrate browser integration component
3. Integrate domain classifier component
4. Integrate distraction detector component
5. Integrate alert system component
6. Implement comprehensive integration tests

### Phase 4: Packaging and Distribution (Days 22-28)

1. Set up PyInstaller configuration
2. Create build scripts for all platforms
3. Implement installer configurations
4. Test packaging and installation on all platforms
5. Create documentation for packaging and distribution

## Conclusion

This plan outlines a comprehensive approach to developing a modular, extensible coordinator for the Focus Guard application, along with a robust packaging strategy for distribution. By addressing the identified issues in other modules before finalizing the coordinator implementation, we can ensure a smoother integration process and a more reliable application.

The coordinator will serve as the central orchestration point for the application, managing the lifecycle of all components and providing a unified interface for the UI layer. The modular design will make it easy to add new components and features in the future, while the packaging strategy will ensure that the application can be easily distributed to users on all platforms.

By following this plan, we can successfully complete the core_v2 refactoring effort and deliver a high-quality, maintainable, and extensible Focus Guard application.
