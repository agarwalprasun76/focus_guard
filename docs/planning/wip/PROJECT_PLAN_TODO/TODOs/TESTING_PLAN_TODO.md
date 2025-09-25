# Testing Plan for Calendar Demos

This document outlines the testing strategy for the reorganized calendar demos.

## Test Environment Setup

1. **Prerequisites**:
   - Python 3.8+
   - Required packages (install via `pip install -r requirements.txt`)
   - Google Calendar API credentials (for calendar integration tests)

2. **Test Data**:
   - Test calendar with sample events
   - Test domains for verification
   - Test window titles for domain extraction

## Test Categories

### 1. Core Functionality Tests

#### domain_classifier.py
- [ ] Test domain classification with various domain patterns
- [ ] Verify handling of invalid/empty domains
- [ ] Test memory usage with large domain lists

#### window_monitor.py
- [ ] Test window title extraction
- [ ] Verify process name retrieval
- [ ] Test memory efficiency during long monitoring sessions

#### calendar_test.py
- [ ] Test calendar API connectivity
- [ ] Verify event retrieval and parsing
- [ ] Test context detection

### 2. Feature Tests

#### Domain Allowance (basic.py)
- [ ] Test domain classification
- [ ] Verify whitelist functionality
- [ ] Test context-based domain allowance

#### Advanced Domain Allowance (advanced.py)
- [ ] Test calendar integration
- [ ] Verify real-time monitoring
- [ ] Test distraction detection

#### Activity Tracking (detailed_tracking.py)
- [ ] Test window activity monitoring
- [ ] Verify calendar context awareness
- [ ] Test domain filtering

### 3. Integrated Demos

#### focus_guard_lite.py
- [ ] Test basic functionality
- [ ] Verify calendar integration
- [ ] Test memory usage

#### focus_guard_pro.py
- [ ] Test all features
- [ ] Verify error handling
- [ ] Test performance under load

## Test Execution

### Manual Testing

1. **Core Tests**:
   ```bash
   # Run core tests
   python -m demos.calendar.core.domain_classifier
   python -m demos.calendar.core.window_monitor
   python -m demos.calendar.core.calendar_test
   ```

2. **Feature Tests**:
   ```bash
   # Domain allowance
   python -m demos.calendar.features.domain_allowance.basic
   python -m demos.calendar.features.domain_allowance.advanced
   
   # Activity tracking
   python -m demos.calendar.features.activity_tracking.detailed_tracking
   ```

3. **Integrated Demos**:
   ```bash
   # Lite version
   python -m demos.calendar.integrated.focus_guard_lite
   
   # Pro version
   python -m demos.calendar.integrated.focus_guard_pro
   ```

### Automated Testing (TODO)

1. **Unit Tests**:
   - [ ] Create test_*.py files for each module
   - [ ] Add test fixtures and mocks
   - [ ] Implement test cases for core functionality

2. **Integration Tests**:
   - [ ] Test module interactions
   - [ ] Verify data flow between components
   - [ ] Test error conditions

## Performance Testing

- [ ] Measure memory usage during long sessions
- [ ] Test with large numbers of calendar events
- [ ] Verify responsiveness during high system load

## Security Testing

- [ ] Validate input sanitization
- [ ] Test with malicious domain patterns
- [ ] Verify secure handling of calendar credentials

## Documentation

- [ ] Update README files
- [ ] Document API changes
- [ ] Add usage examples

## Known Issues

- [ ] List any known issues here
- [ ] Track resolution progress

## Test Sign-off

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Performance verified
- [ ] Security review completed
