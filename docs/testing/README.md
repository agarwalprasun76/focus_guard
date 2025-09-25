# Focus Guard Extension Tools

Development and testing utilities for the Focus Guard browser extension.

## Directory Structure

```
tools/
├── extension/              # Extension-specific utilities
│   ├── check_edge_extensions.py          # Check Edge extensions directory
│   ├── check_edge_extensions_simple.py   # Simplified extension checker
│   ├── get_extension_id.py               # Get extension ID helper
│   └── install_edge_extension_manual.py  # Manual installation guide
└── testing/                # Manual testing scripts
    ├── test_robust_extension_installation.py  # Robust installer tests
    ├── test_actual_functionality.py           # Functionality verification
    ├── test_admin_functionality.py            # Admin features testing
    ├── test_edge_installation.py              # Edge-specific tests
    └── test_real_installation.py              # Real installation tests
```

## Extension Utilities

### Check Extensions
```bash
python extension/check_edge_extensions.py       # Detailed check
python extension/check_edge_extensions_simple.py # Simple check
```

### Get Extension ID
```bash
python extension/get_extension_id.py
```

### Manual Installation Guide
```bash
python extension/install_edge_extension_manual.py
```

## Testing Scripts

### Run All Tests
```bash
python testing/test_robust_extension_installation.py
python testing/test_actual_functionality.py
python testing/test_admin_functionality.py
python testing/test_edge_installation.py
python testing/test_real_installation.py
```

### Individual Test Categories
- **Robust Installation**: Tests retry logic, protection, verification
- **Actual Functionality**: Tests core features and integration
- **Admin Functionality**: Tests Windows admin privileges and protection
- **Edge Installation**: Tests Edge-specific installation methods
- **Real Installation**: Tests actual browser installation process

## Usage Notes

These tools are for development and debugging purposes. For production deployment, use the scripts in the `deployment/` directory.
