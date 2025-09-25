# Coordinator Module

The coordinator module serves as the central orchestrator for the Focus Guard application, managing all components, their lifecycles, and inter-component communication.

## Overview

This module implements the main coordination layer that:
- **Manages Component Lifecycle**: Initializes, starts, stops, and shuts down all application components
- **Handles Communication**: Provides event-based communication between components
- **Monitors Health**: Tracks the health and status of all managed components
- **Coordinates Dependencies**: Manages component dependencies and startup order
- **Provides Central Control**: Offers a single point of control for the entire application

## Key Components

### FocusGuardCoordinator
The main coordinator class that orchestrates all application components:
- **Component Management**: Creates and manages all Focus Guard components
- **Lifecycle Management**: Handles initialization, startup, shutdown sequences
- **Event Coordination**: Manages inter-component communication via event bus
- **Health Monitoring**: Provides health checks and status reporting
- **Configuration Integration**: Coordinates configuration across all components

### Component Architecture
- **Activity Monitor**: Tracks user activity and system state
- **Browser Integration**: Manages browser tab monitoring and communication
- **Distraction Detector**: Identifies and handles distraction events
- **Domain Classifier**: Categorizes domains for blocking decisions
- **Alert System**: Manages user notifications and alerts
- **API Server**: Provides external API access to Focus Guard functionality

## Component Lifecycle

### Initialization Phase
1. **Component Registration**: All components are registered with lifecycle manager
2. **Dependency Resolution**: Component dependencies are resolved and ordered
3. **Configuration Loading**: Each component receives appropriate configuration
4. **Resource Allocation**: Necessary resources are allocated for each component
5. **Health Verification**: Component health is verified before proceeding

### Startup Phase
1. **Sequential Startup**: Components start in dependency order
2. **Event Bus Setup**: Communication channels are established
3. **Health Checks**: Continuous monitoring begins
4. **State Synchronization**: Components synchronize their initial state
5. **Operational Readiness**: System becomes fully operational

### Shutdown Phase
1. **Graceful Degradation**: Components begin shutdown procedures
2. **Resource Cleanup**: Resources are properly released
3. **State Persistence**: Important state is saved
4. **Communication Termination**: Event channels are closed
5. **Final Cleanup**: All resources are fully released

## Event System

### Event Types
- **Component Events**: Lifecycle events (started, stopped, failed)
- **Distraction Events**: User distraction detection events
- **Browser Events**: Tab open/close/update events
- **Configuration Events**: Configuration change notifications
- **Health Events**: Component health status changes

### Event Flow
```
Component → Event Bus → Interested Components
```

## Usage

### Basic Usage
```python
from focus_guard.core.coordinator.focus_guard_coordinator import FocusGuardCoordinator
from focus_guard.core.config.interfaces import ConfigurationManager

# Create coordinator with configuration manager
config_manager = ConfigurationManager()
coordinator = FocusGuardCoordinator(config_manager)

# Initialize the system
success = await coordinator.initialize()
if success:
    print("Focus Guard initialized successfully")

# Start the system
success = await coordinator.start()
if success:
    print("Focus Guard is now running")

# Check system health
if coordinator.is_healthy():
    print("All components are healthy")

# Get system status
status = coordinator.get_status()
print(f"System status: {status}")

# Stop the system
await coordinator.stop()

# Shutdown completely
await coordinator.shutdown()
```

### Component Access
```python
# Get specific components
activity_component = coordinator.get_component("activity")
browser_component = coordinator.get_component("browser")
classifier_component = coordinator.get_component("classification")

# Check component health
if activity_component and activity_component.is_healthy():
    print("Activity monitor is healthy")
```

## Architecture

### Centralized Management
- **Single Coordinator**: One coordinator manages all components
- **Unified Interface**: Consistent API across all component interactions
- **Centralized Configuration**: All components share configuration state
- **Unified Health Monitoring**: Single health check interface

### Event-Driven Communication
- **Asynchronous Events**: Non-blocking event handling
- **Loose Coupling**: Components communicate via events, not direct calls
- **Scalable Architecture**: Easy to add new components
- **Fault Isolation**: Component failures don't cascade

### Dependency Management
- **Explicit Dependencies**: Components declare their dependencies
- **Ordered Startup**: Dependencies ensure correct startup sequence
- **Circular Dependency Detection**: Prevents deadlock situations
- **Graceful Degradation**: System continues operating with failed components

## Integration Points

- **Configuration**: Integrates with core.config for settings management
- **Events**: Uses core.coordinator.events for event handling
- **Lifecycle**: Leverages core.coordinator.lifecycle for component management
- **Interfaces**: Implements core.coordinator.interfaces for component contracts
- **Components**: Manages components from various core modules (activity, browser, etc.)

## File Structure

- `focus_guard_coordinator.py`: Main coordinator implementation
- `interfaces.py`: Component and coordinator interface definitions
- `lifecycle.py`: Component lifecycle management
- `events.py`: Event system implementation
- `components/`: Factory functions for creating individual components

## Error Handling

- **Graceful Degradation**: System continues operating with failed components
- **Health Monitoring**: Continuous health checks detect issues early
- **Eventual Consistency**: System state eventually becomes consistent
- **Recovery Mechanisms**: Automatic recovery from transient failures
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
