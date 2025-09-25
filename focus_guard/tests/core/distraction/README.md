# Distraction Detection Tests

This directory contains tests for the Focus Guard distraction detection system. The tests cover various aspects of the distraction detection module, including models, rules, handlers, and trackers.

## Overview

The distraction detection system is a rule-based system that monitors user activity and detects potential distractions. It uses a set of rules to evaluate the current state and generate alerts when distractions are detected. These alerts are then processed by handlers that can take actions such as showing notifications or blocking distracting websites.

## Test Structure

The tests are organized into the following directories and files:

### Main Test Files

- `test_models.py`: Tests for the core data models used in distraction detection
- `test_rules.py`: Tests for the rule evaluation system
- `test_handlers.py`: Tests for alert handlers

### Subdirectories

#### Handlers Tests (`handlers/`)

- `test_blocking_handler.py`: Tests for the handler that blocks distracting domains
- `test_notification_handler.py`: Tests for the handler that shows notifications

#### Rules Tests (`rules/`)

- `test_area_rule.py`: Tests for the rule that detects window area increases
- `test_base_rule.py`: Tests for the base rule functionality
- `test_context_rule.py`: Tests for the rule that detects context switching
- `test_url_rule.py`: Tests for the rule that detects distracting URLs

#### Trackers Tests (`trackers/`)

- `test_browser_tracker.py`: Tests for the browser state tracker

## Test Coverage

The tests cover the following aspects of the distraction detection system:

### Models

- `AlertLevel`: Enum for distraction alert levels (INFO, WARNING, CRITICAL)
- `DistractionAlert`: Data structure for distraction alerts
- `DistractionState`: State tracking for distraction detection
- `DistractionEvent`: Event data for distraction events

### Rules

- Base rule functionality (enabling/disabling, alert creation)
- URL-based distraction detection
- Context switching detection
- Window area increase detection

### Handlers

- Notification handling (showing notifications based on alert level)
- Domain blocking (blocking distracting domains and closing tabs)

### Trackers

- Browser state tracking (monitoring browser tabs and URLs)

## Running the Tests

To run all distraction tests:

```bash
python -m pytest focus_guard/tests/core/distraction -v
```

To run a specific test file:

```bash
python -m pytest focus_guard/tests/core/distraction/test_models.py -v
```

## Implementation Notes

### Circular Import Resolution

The distraction detection module was refactored to avoid circular imports by:

1. Creating a dedicated `types.py` module to hold shared types like `AlertLevel`, `DistractionAlert`, and `DistractionEvent`
2. Using TYPE_CHECKING for type annotations to avoid runtime imports
3. Moving shared types to a module with minimal dependencies

### Test Mocking

Many tests use mocking to isolate components:

- Browser integration is mocked to avoid actual browser interactions
- Domain extraction utilities are mocked to provide consistent test data
- Configuration is mocked to provide controlled test settings

### Test Independence

Each test is designed to be independent and can be run in isolation. Test fixtures are used to set up the necessary environment for each test.
