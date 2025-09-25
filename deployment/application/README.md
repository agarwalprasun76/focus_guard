# Focus Guard Windows .exe Packaging Guide

This guide covers packaging Focus Guard into standalone Windows executables for distribution.

## Packaging Options

### 1. PyInstaller (Recommended)
- **Best for**: Complete standalone executables
- **Pros**: Bundles all dependencies, works with PyQt5, handles complex imports
- **Cons**: Large file sizes (50-100MB)

### 2. cx_Freeze
- **Best for**: Alternative to PyInstaller
- **Pros**: Good Python 3 support, cross-platform
- **Cons**: More configuration needed

### 3. Nuitka
- **Best for**: Performance-optimized executables
- **Pros**: Compiles to C++, faster execution
- **Cons**: Complex setup, larger learning curve

## Recommended Approach: PyInstaller

### Installation
```bash
pip install pyinstaller
pip install pyinstaller[encryption]  # Optional: for encrypted executables
```

### Target Executables

1. **FocusGuard CLI** (`focus_guard_cli.exe`)
   - Entry point: `focus_guard/cli/windows_cli.py`
   - Console application
   - Size: ~40-60MB

2. **FocusGuard Tray** (`focus_guard_tray.exe`)
   - Entry point: `focus_guard/gui/windows_tray.py`
   - GUI application (no console)
   - Size: ~60-80MB (includes PyQt5)

3. **FocusGuard Installer** (`focus_guard_setup.exe`)
   - Custom installer that deploys both executables
   - Handles browser extension installation
   - Creates shortcuts and registry entries

## Implementation Steps

### Phase 1: Basic PyInstaller Setup
1. Create `.spec` files for each executable
2. Configure hidden imports and data files
3. Test basic packaging

### Phase 2: Advanced Configuration
1. Add icons and version info
2. Handle PyQt5 and extension files
3. Optimize file size and startup time

### Phase 3: Distribution Package
1. Create NSIS installer script
2. Bundle executables with dependencies
3. Add auto-update mechanism

### Phase 4: Testing & Deployment
1. Test on clean Windows systems
2. Create signed executables (optional)
3. Set up distribution pipeline

## File Structure After Packaging

```
dist/
├── FocusGuard_CLI.exe              # Command-line interface
├── FocusGuard_Tray.exe             # System tray GUI
├── FocusGuard_Setup.exe            # Complete installer
└── resources/
    ├── extension/                  # Browser extension files
    ├── config/                     # Default configuration
    └── icons/                      # Application icons
```

## Dependencies to Bundle

- Python runtime
- PyQt5 (for GUI)
- OpenAI library (for LLM classifier)
- Browser extension files
- Configuration files
- Domain lists and caches

## Estimated Sizes

- CLI executable: ~50MB
- Tray GUI executable: ~80MB
- Complete installer: ~100MB
- Installed footprint: ~150MB

## Next Steps

Run the packaging scripts in this directory to create Windows executables.
