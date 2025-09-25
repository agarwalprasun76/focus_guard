# Focus Guard Master Implementation Plan

## Project Overview

Focus Guard is a productivity application that helps users maintain focus by detecting and managing distractions. The project is undergoing a major refactoring effort to migrate from the legacy `core` module to a more modular, maintainable, and testable `core_v2` architecture.

This document outlines the recommended implementation order for the refactoring work, based on dependencies between components and the complexity of each task. Since the domain classifier refactoring is mostly complete, we'll use that as our starting point.

## Core Architecture Principles

Before diving into the implementation order, it's essential to understand the core architectural principles that should be applied across all modules:

1. **Interface-Based Design**: All components should expose well-defined interfaces that other components can depend on
2. **Dependency Injection**: Components should receive their dependencies through constructor parameters
3. **Platform Abstraction**: Platform-specific code should be isolated behind interfaces
4. **Testability**: All components should be designed for testability with clear seams for mocking
5. **Configuration-Driven**: Component behavior should be configurable through the central configuration system
6. **Event-Based Communication**: Components should communicate through events when appropriate

## Directory Structure

The new architecture follows this general directory structure:

```
core_v2/
├── activity/           # Activity monitoring components
├── alert/              # Alert system components
├── browser/            # Browser integration components
├── classification/     # Domain classification components
├── config/             # Configuration system
├── coordinator/        # Main application coordinator
├── distraction/        # Distraction detection components
├── domain/             # Domain models and utilities
└── utils/              # Shared utilities
```

## Recommended Implementation Order

### 1. Config System Migration (First Priority)

**Rationale**: The configuration system is a foundational component that almost all other modules depend on. Having a robust configuration system in place early will simplify the implementation of subsequent modules.

**Key Benefits**:
- Provides centralized configuration for all other modules
- Establishes patterns for settings validation and UI integration
- Creates a consistent approach for accessing configuration across the application

**Key Interfaces**:
- `ConfigProvider`: Interface for configuration storage providers
- `ConfigurationManager`: Main interface for accessing configuration
- `ConfigSectionSchema`: Schema definition for configuration sections

**Integration Points**:
- All other modules will depend on the configuration system
- UI components will use the configuration system for settings management

### 2. Activity Monitor Refactoring (Second Priority)

**Rationale**: The activity monitor provides core functionality for detecting user activity and is relatively self-contained with fewer dependencies on other modules.

**Key Benefits**:
- Establishes platform abstraction patterns that can be reused in other modules
- Provides essential data for the distraction detector
- Relatively independent from other modules, making it easier to implement early

**Key Interfaces**:
- `PlatformMonitorInterface`: Platform-specific monitoring implementation
- `ActivityMonitor`: Main interface for activity monitoring
- `WindowInfo`: Data model for window information

**Integration Points**:
- Distraction detector will use activity monitor data
- Coordinator will manage activity monitor lifecycle

### 3. Browser Detection & WebExtension Integration (Third Priority)

**Rationale**: This module provides critical browser integration functionality and builds on the patterns established in the activity monitor.

**Key Benefits**:
- Leverages platform abstraction patterns from the activity monitor
- Provides essential browser data for the distraction detector
- Already has a well-functioning implementation that requires minimal rewriting

**Key Interfaces**:
- `BrowserDetectorInterface`: Interface for detecting browser windows
- `TabTrackerInterface`: Interface for tracking browser tabs
- `TabBlockerInterface`: Interface for blocking browser tabs
- `UsageTrackerInterface`: Interface for tracking browser usage

**Integration Points**:
- Distraction detector will use browser integration data
- Alert system may use browser integration for notifications
- Coordinator will manage browser integration lifecycle

### 4. Alert System Refactoring (Fourth Priority)

**Rationale**: The alert system depends on configuration but is otherwise relatively independent. It should be implemented before the distraction detector, which will use it to notify users.

**Key Benefits**:
- Establishes notification patterns that will be used by the distraction detector
- Provides user feedback mechanisms for all other modules
- Relatively independent from other modules except for configuration

**Key Interfaces**:
- `AlertProvider`: Base interface for all alert providers
- `PlatformAlertInterface`: Platform-specific alert implementation
- `AlertSystem`: Main interface for the alert system

**Integration Points**:
- Distraction detector will use the alert system for notifications
- Coordinator will manage alert system lifecycle
- Configuration system will provide alert settings

### 5. Distraction Detector Refactoring (Fifth Priority)

**Rationale**: The distraction detector depends on the activity monitor, browser integration, domain classifier, and alert system. It should be implemented after these dependencies are in place.

**Key Benefits**:
- Integrates data from multiple sources (activity monitor, browser integration, domain classifier)
- Uses the alert system to notify users of distractions
- Represents a higher-level component that builds on lower-level functionality

**Key Interfaces**:
- `DistractionRule`: Interface for distraction detection rules
- `DistractionDetector`: Main interface for distraction detection
- `DistractionListener`: Interface for receiving distraction events

**Integration Points**:
- Uses activity monitor for window information
- Uses browser integration for tab information
- Uses domain classifier for URL categorization
- Uses alert system for notifications
- Coordinator will manage distraction detector lifecycle

### 6. Coordinator Implementation (Final Priority)

**Rationale**: The coordinator integrates all other modules and should be implemented last, once all the individual components are working properly.

**Key Benefits**:
- Brings together all refactored modules into a cohesive application
- Manages component lifecycle and inter-component communication
- Provides a unified interface for the UI layer
- Includes packaging and distribution functionality

**Key Interfaces**:
- `Component`: Base interface for all coordinator-managed components
- `FocusGuardCoordinator`: Main coordinator interface
- `EventBus`: Event communication system

**Integration Points**:
- Manages lifecycle of all other components
- Handles inter-component communication
- Provides a unified interface for the UI layer

## Implementation Approach

For each module, follow this general approach:

1. **Create Core Interfaces**: Define the interfaces that will be used by other modules
2. **Implement Core Functionality**: Implement the basic functionality required by other modules
3. **Add Advanced Features**: Add more advanced features once the core functionality is working
4. **Write Tests**: Create comprehensive tests for the module
5. **Document**: Document the module's API and usage patterns

## Design Patterns to Apply

The following design patterns should be consistently applied across all modules:

1. **Factory Method**: For creating platform-specific implementations
2. **Strategy**: For pluggable algorithms and behaviors
3. **Observer**: For event notification between components
4. **Adapter**: For integrating with legacy code
5. **Dependency Injection**: For providing dependencies to components
6. **Repository**: For data access abstraction

## Cross-Cutting Concerns

These concerns should be addressed consistently across all modules:

1. **Logging**: Use a consistent logging approach across all modules
2. **Error Handling**: Establish consistent error handling patterns
3. **Configuration**: Use the configuration system for all settings
4. **Testing**: Create unit tests for all components
5. **Documentation**: Document all public interfaces and classes

## Parallel Development Considerations

Some modules could potentially be developed in parallel if you have multiple developers:

- **Config System** and **Activity Monitor** could be developed simultaneously
- **Browser Integration** and **Alert System** could be developed simultaneously after the first two
- **Distraction Detector** and **Coordinator** should be developed sequentially after the others

## Migration Strategy

To ensure a smooth transition from the legacy `core` module to the new `core_v2` architecture:

1. **Parallel Implementation**: Keep the original components working while implementing the new ones
2. **Adapter Pattern**: Create adapters to allow new components to work with legacy code
3. **Feature Parity**: Ensure all existing functionality is preserved in the new implementation
4. **Incremental Adoption**: Replace legacy components one at a time
5. **Testing**: Thoroughly test each component before replacing its legacy counterpart

## Conclusion

This implementation order minimizes dependencies between modules and allows for incremental development and testing. By starting with the foundational components and working up to higher-level functionality, you'll establish consistent patterns and interfaces that can be reused across the application.

The refactoring effort will result in a more modular, maintainable, and testable architecture that will make it easier to add new features and fix bugs in the future.
