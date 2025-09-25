# Application Packaging Workflow

This document outlines the complete workflow for packaging Focus Guard applications.

## Prerequisites

1. **Python Environment**
   ```bash
   pip install -r deployment/application/requirements/requirements_packaging.txt
   ```

2. **PyInstaller**
   ```bash
   pip install pyinstaller
   ```

3. **Inno Setup** (Windows only)
   - Download from: https://jrsoftware.org/isinfo.php
   - Install to default location

## Build Process

### 1. Build Executables

```bash
# From project root
cd deployment/application/windows/scripts
python build_exe.py
```

This will:
- Build `FocusGuard_CLI.exe` using `pyinstaller_cli.spec`
- Build `FocusGuard_Tray.exe` using `pyinstaller_tray.spec`
- Output executables to `deployment/application/dist/`
- Create build artifacts in `deployment/application/build/`

### 2. Create Windows Installer

```bash
# Using Inno Setup
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" deployment/application/windows/installers/inno_setup_script_mv3.iss
```

This creates a Windows installer in `deployment/application/windows/installers/output/`

### 3. Test Package

```bash
# Create test VM package
powershell deployment/tools/create_test_vm.ps1
```

## File Locations

- **Specs**: `deployment/application/windows/specs/*.spec`
- **Build Scripts**: `deployment/application/windows/scripts/build_exe.py`
- **Executables**: `deployment/application/dist/`
- **Build Artifacts**: `deployment/application/build/`
- **Installers**: `deployment/application/windows/installers/`
- **Version Info**: `deployment/application/windows/version_info.txt`

## Troubleshooting

### Build Failures
1. Check PyInstaller installation: `pip show pyinstaller`
2. Verify spec file paths are correct
3. Check for missing dependencies in requirements

### Large Executable Size
- Review included modules in spec files
- Consider using `--exclude-module` for unnecessary packages
- Use UPX compression if needed

### Installer Issues
- Ensure Inno Setup is installed correctly
- Check file paths in `.iss` files
- Verify output directory permissions

## Next Steps After Build

1. Test executables in `deployment/application/dist/`
2. Run installer: `deployment/installer/windows/install_focus_guard.bat`
3. Deploy browser extension using `deployment/tools/deploy.py`
