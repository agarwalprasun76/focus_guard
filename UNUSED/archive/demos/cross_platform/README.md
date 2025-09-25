# Cross Platform Demos

This folder contains demonstration scripts that showcase the window and application monitoring capabilities of the Focus Guard system. These demos are primarily designed for Windows platforms.

## Available Demos

### 1. Activity Monitor Demo (`demo_activity_monitor.py`)
Tracks and displays the currently active window in real-time, showing window titles, application names, and process IDs. Useful for understanding window switching behavior.

**Features:**
- Real-time window activity tracking
- Displays comprehensive window information
- Runs continuously until manually stopped

**Usage:**
```bash
python -m demos.cross_platform.demo_activity_monitor
```

### 2. Top Windows Analysis (`demo_enumerate_top_windows.py`)
Analyzes and displays information about windows in the top portion of the screen, including their size, position, and screen space usage.

**Features:**
- Identifies windows in the top screen region
- Calculates window areas and screen percentages
- Runs for 1 minute with 5-second updates

**Usage:**
```bash
python -m demos.cross_platform.demo_enumerate_top_windows
```

## Requirements
- Windows OS (currently only Windows is supported)
- Python 3.8+
- Required packages: `pywin32`, `psutil`

## Getting Started
1. Install the required packages:
   ```bash
   pip install pywin32 psutil
   ```

2. Run any demo using the commands shown above.

## Notes
- These scripts are primarily intended for development and debugging purposes.
- For production use, consider using the core modules directly in your application.
- Some features may be Windows-specific due to platform dependencies.

## See Also
- `core/activity_monitor.py` - The main activity monitoring implementation
- `utils/cross_platform.py` - Cross-platform window utilities
