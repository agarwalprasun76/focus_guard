# Focus Guard Scripts

This directory contains various scripts for setting up, validating, testing, and troubleshooting the Focus Guard application.

## Directory Structure

The scripts are organized by purpose and then by module:

```
scripts/
├── setup/                # Installation and setup scripts
├── validation/           # Validation and verification scripts
├── testing/              # Testing scripts
│   ├── integration/      # Integration tests
│   └── user/             # User-facing tests
├── troubleshooting/      # Troubleshooting scripts
├── demo/                 # Demo and example scripts
├── dev/                  # Development scripts
└── utils/                # Utility scripts
```

## Script Categories

### Setup Scripts

Scripts for installing and setting up Focus Guard components:

- **Browser Extension Setup**: Scripts for setting up browser extensions
  - `setup/browser_extension/setup_browser_extension.py`: Sets up browser extension infrastructure
- **Native Host Setup**: Scripts for setting up native messaging hosts
  - `setup/native_host/setup_native_host.py`: Sets up native messaging host for browser communication

### Validation Scripts

Scripts for validating the correct operation of Focus Guard components:

- **Browser Extension Validation**: Scripts for validating browser extension functionality
  - `validation/browser_extension/test_extension_install.py`: Tests browser extension installation
  - `validation/browser_extension/test_extension_fixes.py`: Verifies fixes for browser extension issues
- **Core Validation**: Scripts for validating core functionality
  - `validation/core/validate_browser_integration.py`: Validates browser integration

### Testing Scripts

Scripts for testing Focus Guard functionality:

- **Integration Tests**: Scripts for testing integration between components
  - `testing/integration/browser/test_domain_blocking.py`: Tests domain blocking functionality
  - `testing/integration/browser/browser_tab_blocker.py`: Tests tab blocking functionality
  - `testing/integration/activity/demo_activity_integration.py`: Tests activity tracking integration
- **User Tests**: Scripts for user-facing tests
  - `testing/user/user_test_guide.py`: User-facing test guide

### Troubleshooting Scripts

Scripts for troubleshooting issues:

- **Browser Extension Troubleshooting**: Scripts for troubleshooting browser extension issues
  - `troubleshooting/browser_extension/troubleshoot_browser_extension.py`: Troubleshoots browser extension issues

### Demo Scripts

Scripts for demonstrating Focus Guard functionality:

- **Browser Demos**: Scripts for demonstrating browser-related functionality
  - `demo/browser/demo_extension_install.py`: Demonstrates browser extension installation

### Development Scripts

Scripts for development purposes:

- `dev/run_focus_guard.py`: Runs Focus Guard in development mode
- `dev/start_tab_server.py`: Starts the tab server for development

### Utility Scripts

Utility scripts for common tasks:

- **Common Utilities**: Common utility functions used across scripts

## Usage Guidelines

1. **Setup Scripts**: Run these scripts during initial installation or when reinstalling components
2. **Validation Scripts**: Run these scripts to validate that components are working correctly
3. **Testing Scripts**: Run these scripts to test specific functionality
4. **Troubleshooting Scripts**: Run these scripts when encountering issues
5. **Demo Scripts**: Run these scripts to see demonstrations of functionality
6. **Development Scripts**: Use these scripts during development

## Python Path Management

Most scripts automatically add the project root to the Python path using:

```python
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

## Common Dependencies

Most scripts depend on the following:

- `focus_guard.core.browser.models.browser`: Browser models and types
- `focus_guard.core.browser.extension.installer`: Extension installation functionality
- `focus_guard.core.browser.extension.tab_server`: Tab server functionality
- `focus_guard.core.browser.extension.manager`: Browser extension management

## Contributing

When adding new scripts:

1. Place them in the appropriate category directory
2. Follow the naming convention of existing scripts
3. Add appropriate documentation in the script and in the README.md
4. Ensure proper error handling and logging
5. Use consistent path handling with `pathlib`
