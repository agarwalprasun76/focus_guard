# Module: Cross Platform Utilities (`cross_platform`)

## Purpose
- Provide OS-specific functions to get active window/app info

## To-Do List
- [x] Implement for Windows (win32gui, psutil)
- [ ] Implement for macOS (Quartz, AppKit)
- [ ] Implement for Linux (wmctrl, xprop, psutil)
- [ ] Abstract interface for use by `activity_monitor`

## Requirements
- Must detect active window/app reliably on all platforms
- Should fail gracefully if unsupported

## Testing Plan
- Manual testing on all platforms
- Mock platform calls in unit tests
