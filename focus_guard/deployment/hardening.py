"""
Service hardening and tamper resistance for Focus Guard.

This module implements multiple layers of protection to prevent
unauthorized stopping or disabling of the activity monitor.

IMPORTANT: These protections are most effective when:
1. The monitored user does NOT have admin privileges
2. The service runs as SYSTEM account
3. Parent controls the admin password
"""

import os
import sys
import ctypes
import subprocess
import logging
import winreg
from pathlib import Path
from typing import Tuple, Optional
from enum import IntEnum

logger = logging.getLogger(__name__)


class ServiceFailureAction(IntEnum):
    """Actions to take when service fails."""
    NONE = 0
    RESTART = 1
    REBOOT = 2
    RUN_COMMAND = 3


def is_admin() -> bool:
    """Check if running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def configure_service_recovery(service_name: str = "FocusGuardMonitor") -> Tuple[bool, str]:
    """
    Configure automatic service recovery on failure.
    
    Sets the service to:
    - Restart after 1st failure (after 1 second)
    - Restart after 2nd failure (after 5 seconds)
    - Restart after subsequent failures (after 30 seconds)
    - Reset failure count after 1 day
    
    Args:
        service_name: Name of the Windows service
        
    Returns:
        Tuple of (success, message)
    """
    if not is_admin():
        return False, "Admin privileges required"
    
    try:
        # sc failure <service> reset= 86400 actions= restart/1000/restart/5000/restart/30000
        result = subprocess.run([
            'sc', 'failure', service_name,
            'reset=', '86400',  # Reset failure count after 1 day (seconds)
            'actions=', 'restart/1000/restart/5000/restart/30000'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Configured service recovery for {service_name}")
            return True, "Service recovery configured"
        else:
            return False, f"Failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Error: {e}"


def configure_service_permissions(service_name: str = "FocusGuardMonitor") -> Tuple[bool, str]:
    """
    Restrict service permissions so standard users cannot stop it.
    
    By default, only Administrators and SYSTEM can control the service.
    This removes any permissions that might allow standard users to stop it.
    
    Args:
        service_name: Name of the Windows service
        
    Returns:
        Tuple of (success, message)
    """
    if not is_admin():
        return False, "Admin privileges required"
    
    try:
        # Get current security descriptor
        # Then set it to only allow Administrators and SYSTEM
        # D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)
        # SY = SYSTEM, BA = Built-in Administrators
        # This denies Interactive users (standard users) from stopping the service
        
        sddl = "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)"
        
        result = subprocess.run([
            'sc', 'sdset', service_name, sddl
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Restricted service permissions for {service_name}")
            return True, "Service permissions restricted - only admins can stop"
        else:
            return False, f"Failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Error: {e}"


def create_scheduled_task_backup(exe_path: Path, task_name: str = "FocusGuardBackup") -> Tuple[bool, str]:
    """
    Create a scheduled task as a backup startup method.
    
    This provides redundancy - if the service is disabled, the scheduled
    task will still start the monitor. The task runs at logon and also
    periodically checks if the main service is running.
    
    Args:
        exe_path: Path to the executable
        task_name: Name for the scheduled task
        
    Returns:
        Tuple of (success, message)
    """
    if not is_admin():
        return False, "Admin privileges required"
    
    try:
        # Create task that runs at logon
        result = subprocess.run([
            'schtasks', '/create',
            '/tn', task_name,
            '/tr', f'"{exe_path}" run',
            '/sc', 'onlogon',
            '/ru', 'SYSTEM',
            '/rl', 'HIGHEST',
            '/f'  # Force overwrite if exists
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Also create a periodic check task
            subprocess.run([
                'schtasks', '/create',
                '/tn', f'{task_name}Check',
                '/tr', f'"{exe_path}" run',
                '/sc', 'minute',
                '/mo', '5',  # Every 5 minutes
                '/ru', 'SYSTEM',
                '/rl', 'HIGHEST',
                '/f'
            ], capture_output=True, text=True)
            
            logger.info(f"Created backup scheduled tasks")
            return True, "Backup scheduled tasks created"
        else:
            return False, f"Failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Error: {e}"


def protect_executable(exe_path: Path) -> Tuple[bool, str]:
    """
    Set file permissions to prevent deletion by standard users.
    
    Args:
        exe_path: Path to the executable
        
    Returns:
        Tuple of (success, message)
    """
    if not is_admin():
        return False, "Admin privileges required"
    
    try:
        # Remove inherited permissions, grant only to Administrators and SYSTEM
        result = subprocess.run([
            'icacls', str(exe_path),
            '/inheritance:r',  # Remove inherited permissions
            '/grant:r', 'Administrators:(F)',  # Full control for admins
            '/grant:r', 'SYSTEM:(F)',  # Full control for SYSTEM
            '/grant:r', 'Users:(RX)'  # Read/Execute only for users
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Protected executable: {exe_path}")
            return True, "Executable protected"
        else:
            return False, f"Failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Error: {e}"


def protect_data_directory(data_dir: Path) -> Tuple[bool, str]:
    """
    Set directory permissions to prevent tampering by standard users.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        Tuple of (success, message)
    """
    if not is_admin():
        return False, "Admin privileges required"
    
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        
        result = subprocess.run([
            'icacls', str(data_dir),
            '/inheritance:r',
            '/grant:r', 'Administrators:(OI)(CI)F',  # Full control, inherit
            '/grant:r', 'SYSTEM:(OI)(CI)F',
            '/grant:r', 'Users:(OI)(CI)RX'  # Read/Execute only
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Protected data directory: {data_dir}")
            return True, "Data directory protected"
        else:
            return False, f"Failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Error: {e}"


def hide_from_add_remove_programs(app_name: str = "FocusGuard") -> Tuple[bool, str]:
    """
    Hide the application from Add/Remove Programs (optional).
    
    This is a minor obscurity measure - the app won't appear in the
    standard uninstall list, making it slightly harder to find.
    
    Args:
        app_name: Application name in registry
        
    Returns:
        Tuple of (success, message)
    """
    if not is_admin():
        return False, "Admin privileges required"
    
    try:
        key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{app_name}"
        
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0,
                           winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.SetValueEx(key, "SystemComponent", 0, winreg.REG_DWORD, 1)
        
        return True, "Hidden from Add/Remove Programs"
        
    except FileNotFoundError:
        return False, "Registry key not found"
    except Exception as e:
        return False, f"Error: {e}"


def apply_all_hardening(
    service_name: str = "FocusGuardMonitor",
    exe_path: Optional[Path] = None,
    data_dir: Optional[Path] = None
) -> dict:
    """
    Apply all hardening measures.
    
    Args:
        service_name: Name of the Windows service
        exe_path: Path to the executable (optional)
        data_dir: Path to data directory (optional)
        
    Returns:
        Dictionary of results for each hardening measure
    """
    results = {}
    
    # Service recovery
    success, msg = configure_service_recovery(service_name)
    results['service_recovery'] = {'success': success, 'message': msg}
    
    # Service permissions
    success, msg = configure_service_permissions(service_name)
    results['service_permissions'] = {'success': success, 'message': msg}
    
    # Scheduled task backup
    if exe_path:
        success, msg = create_scheduled_task_backup(exe_path)
        results['scheduled_task'] = {'success': success, 'message': msg}
        
        # Protect executable
        success, msg = protect_executable(exe_path)
        results['exe_protection'] = {'success': success, 'message': msg}
    
    # Protect data directory
    if data_dir:
        success, msg = protect_data_directory(data_dir)
        results['data_protection'] = {'success': success, 'message': msg}
    
    return results


def get_hardening_status(service_name: str = "FocusGuardMonitor") -> dict:
    """
    Check current hardening status.
    
    Returns:
        Dictionary with status of each protection layer
    """
    status = {
        'service_exists': False,
        'service_running': False,
        'recovery_configured': False,
        'permissions_restricted': False,
        'scheduled_task_exists': False
    }
    
    try:
        # Check service exists and is running
        result = subprocess.run(['sc', 'query', service_name],
                               capture_output=True, text=True)
        status['service_exists'] = result.returncode == 0
        status['service_running'] = 'RUNNING' in result.stdout
        
        # Check recovery configuration
        result = subprocess.run(['sc', 'qfailure', service_name],
                               capture_output=True, text=True)
        status['recovery_configured'] = 'RESTART' in result.stdout
        
        # Check scheduled task
        result = subprocess.run(['schtasks', '/query', '/tn', 'FocusGuardBackup'],
                               capture_output=True, text=True)
        status['scheduled_task_exists'] = result.returncode == 0
        
    except Exception as e:
        logger.error(f"Error checking hardening status: {e}")
    
    return status


# Recommendations for maximum protection
SECURITY_RECOMMENDATIONS = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FOCUS GUARD SECURITY RECOMMENDATIONS                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  For MAXIMUM protection, ensure the following:                               ║
║                                                                              ║
║  1. USER ACCOUNT SETUP (MOST IMPORTANT)                                      ║
║     ├─ Create a STANDARD user account for your daughter                     ║
║     ├─ Do NOT give her admin privileges                                     ║
║     └─ Keep the admin password secret                                       ║
║                                                                              ║
║  2. SERVICE CONFIGURATION                                                    ║
║     ├─ Service runs as SYSTEM account (not user)                            ║
║     ├─ Auto-restart on failure enabled                                      ║
║     └─ Service permissions restrict stop to admins only                     ║
║                                                                              ║
║  3. FILE PROTECTION                                                          ║
║     ├─ Executable in protected directory (Program Files)                    ║
║     ├─ Data in C:\\ProgramData\\FocusGuard (admin-only write)                ║
║     └─ Standard users cannot delete or modify                               ║
║                                                                              ║
║  4. REDUNDANCY                                                               ║
║     ├─ Windows Service (primary)                                            ║
║     ├─ Scheduled Task (backup, runs at logon)                               ║
║     └─ Periodic check task (every 5 minutes)                                ║
║                                                                              ║
║  ⚠️  WARNING: If the user has admin access, they CAN disable protection.    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
