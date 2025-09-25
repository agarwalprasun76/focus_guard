# Diagnostics Tests

This directory contains diagnostic tests and utilities for the FocusGuard application, organized into logical modules.

## Directory Structure

```
diagnostics/
├── browser/                  # Browser-related diagnostics
│   ├── __init__.py
│   ├── test_browser_windows.py  # Check browser windows and titles
│   └── test_extension.py        # Test browser extension connection
│
├── server/                   # Server testing utilities
│   ├── __init__.py
│   ├── test_server.py        # Mock HTTP server for testing
│   └── server_utils.py       # Common server utilities
│
├── tab_server/               # Tab server diagnostics
│   ├── __init__.py
│   ├── test_status.py        # Check tab server status
│   └── server_runner.py      # Script to start the tab server
│
└── fixtures/                 # Test fixtures
    └── __init__.py
```

## Usage

### Browser Diagnostics

- **Check browser windows**:
  ```bash
  python -m tests.diagnostics.browser.test_browser_windows
  ```

- **Test browser extension connection**:
  ```bash
  python -m tests.diagnostics.browser.test_extension
  ```

### Tab Server

- **Check tab server status**:
  ```bash
  python -m tests.diagnostics.tab_server.test_status
  ```

- **Start the tab server**:
  ```bash
  python -m tests.diagnostics.tab_server.server_runner
  ```

### Server Testing

- **Run test HTTP server**:
  ```bash
  python -m tests.diagnostics.server.test_server
  ```

## Development

- All imports should be relative to the project root
- Use the logger with appropriate module names (e.g., "browser.windows", "tab_server.runner")
- Add new test files to the appropriate module directory
- Update this README when adding new test categories or significant features
