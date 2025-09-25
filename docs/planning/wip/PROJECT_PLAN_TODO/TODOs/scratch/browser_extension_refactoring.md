# Browser Extension Refactoring Plan

## Current State Analysis

### Issues Identified
1. **Communication Gap**: Browser extension reports tabs to log files but the tab server is not detecting/receiving these tabs
2. **Legacy Code Dependencies**: Current implementation relies on code in `core` directory that needs to be migrated to `core_v2`
3. **Integration Challenges**: Need to integrate browser/tab detection with `core_v2/activity/browser`
4. **Process Robustness**: Tab server process needs to be more robust (auto-restart, error handling)
5. **Extension Setup**: Need programmatic extension setup/installation for first-time users

### Current Architecture
- Browser extension (Manifest V3) in `core/browser_detection/webextension_mv3/`
- Native messaging host (`focus_guard_native_host.exe`) for extension-app communication
- Tab server in legacy code handling HTTP communication with extension
- Partial implementation in `core_v2/browser/` following interface-based design

## Refactoring Goals

1. **Fix Communication Issues**: Ensure reliable communication between extension and tab server
2. **Complete Migration**: Move all browser detection/extension functionality from `core` to `core_v2`
3. **Robust Process Management**: Implement auto-restart and health monitoring for extension and tab server
4. **Programmatic Extension Setup**: Create streamlined extension installation process
5. **Clean Integration**: Integrate with `core_v2/activity/browser` for activity tracking

## Detailed Implementation Plan

### 1. Diagnose and Fix Communication Issues

#### 1.1 Tab Server Communication Diagnosis
- [ ] Add detailed logging to tab server to track incoming requests
- [ ] Verify server is running on the expected port (default: 5000)
- [ ] Check for any firewall or permission issues blocking communication
- [ ] Validate JSON format of messages from extension to server
- [ ] Test direct HTTP requests to tab server to confirm functionality

#### 1.2 Extension Communication Diagnosis
- [ ] Add detailed logging to extension background script
- [ ] Verify extension is correctly sending data to tab server
- [ ] Check for any CORS or network issues in extension
- [ ] Validate native messaging host is correctly installed and functioning

#### 1.3 Fix Communication Pipeline
- [ ] Update extension code to ensure reliable communication with tab server
- [ ] Implement retry logic for failed communications
- [ ] Add heartbeat mechanism between extension and tab server
- [ ] Implement proper error handling and reporting

### 2. Tab Server Process Robustness

#### 2.1 Process Manager Implementation
- [ ] Create `BrowserExtensionProcessManager` class in `core_v2/browser/extension/process_manager.py`
- [ ] Implement auto-restart functionality for tab server
- [ ] Add health monitoring with periodic checks
- [ ] Implement graceful shutdown and cleanup

#### 2.2 Error Handling and Logging
- [ ] Implement comprehensive error handling in tab server
- [ ] Add structured logging for debugging and monitoring
- [ ] Create error reporting mechanism to notify application of issues

### 3. Extension Setup and Management

#### 3.1 Extension Installation
- [ ] Create `ExtensionInstaller` class in `core_v2/browser/extension/installer.py`
- [ ] Implement browser detection for supported browsers
- [ ] Add automated installation of extension for each browser type
- [ ] Implement validation to confirm successful installation

#### 3.2 Native Messaging Host Setup
- [ ] Create `NativeMessagingHostManager` in `core_v2/browser/extension/native_host.py`
- [ ] Implement automated setup of native messaging host
- [ ] Add registry/filesystem operations for proper configuration
- [ ] Implement validation and troubleshooting utilities

#### 3.3 Extension Management UI Integration
- [ ] Create simple UI components for extension management
- [ ] Implement status reporting for extension health
- [ ] Add troubleshooting guidance for common issues

### 4. Migration from Core to Core_v2

#### 4.1 Core Components Migration
- [ ] Move and refactor `tab_server_v2.py` to `core_v2/browser/extension/tab_server.py`
- [ ] Move and refactor `browser_integration_v2.py` to `core_v2/browser/integration/browser_integration.py`
- [ ] Move and refactor `process_manager_v2.py` to `core_v2/browser/extension/process_manager.py`
- [ ] Update import paths and dependencies

#### 4.2 Extension Code Migration
- [ ] Review and update extension code if needed
- [ ] Ensure compatibility with new tab server implementation
- [ ] Update manifest and permissions as needed

#### 4.3 Adapter Implementation
- [ ] Complete adapter implementation in `core_v2/browser/adapter.py`
- [ ] Ensure backward compatibility for existing code
- [ ] Implement proper dependency injection

### 5. Integration with Activity Tracking

#### 5.1 Browser Activity Integration
- [ ] Integrate tab tracking with `core_v2/activity/browser`
- [ ] Implement event forwarding from tab tracker to activity system
- [ ] Create domain classification integration

#### 5.2 Usage Tracking Implementation
- [ ] Implement `BrowserUsageTracker` in `core_v2/browser/usage/tracker.py`
- [ ] Create storage backend for usage data
- [ ] Implement analytics and reporting capabilities

### 6. Testing and Validation

#### 6.1 Unit Tests
- [ ] Create unit tests for all new components
- [ ] Implement mock objects for testing
- [ ] Ensure high test coverage for critical components

#### 6.2 Integration Tests
- [ ] Create integration tests for extension-server communication
- [ ] Test process management and auto-restart functionality
- [ ] Validate activity tracking integration

#### 6.3 End-to-End Tests
- [ ] Create end-to-end tests for complete browser detection pipeline
- [ ] Test extension installation and setup
- [ ] Validate tab tracking and blocking functionality

## Implementation Timeline

### Week 1: Diagnosis and Core Fixes
- Days 1-2: Diagnose communication issues
- Days 3-4: Fix communication pipeline
- Days 5-7: Implement process robustness improvements

### Week 2: Extension Management and Migration
- Days 1-3: Implement extension setup and management
- Days 4-7: Migrate core components to core_v2

### Week 3: Integration and Testing
- Days 1-3: Integrate with activity tracking
- Days 4-6: Implement comprehensive testing
- Day 7: Documentation and final review

## Success Criteria

1. **Communication Reliability**: Extension consistently reports tabs to tab server
2. **Process Robustness**: Tab server automatically restarts if it crashes
3. **Extension Management**: One-click extension installation for supported browsers
4. **Complete Migration**: All browser detection code moved to core_v2
5. **Activity Integration**: Browser activity properly tracked and categorized

## Conclusion

This refactoring plan addresses the immediate issues with the browser extension integration while also providing a path to fully migrate the functionality to the core_v2 architecture. By focusing on communication reliability, process robustness, and clean integration with the activity tracking system, we'll create a more maintainable and reliable browser detection system.

The plan prioritizes fixing the immediate issues with tab server communication before moving on to broader refactoring goals, ensuring that the system remains functional throughout the migration process.
