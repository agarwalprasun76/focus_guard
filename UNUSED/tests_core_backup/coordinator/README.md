# Coordinator Tests

This directory contains comprehensive tests for the Focus Guard coordinator module, which handles the core functionality of the Focus Guard application. The tests are written using `pytest` with `pytest-asyncio` for async test support.

## Test Structure

The test suite is organized into the following test files:

1. **Core Component Tests**
   - `test_base_component_pytest.py`: Tests for the base component functionality
   - `test_events_pytest.py`: Tests for event handling and processing
   - `test_interfaces_pytest.py`: Tests for component interfaces
   - `test_lifecycle_pytest.py`: Tests for component lifecycle management

2. **Component-Specific Tests**
   - `test_activity_component_pytest.py`: Tests for activity monitoring
   - `test_alert_component_pytest.py`: Tests for the alert system
   - `test_api_component_pytest.py`: Tests for API integration
   - `test_browser_component_pytest.py`: Tests for browser integration
   - `test_classification_component_pytest.py`: Tests for domain classification
   - `test_config_component_pytest.py`: Tests for configuration handling
   - `test_distraction_component_pytest.py`: Tests for distraction detection

3. **Integration Tests**
   - `test_coordinator_integration_pytest.py`: End-to-end tests for coordinator integration

## Test Dependencies

The tests require the following Python packages:
- `pytest>=7.0.0`
- `pytest-asyncio>=0.21.0`
- `pytest-mock>=3.10.0`

## Running Tests

To run all tests:

```bash
# Run all tests in the coordinator directory (excluding old/ folder)
pytest tests/core_v2/coordinator -v --ignore=tests/core_v2/coordinator/old
```

To run a specific test file:

```bash
pytest tests/core_v2/coordinator/test_base_component_pytest.py -v
```

To run tests with coverage report:

```bash
pytest tests/core_v2/coordinator --cov=core_v2.coordinator --cov-report=term-missing -v
```

## Test Conventions

1. **Test Classes**: Each test file contains a test class named `Test[Component]Pytest`.
2. **Fixtures**: Common test fixtures are defined at the class or module level.
3. **Async Tests**: All async tests use `@pytest.mark.asyncio` decorator.
4. **Mocks**: `unittest.mock.AsyncMock` and `MagicMock` are used for mocking async and sync methods respectively.

## Common Test Patterns

### Component Initialization
```python
@pytest.mark.asyncio
async def test_initialization(self, mock_deps):
    component = MyComponent(**mock_deps)
    assert component is not None
    # Additional assertions
```

### Lifecycle Testing
```python
async def test_lifecycle(self, component):
    # Test initialization
    await component.initialize()
    assert component.initialized
    
    # Test start
    await component.start()
    assert component.running
    
    # Test stop
    await component.stop()
    assert not component.running
```

### Event Handling
```python
async def test_event_handling(self, component, mock_event_bus):
    test_event = EventData(
        event_type=EventTypes.TEST_EVENT,
        data={"key": "value"}
    )
    
    await component.on_event(test_event)
    # Assert event was handled correctly
```

## Known Issues

1. **Async Mock Warnings**: Some tests show "coroutine was never awaited" warnings. These are typically related to mock objects in test setup and don't affect test results.

2. **Pytest Markers**: Some tests have `@pytest.mark.asyncio` on non-async functions, which triggers warnings.

## Adding New Tests

When adding new tests, please follow these guidelines:

1. Use descriptive test method names that describe the behavior being tested.
2. Group related tests in the same test class.
3. Use fixtures for common test setup.
4. Keep tests focused on a single behavior.
5. Use appropriate assertions with helpful failure messages.

## Test Coverage

The test suite provides comprehensive coverage of the coordinator module, including:
- Component initialization and configuration
- Event handling and propagation
- Lifecycle management
- Error conditions and edge cases
- Integration between components

## Debugging Tests

To debug a failing test:

```bash
# Run with pdb on failure
pytest tests/core_v2/coordinator/test_my_component.py -v --pdb

# Run with detailed logging
pytest tests/core_v2/coordinator/test_my_component.py -v -s
```

## License

[Your License Information Here]
