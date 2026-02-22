"""
Installer script for Focus Guard Activity Monitor.

This module provides functionality to install the activity monitor as a
Windows service with admin privileges and protected file storage.
"""

import os
import sys
import ctypes
import subprocess
import shutil
import winreg
from pathlib import Path
from typing import Optional, Tuple

from focus_guard.deployment.config import DeploymentConfig, create_default_config


def is_admin() -> bool:
    """Check if the current process has admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin(script_path: str, *args) -> bool:
    """
    Re-run the current script with admin privileges.
    
    Args:
        script_path: Path to the script to run
        *args: Additional arguments
        
    Returns:
        True if elevation was successful
    """
    try:
        params = ' '.join([f'"{arg}"' for arg in args])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script_path}" {params}', None, 1
        )
        return True
    except Exception as e:
        print(f"Failed to elevate privileges: {e}")
        return False


def create_protected_directory(path: Path) -> bool:
    """
    Create a directory with admin-only write access.
    
    Args:
        path: Path to create
        
    Returns:
        True if successful
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        
        # Use icacls to set permissions (admin only)
        # Remove inherited permissions and grant full control to Administrators
        subprocess.run([
            'icacls', str(path),
            '/inheritance:r',  # Remove inherited permissions
            '/grant:r', 'Administrators:(OI)(CI)F',  # Full control for admins
            '/grant:r', 'SYSTEM:(OI)(CI)F',  # Full control for SYSTEM
            '/grant:r', 'Users:(OI)(CI)RX'  # Read/Execute for users
        ], check=True, capture_output=True)
        
        return True
    except Exception as e:
        print(f"Failed to create protected directory: {e}")
        return False


def add_to_startup(exe_path: Path, name: str = "FocusGuardMonitor") -> bool:
    """
    Add the application to Windows startup.
    
    Args:
        exe_path: Path to the executable
        name: Name for the startup entry
        
    Returns:
        True if successful
    """
    try:
        # Use HKLM for all users (requires admin)
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, 
                           winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(exe_path))
        
        return True
    except Exception as e:
        print(f"Failed to add to startup: {e}")
        return False


def remove_from_startup(name: str = "FocusGuardMonitor") -> bool:
    """
    Remove the application from Windows startup.
    
    Args:
        name: Name of the startup entry
        
    Returns:
        True if successful
    """
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0,
                           winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.DeleteValue(key, name)
        
        return True
    except FileNotFoundError:
        return True  # Already removed
    except Exception as e:
        print(f"Failed to remove from startup: {e}")
        return False


def install_service(exe_path: Path) -> Tuple[bool, str]:
    """
    Install the Focus Guard Windows service.
    
    Args:
        exe_path: Path to the service executable
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Use sc.exe to create the service
        result = subprocess.run([
            'sc', 'create', 'FocusGuardMonitor',
            'binPath=', str(exe_path),
            'DisplayName=', 'Focus Guard Activity Monitor',
            'start=', 'auto',
            'obj=', 'LocalSystem'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Set service description
            subprocess.run([
                'sc', 'description', 'FocusGuardMonitor',
                'Monitors application usage and sends activity reports to parents/administrators.'
            ], capture_output=True)
            
            return True, "Service installed successfully"
        else:
            return False, f"Failed to install service: {result.stderr}"
            
    except Exception as e:
        return False, f"Error installing service: {e}"


def uninstall_service() -> Tuple[bool, str]:
    """
    Uninstall the Focus Guard Windows service.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Stop the service first
        subprocess.run(['sc', 'stop', 'FocusGuardMonitor'], capture_output=True)
        
        # Delete the service
        result = subprocess.run(['sc', 'delete', 'FocusGuardMonitor'], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, "Service uninstalled successfully"
        else:
            return False, f"Failed to uninstall service: {result.stderr}"
            
    except Exception as e:
        return False, f"Error uninstalling service: {e}"


def start_service() -> Tuple[bool, str]:
    """Start the Focus Guard service."""
    try:
        result = subprocess.run(['sc', 'start', 'FocusGuardMonitor'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            return True, "Service started"
        else:
            return False, f"Failed to start service: {result.stderr}"
    except Exception as e:
        return False, f"Error starting service: {e}"


def stop_service() -> Tuple[bool, str]:
    """Stop the Focus Guard service."""
    try:
        result = subprocess.run(['sc', 'stop', 'FocusGuardMonitor'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            return True, "Service stopped"
        else:
            return False, f"Failed to stop service: {result.stderr}"
    except Exception as e:
        return False, f"Error stopping service: {e}"


class FocusGuardInstaller:
    """
    Installer for Focus Guard Activity Monitor.
    
    Handles:
    - Creating protected directories
    - Installing as Windows service or startup program
    - Configuring email and reporting settings
    - Setting up log file protection
    """
    
    def __init__(self, config: Optional[DeploymentConfig] = None):
        """
        Initialize the installer.
        
        Args:
            config: Deployment configuration, or None to create default
        """
        self.config = config or create_default_config()
        
        # Installation paths
        self.install_dir = Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'FocusGuard'
        self.data_dir = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / 'FocusGuard'
    
    def check_prerequisites(self) -> Tuple[bool, list]:
        """
        Check installation prerequisites.
        
        Returns:
            Tuple of (all_ok, list of issues)
        """
        issues = []
        
        if not is_admin():
            issues.append("Administrator privileges required")
        
        if sys.platform != 'win32':
            issues.append("Windows operating system required")
        
        return len(issues) == 0, issues
    
    def install(self, 
                exe_path: Optional[Path] = None,
                as_service: bool = True,
                create_shortcut: bool = False) -> Tuple[bool, str]:
        """
        Perform the installation.
        
        Args:
            exe_path: Path to the executable to install
            as_service: Install as Windows service
            create_shortcut: Create desktop shortcut for config UI
            
        Returns:
            Tuple of (success, message)
        """
        if not is_admin():
            return False, "Administrator privileges required. Please run as administrator."
        
        try:
            print("Installing Focus Guard Activity Monitor...")
            
            # Step 1: Create protected directories
            print("  Creating protected directories...")
            if not create_protected_directory(self.data_dir):
                return False, "Failed to create data directory"
            
            if not create_protected_directory(self.data_dir / 'logs'):
                return False, "Failed to create logs directory"
            
            if not create_protected_directory(self.data_dir / 'backups'):
                return False, "Failed to create backups directory"
            
            # Step 2: Copy executable if provided
            if exe_path and exe_path.exists():
                print("  Copying executable...")
                self.install_dir.mkdir(parents=True, exist_ok=True)
                dest_exe = self.install_dir / exe_path.name
                shutil.copy2(exe_path, dest_exe)
                exe_path = dest_exe
            
            # Step 3: Save configuration
            print("  Saving configuration...")
            self.config.storage.data_directory = str(self.data_dir)
            config_path = self.data_dir / 'deployment_config.json'
            self.config.save(config_path)
            
            # Step 4: Install as service or startup
            if as_service and exe_path:
                print("  Installing Windows service...")
                success, msg = install_service(exe_path)
                if not success:
                    # Fall back to startup entry
                    print(f"  Service installation failed: {msg}")
                    print("  Adding to startup instead...")
                    add_to_startup(exe_path)
            elif exe_path:
                print("  Adding to startup...")
                add_to_startup(exe_path)
            
            # Step 5: Apply hardening measures
            if as_service and exe_path:
                print("  Applying security hardening...")
                from focus_guard.deployment.hardening import (
                    configure_service_recovery,
                    configure_service_permissions,
                    create_scheduled_task_backup,
                    protect_executable,
                    SECURITY_RECOMMENDATIONS
                )
                
                # Configure auto-restart on failure
                success, msg = configure_service_recovery()
                print(f"    Service recovery: {msg}")
                
                # Restrict who can stop the service
                success, msg = configure_service_permissions()
                print(f"    Service permissions: {msg}")
                
                # Create backup scheduled task
                success, msg = create_scheduled_task_backup(exe_path)
                print(f"    Backup task: {msg}")
                
                # Protect the executable
                success, msg = protect_executable(exe_path)
                print(f"    Executable protection: {msg}")
            
            # Step 6: Start the service/application
            if as_service:
                print("  Starting service...")
                start_service()
            
            print("\nInstallation complete!")
            print(f"  Data directory: {self.data_dir}")
            print(f"  Config file: {config_path}")
            
            # Print security recommendations
            if as_service:
                from focus_guard.deployment.hardening import SECURITY_RECOMMENDATIONS
                print(SECURITY_RECOMMENDATIONS)
            
            return True, "Installation successful"
            
        except Exception as e:
            return False, f"Installation failed: {e}"
    
    def uninstall(self, remove_data: bool = False) -> Tuple[bool, str]:
        """
        Uninstall Focus Guard.
        
        Args:
            remove_data: Also remove log files and database
            
        Returns:
            Tuple of (success, message)
        """
        if not is_admin():
            return False, "Administrator privileges required"
        
        try:
            print("Uninstalling Focus Guard Activity Monitor...")
            
            # Stop and remove service
            print("  Stopping service...")
            stop_service()
            
            print("  Removing service...")
            uninstall_service()
            
            # Remove from startup
            print("  Removing from startup...")
            remove_from_startup()
            
            # Remove installation directory
            if self.install_dir.exists():
                print("  Removing installation files...")
                shutil.rmtree(self.install_dir, ignore_errors=True)
            
            # Optionally remove data
            if remove_data and self.data_dir.exists():
                print("  Removing data files...")
                shutil.rmtree(self.data_dir, ignore_errors=True)
            
            print("\nUninstallation complete!")
            return True, "Uninstallation successful"
            
        except Exception as e:
            return False, f"Uninstallation failed: {e}"
    
    def update_config(self, new_config: DeploymentConfig) -> bool:
        """
        Update the deployment configuration.
        
        Args:
            new_config: New configuration to save
            
        Returns:
            True if successful
        """
        self.config = new_config
        config_path = self.data_dir / 'deployment_config.json'
        return self.config.save(config_path)


def main():
    """Main entry point for the installer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Focus Guard Installer")
    parser.add_argument('action', choices=['install', 'uninstall', 'start', 'stop', 'status'],
                       help="Action to perform")
    parser.add_argument('--exe', type=str, help="Path to executable")
    parser.add_argument('--remove-data', action='store_true', 
                       help="Remove data files during uninstall")
    parser.add_argument('--no-service', action='store_true',
                       help="Install as startup program instead of service")
    
    args = parser.parse_args()
    
    if args.action == 'install':
        if not is_admin():
            print("This installer requires administrator privileges.")
            print("Please run as administrator.")
            sys.exit(1)
        
        installer = FocusGuardInstaller()
        exe_path = Path(args.exe) if args.exe else None
        success, msg = installer.install(
            exe_path=exe_path,
            as_service=not args.no_service
        )
        print(msg)
        sys.exit(0 if success else 1)
        
    elif args.action == 'uninstall':
        if not is_admin():
            print("Uninstallation requires administrator privileges.")
            sys.exit(1)
        
        installer = FocusGuardInstaller()
        success, msg = installer.uninstall(remove_data=args.remove_data)
        print(msg)
        sys.exit(0 if success else 1)
        
    elif args.action == 'start':
        success, msg = start_service()
        print(msg)
        sys.exit(0 if success else 1)
        
    elif args.action == 'stop':
        success, msg = stop_service()
        print(msg)
        sys.exit(0 if success else 1)
        
    elif args.action == 'status':
        result = subprocess.run(['sc', 'query', 'FocusGuardMonitor'],
                               capture_output=True, text=True)
        print(result.stdout if result.returncode == 0 else "Service not installed")


if __name__ == '__main__':
    main()
