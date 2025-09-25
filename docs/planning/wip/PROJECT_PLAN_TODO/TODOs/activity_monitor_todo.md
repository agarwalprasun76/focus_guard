# Module: Activity Monitor (`activity_monitor`)

## Purpose
- Monitor the currently active application and window title (cross-platform)
- Interface with platform-specific utilities
- Optionally monitor browser tabs (future)

## To-Do List
- [ ] Implement OS-agnostic interface
- [ ] Integrate platform-specific logic from `cross_platform`
- [ ] Poll active window every N seconds
- [ ] Return app name, window title, timestamp
- [ ] (Future) Integrate browser tab monitoring

## Requirements
- Must work on Windows, macOS, Linux
- Should be efficient and not impact system performance

## Testing Plan
- Unit tests for interface
- Manual cross-platform checks
- Mock platform-specific calls for CI
