# cross_platform.py

This module provides cross-platform utilities for detecting and analyzing windows and applications.

## Key Functions
- `get_active_window_info()`: Returns info about the currently active window/app (Windows, Linux implemented).
- `get_window_info(hwnd)`: Returns info (including area) for a given window handle (Windows).
- `enumerate_top_windows(top_region=200)`: Lists all visible windows at the top of the screen (Windows).
- `get_screen_area()`: Returns the area of the primary screen (Windows).

## Features
- Filters out desktop and background windows for accurate area/fraction reporting.
- Returns window area and fraction of screen occupied for UI analysis.

## Extensibility
- Linux support (via wmctrl, xprop) is partially implemented.
- macOS support is planned.

## Requirements
- Windows: `pywin32`, `psutil`
- Linux: `wmctrl`, `xprop`, `psutil`

## Usage
See the `demos/cross_platform/` folder for example scripts.
