# Focus Guard Testing Guide

## Current Test Status

### Working Tests
- **Coordinator Integration Tests**: All tests in `focus_guard/tests/core/coordinator/test_coordinator_integration_pytest.py` are passing.
  - These tests verify the core functionality of the Focus Guard coordinator and its interaction with components.
  - Includes tests for component registration, lifecycle management, event propagation, and health checks.

### Known Issues

1. **Legacy/Archived Tests**:
   - Tests in the `UNUSED/` directory and some in `focus_guard/tests/core/` are failing due to:
     - Missing modules (e.g., `ModuleNotFoundError: No module named 'core'`)
     - Import errors from refactored code
     - Outdated test code that hasn't been maintained
     - We only care about tests in focus_guard\tests\core and should ignore those in focus_guard\tests\core\UNUSED
     - It is possible that the tests in focus_guard\tests\core\UNUSED can be helpful to increase coverage and handle edge cases but they are not compatible with the current codebase and should be refactored to work with the current codebase. They should be added only if they improve test coverage.

2. **Test Dependencies**:
   - Some tests may require external services or specific environment setup.
   - The test suite is being actively refactored to use modern Python practices (pytest-asyncio, proper fixtures, etc.).

## Running Tests

### Prerequisites
- Python 3.8+
- Dependencies installed: `pip install -e .[dev]`

### Running Working Tests

1. **Run all coordinator integration tests**:
   ```bash
   python -m pytest -v focus_guard/tests/core/coordinator/test_coordinator_integration_pytest.py
   ```

2. **Run a specific test**:
   ```bash
   python -m pytest -v focus_guard/tests/core/coordinator/test_coordinator_integration_pytest.py::test_component_registration
   ```

### Test Coverage

To generate a coverage report for the working tests:

```bash
pytest --cov=focus_guard.core.coordinator focus_guard/tests/core/coordinator/test_coordinator_integration_pytest.py
```

## Troubleshooting

### Common Issues

1. **Import Errors**:
   - Ensure the project root is in your `PYTHONPATH`
   - Run tests from the project root directory
   - Check that all dependencies are installed

2. **Test Discovery Issues**:
   - The `pytest.ini` file configures pytest to find tests correctly
   - If you modify the project structure, update `pytest.ini` accordingly

## Next Steps

1. **Test Migration**:
   - Continue migrating tests to use pytest-asyncio
   - Update test fixtures to use dependency injection
   - Add comprehensive test coverage for new features

2. **Documentation**:
   - Document the test architecture
   - Add docstrings to test functions
   - Create test data and mocks documentation

## Contributing

When adding new tests:
1. Follow the existing pytest-asyncio pattern
2. Use fixtures for test dependencies
3. Add appropriate docstrings and comments
4. Ensure tests are isolated and independent
