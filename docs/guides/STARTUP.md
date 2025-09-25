# Focus Guard Application Startup Guide

This document outlines the correct procedure for starting the Focus Guard application, based on the working coordinator and component implementation.

## Prerequisites

- Python 3.8 or higher
- Dependencies installed: `pip install -e .[dev]`
- Configuration files in place (see Configuration section below)

## Basic Startup

### 1. Import Required Components

```python
from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from focus_guard.core.coordinator.events import DefaultEventBus
from focus_guard.core.coordinator.components.config import ConfigComponent
from focus_guard.core.coordinator.components.activity import ActivityMonitorComponent
from focus_guard.core.coordinator.components.browser import BrowserIntegrationComponent
from focus_guard.core.coordinator.components.classification import ClassificationComponent
from focus_guard.core.coordinator.components.distraction import DistractionDetectorComponent
from focus_guard.core.coordinator.components.alert import AlertSystemComponent
from focus_guard.core.coordinator.components.api import ApiServerComponent
```

### 2. Initialize Core Components

```python
# Create event bus for inter-component communication
event_bus = DefaultEventBus()

# Create configuration manager (simplified example)
config_manager = create_config_manager()  # Implement this based on your configuration system

# Initialize the coordinator
coordinator = FocusGuardCoordinator(
    name="FocusGuard",
    event_bus=event_bus,
    config_manager=config_manager
)

# Register core components
components = [
    ConfigComponent("config", event_bus, config_manager),
    ActivityMonitorComponent("activity", event_bus, config_manager),
    BrowserIntegrationComponent("browser", event_bus, config_manager),
    ClassificationComponent("classification", event_bus, config_manager),
    DistractionDetectorComponent("distraction", event_bus, config_manager),
    AlertSystemComponent("alert", event_bus, config_manager),
    ApiServerComponent("api", event_bus, config_manager)
]

for component in components:
    coordinator.register_component(component)
```

### 3. Start the Application

```python
import asyncio

async def main():
    # Initialize all components
    if not await coordinator.initialize():
        print("Failed to initialize components")
        return
    
    # Start all components
    if not await coordinator.start():
        print("Failed to start components")
        return
    
    print("Focus Guard is running. Press Ctrl+C to exit.")
    
    try:
        # Keep the application running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Properly shut down all components
        await coordinator.stop()
        await coordinator.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

Create a configuration file (e.g., `config.json`) with the following structure:

```json
{
    "browser": {
        "polling_interval": 1.0,
        "browser_executables": ["chrome.exe", "msedge.exe"]
    },
    "classification": {
        "cache_ttl_seconds": 3600,
        "default_category": "neutral"
    },
    "alert": {
        "enabled": true,
        "notification_duration": 10
    },
    "api": {
        "host": "127.0.0.1",
        "port": 8000,
        "enabled": true
    }
}
```

## Component Lifecycle

1. **Initialization**: Components set up their internal state and register event handlers.
2. **Start**: Components begin their main operations (e.g., starting background tasks, opening connections).
3. **Running**: Components are fully operational and processing events.
4. **Stop**: Components gracefully shut down operations.
5. **Shutdown**: Components release all resources.

## Event System

Components communicate through the event bus. Common events include:

- `TAB_OPENED`: When a new browser tab is detected
- `TAB_UPDATED`: When a tab's URL or title changes
- `DISTRACTION_DETECTED`: When a distracting website is detected
- `ALERT_TRIGGERED`: When an alert is shown to the user

## Troubleshooting

1. **Component Fails to Start**:
   - Check the component's logs for errors
   - Verify all required configuration values are set
   - Ensure all dependencies are installed

2. **Events Not Being Processed**:
   - Verify event subscriptions in the component's `_initialize_component` method
   - Check if the component is in the correct state (initialized and started)
   - Ensure the event type matches between publisher and subscriber

3. **Configuration Issues**:
   - Validate the configuration file against the expected schema
   - Check for missing or invalid values
   - Verify file permissions

## Next Steps

- Implement proper logging
- Add health check endpoints
- Set up monitoring and metrics collection
- Implement configuration hot-reloading
