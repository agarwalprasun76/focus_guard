"""
Build script for creating a standalone executable.

This script uses PyInstaller to create a single .exe file that can be
deployed on another machine without requiring Python installation.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def build_exe(
    output_name: str = "FocusGuardMonitor",
    one_file: bool = True,
    console: bool = False,
    icon_path: str = None,
    include_config_ui: bool = False
) -> bool:
    """
    Build the Focus Guard executable using PyInstaller.
    
    Args:
        output_name: Name for the output executable
        one_file: Create single .exe file (vs folder)
        console: Show console window
        icon_path: Path to .ico file for the executable
        include_config_ui: Include the configuration UI
        
    Returns:
        True if build was successful
    """
    project_root = get_project_root()
    
    # Entry point script (main_service.py is the single source of truth)
    entry_script = project_root / 'focus_guard' / 'deployment' / 'main_service.py'
    
    # Verify entry script exists
    if not ensure_entry_script_exists(entry_script):
        return False
    
    # Build PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', output_name,
        '--clean',
        '--noconfirm',
    ]
    
    if one_file:
        cmd.append('--onefile')
    
    if not console:
        cmd.append('--noconsole')
    else:
        cmd.append('--console')
    
    if icon_path and Path(icon_path).exists():
        cmd.extend(['--icon', icon_path])
    
    # Add hidden imports for dynamic imports
    hidden_imports = [
        'focus_guard.core.activity.enhanced_logger',
        'focus_guard.core.activity.monitor',
        'focus_guard.core.activity.idle_detector',
        'focus_guard.core.activity.usage_tracker',
        'focus_guard.core.activity.platform.windows',
        'focus_guard.deployment.config',
        'focus_guard.deployment.email_reporter',
        'focus_guard.deployment.service',
        'win32api',
        'win32con',
        'win32gui',
        'win32process',
        'win32ts',
        'pywintypes',
    ]
    
    for imp in hidden_imports:
        cmd.extend(['--hidden-import', imp])
    
    # Add data files
    data_files = [
        (str(project_root / 'config' / 'focus_guard_config_template.json'), 'config'),
    ]

    admin_ui_dist = project_root / 'admin_ui' / 'dist'
    if admin_ui_dist.exists():
        data_files.append((str(admin_ui_dist), 'admin_ui/dist'))
    
    for src, dest in data_files:
        if Path(src).exists():
            cmd.extend(['--add-data', f'{src};{dest}'])
    
    # Add the entry script
    cmd.append(str(entry_script))
    
    # Run PyInstaller
    print(f"Building {output_name}.exe...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=str(project_root), check=True)
        
        # Move output to a more accessible location
        dist_dir = project_root / 'dist'
        if dist_dir.exists():
            print(f"\nBuild successful!")
            print(f"Executable location: {dist_dir / output_name}.exe")
            return True
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False
    except FileNotFoundError:
        print("PyInstaller not found. Install with: pip install pyinstaller")
        return False
    
    return False


def ensure_entry_script_exists(script_path: Path) -> bool:
    """
    Ensure the main_service.py entry script exists.
    
    The entry script is maintained as a separate file (main_service.py) to avoid
    code duplication. This function just verifies it exists.
    
    Args:
        script_path: Expected path to the entry script
        
    Returns:
        True if the script exists
    """
    if script_path.exists():
        return True
    
    print(f"ERROR: Entry script not found: {script_path}")
    print("The main_service.py file should exist in focus_guard/deployment/")
    return False


def create_spec_file(output_name: str = "FocusGuardMonitor") -> Path:
    """
    Create a PyInstaller .spec file for more control over the build.
    
    Args:
        output_name: Name for the output executable
        
    Returns:
        Path to the created .spec file
    """
    project_root = get_project_root()
    spec_path = project_root / f'{output_name}.spec'
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Focus Guard Activity Monitor

import sys
from pathlib import Path

block_cipher = None

# Project paths
project_root = Path(r'{project_root}')
entry_script = project_root / 'focus_guard' / 'deployment' / 'main_service.py'

a = Analysis(
    [str(entry_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'config' / 'focus_guard_config_template.json'), 'config'),
    ],
    hiddenimports=[
        'focus_guard.core.activity.enhanced_logger',
        'focus_guard.core.activity.monitor',
        'focus_guard.core.activity.idle_detector',
        'focus_guard.core.activity.usage_tracker',
        'focus_guard.core.activity.platform.windows',
        'focus_guard.deployment.config',
        'focus_guard.deployment.email_reporter',
        'focus_guard.deployment.service',
        'win32api',
        'win32con',
        'win32gui',
        'win32process',
        'win32ts',
        'win32event',
        'win32service',
        'win32serviceutil',
        'servicemanager',
        'pywintypes',
        'sqlite3',
        'email.mime.text',
        'email.mime.multipart',
        'smtplib',
        'ssl',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
        'PyQt5',
        'PyQt6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{output_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='path/to/icon.ico',  # Uncomment and set path to add icon
)
'''
    
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"Created spec file: {spec_path}")
    return spec_path


def main():
    """Main entry point for the build script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build Focus Guard executable")
    parser.add_argument('--name', default='FocusGuardMonitor', help='Output executable name')
    parser.add_argument('--console', action='store_true', help='Show console window')
    parser.add_argument('--icon', help='Path to .ico file')
    parser.add_argument('--spec-only', action='store_true', help='Only create .spec file')
    parser.add_argument('--use-spec', action='store_true', help='Build using .spec file')
    
    args = parser.parse_args()
    
    project_root = get_project_root()
    
    # Verify entry script exists (main_service.py is the single source of truth)
    entry_script = project_root / 'focus_guard' / 'deployment' / 'main_service.py'
    if not ensure_entry_script_exists(entry_script):
        print("Cannot proceed without entry script.")
        return
    
    if args.spec_only:
        create_spec_file(args.name)
        return
    
    if args.use_spec:
        spec_path = project_root / f'{args.name}.spec'
        if not spec_path.exists():
            spec_path = create_spec_file(args.name)
        
        print(f"Building with spec file: {spec_path}")
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller',
            '--clean', '--noconfirm',
            str(spec_path)
        ], cwd=str(project_root))
        
        if result.returncode == 0:
            print(f"\nBuild successful!")
            print(f"Executable: {project_root / 'dist' / args.name}.exe")
    else:
        build_exe(
            output_name=args.name,
            console=args.console,
            icon_path=args.icon
        )


if __name__ == '__main__':
    main()
