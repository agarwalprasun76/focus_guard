# Cross Platform Tests

This folder contains tests for the cross_platform module.

## Files
- **test_cross_platform.py**: Unit and integration tests for window detection, mocking platform calls for CI.

## Usage
Run tests from the project root for correct imports:

    python -m pytest tests/cross_platform/test_cross_platform.py

## Requirements
- Windows OS for full functionality
- `pytest`, `pywin32`, `psutil`
