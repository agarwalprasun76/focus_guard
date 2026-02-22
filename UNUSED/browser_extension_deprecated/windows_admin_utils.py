"""
Windows admin utilities for browser extension protection.

This module provides Windows-specific administrative functions for:
- File and directory protection
- Registry operations
- Admin privilege management
- Extension file security
"""

import logging
import os
import sys
import platform
import subprocess
import ctypes
import winreg
from pathlib import Path
from typing import Optional, List, Dict, Any
from ctypes import wintypes

logger = logging.getLogger(__name__)


class WindowsAdminUtils:
    """Windows administrative utilities for extension protection."""
    
    @staticmethod
    def is_admin() -> bool:
        """Check if the current process has administrator privileges."""
        if platform.system() != "Windows":
            return False
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    @staticmethod
    def run_as_admin(command: List[str], wait: bool = True) -> bool:
        """Run a command with administrator privileges.
        
        Args:
            command: Command and arguments to run
            wait: Whether to wait for command completion
            
        Returns:
            bool: True if command was executed successfully
        """
        try:
            if wait:
                result = subprocess.run(
                    ["powershell", "-Command", f"Start-Process -FilePath '{command[0]}' -ArgumentList '{' '.join(command[1:])}' -Verb RunAs -Wait"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.returncode == 0
            else:
                subprocess.Popen(
                    ["powershell", "-Command", f"Start-Process -FilePath '{command[0]}' -ArgumentList '{' '.join(command[1:])}' -Verb RunAs"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                return True
        except Exception as e:
            logger.error(f"Failed to run command as admin: {e}")
            return False
    
    @staticmethod
    def protect_directory_advanced(directory_path: str, deny_delete: bool = True, deny_modify: bool = False) -> bool:
        """Apply advanced Windows protection to a directory.
        
        Args:
            directory_path: Path to directory to protect
            deny_delete: Whether to deny delete operations for non-admin users
            deny_modify: Whether to deny modify operations for non-admin users
            
        Returns:
            bool: True if protection was applied successfully
        """
        if platform.system() != "Windows":
            logger.warning("Windows protection only available on Windows")
            return False
        
        if not os.path.exists(directory_path):
            logger.error(f"Directory does not exist: {directory_path}")
            return False
        
        try:
            # Build icacls command
            cmd = ["icacls", directory_path]
            
            # Grant full control to administrators
            cmd.extend(["/grant", "Administrators:(OI)(CI)F"])
            
            # Grant read/execute to users, but deny delete/modify as specified
            if deny_delete and deny_modify:
                cmd.extend(["/deny", "Users:(OI)(CI)D,W,DC,WD,AD,WA"])
            elif deny_delete:
                cmd.extend(["/deny", "Users:(OI)(CI)D,DC,WD,AD"])
            elif deny_modify:
                cmd.extend(["/deny", "Users:(OI)(CI)W,WA"])
            
            # Remove inheritance to ensure our permissions take precedence
            cmd.extend(["/inheritance:r"])
            
            # Execute the command
            if WindowsAdminUtils.is_admin():
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            else:
                # Run with admin privileges
                return WindowsAdminUtils.run_as_admin(cmd)
            
            logger.info(f"Applied Windows protection to directory: {directory_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to protect directory {directory_path}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error protecting directory {directory_path}: {e}")
            return False
    
    @staticmethod
    def create_registry_protection(extension_path: str) -> bool:
        """Create registry entries to track and protect extension installation.
        
        Args:
            extension_path: Path to the extension directory
            
        Returns:
            bool: True if registry protection was created
        """
        if platform.system() != "Windows":
            return False
        
        try:
            # Create registry key for Focus Guard extension tracking
            registry_key = r"SOFTWARE\FocusGuard\ExtensionProtection"
            
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, registry_key) as key:
                # Store extension path
                winreg.SetValueEx(key, "ExtensionPath", 0, winreg.REG_SZ, extension_path)
                
                # Store protection timestamp
                import time
                winreg.SetValueEx(key, "ProtectionApplied", 0, winreg.REG_SZ, str(int(time.time())))
                
                # Store protection level
                winreg.SetValueEx(key, "ProtectionLevel", 0, winreg.REG_SZ, "AdminProtected")
            
            logger.info("Created registry protection entries")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create registry protection: {e}")
            return False
    
    @staticmethod
    def verify_registry_protection(extension_path: str) -> bool:
        """Verify registry protection entries exist and are valid.
        
        Args:
            extension_path: Path to the extension directory
            
        Returns:
            bool: True if registry protection is valid
        """
        if platform.system() != "Windows":
            return False
        
        try:
            registry_key = r"SOFTWARE\FocusGuard\ExtensionProtection"
            
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_key) as key:
                stored_path = winreg.QueryValueEx(key, "ExtensionPath")[0]
                protection_level = winreg.QueryValueEx(key, "ProtectionLevel")[0]
                
                return (stored_path == extension_path and 
                        protection_level == "AdminProtected")
                        
        except FileNotFoundError:
            logger.warning("Registry protection entries not found")
            return False
        except Exception as e:
            logger.error(f"Error verifying registry protection: {e}")
            return False
    
    @staticmethod
    def remove_registry_protection() -> bool:
        """Remove registry protection entries (for uninstallation).
        
        Returns:
            bool: True if registry entries were removed
        """
        if platform.system() != "Windows":
            return False
        
        try:
            registry_key = r"SOFTWARE\FocusGuard\ExtensionProtection"
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, registry_key)
            logger.info("Removed registry protection entries")
            return True
        except FileNotFoundError:
            logger.info("Registry protection entries already removed")
            return True
        except Exception as e:
            logger.error(f"Failed to remove registry protection: {e}")
            return False
    
    @staticmethod
    def backup_extension_directory(extension_path: str, backup_path: str = None) -> Optional[str]:
        """Create a backup of the extension directory.
        
        Args:
            extension_path: Path to extension directory to backup
            backup_path: Optional custom backup path
            
        Returns:
            Optional[str]: Path to backup directory if successful
        """
        import shutil
        
        if not os.path.exists(extension_path):
            logger.error(f"Extension directory not found: {extension_path}")
            return None
        
        try:
            if backup_path is None:
                # Create backup in temp directory
                import tempfile
                temp_dir = tempfile.gettempdir()
                backup_path = os.path.join(temp_dir, "focus_guard_extension_backup")
            
            # Remove existing backup if it exists
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            
            # Create backup
            shutil.copytree(extension_path, backup_path)
            logger.info(f"Created extension backup at: {backup_path}")
            
            # Protect the backup as well
            if platform.system() == "Windows":
                WindowsAdminUtils.protect_directory_advanced(backup_path, deny_delete=True)
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create extension backup: {e}")
            return None
    
    @staticmethod
    def restore_extension_from_backup(backup_path: str, extension_path: str) -> bool:
        """Restore extension directory from backup.
        
        Args:
            backup_path: Path to backup directory
            extension_path: Path where extension should be restored
            
        Returns:
            bool: True if restoration was successful
        """
        import shutil
        
        if not os.path.exists(backup_path):
            logger.error(f"Backup directory not found: {backup_path}")
            return False
        
        try:
            # Remove existing extension directory if it exists
            if os.path.exists(extension_path):
                shutil.rmtree(extension_path)
            
            # Restore from backup
            shutil.copytree(backup_path, extension_path)
            logger.info(f"Restored extension from backup: {backup_path} -> {extension_path}")
            
            # Reapply protection
            if platform.system() == "Windows":
                WindowsAdminUtils.protect_directory_advanced(extension_path, deny_delete=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore extension from backup: {e}")
            return False
    
    @staticmethod
    def check_file_permissions(file_path: str) -> Dict[str, Any]:
        """Check the current file permissions for a file or directory.
        
        Args:
            file_path: Path to file or directory to check
            
        Returns:
            Dict[str, Any]: Permission information
        """
        if platform.system() != "Windows":
            return {"error": "Windows-only function"}
        
        if not os.path.exists(file_path):
            return {"error": f"Path does not exist: {file_path}"}
        
        try:
            # Use icacls to get current permissions
            result = subprocess.run(
                ["icacls", file_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "path": file_path,
                "permissions": result.stdout.strip(),
                "protected": "Users:(D)" in result.stdout or "Users:(OI)(CI)D" in result.stdout
            }
            
        except Exception as e:
            return {"error": f"Failed to check permissions: {e}"}


class ExtensionProtectionManager:
    """Manager for comprehensive extension protection."""
    
    def __init__(self, extension_path: str):
        """Initialize protection manager.
        
        Args:
            extension_path: Path to extension directory
        """
        self.extension_path = extension_path
        self.admin_utils = WindowsAdminUtils()
        self.backup_path = None
    
    def apply_full_protection(self) -> Dict[str, bool]:
        """Apply comprehensive protection to extension files.
        
        Returns:
            Dict[str, bool]: Protection results
        """
        results = {
            "directory_protection": False,
            "registry_protection": False,
            "backup_created": False,
            "admin_privileges": self.admin_utils.is_admin()
        }
        
        if platform.system() != "Windows":
            logger.info("Full protection only available on Windows")
            return results
        
        # Create backup first
        self.backup_path = self.admin_utils.backup_extension_directory(self.extension_path)
        results["backup_created"] = self.backup_path is not None
        
        # Apply directory protection
        results["directory_protection"] = self.admin_utils.protect_directory_advanced(
            self.extension_path, deny_delete=True, deny_modify=False
        )
        
        # Create registry protection
        results["registry_protection"] = self.admin_utils.create_registry_protection(self.extension_path)
        
        return results
    
    def verify_protection(self) -> Dict[str, Any]:
        """Verify all protection measures are in place.
        
        Returns:
            Dict[str, Any]: Protection verification results
        """
        results = {
            "directory_exists": os.path.exists(self.extension_path),
            "file_permissions": self.admin_utils.check_file_permissions(self.extension_path),
            "registry_protection": self.admin_utils.verify_registry_protection(self.extension_path),
            "backup_exists": self.backup_path and os.path.exists(self.backup_path)
        }
        
        return results
    
    def repair_protection(self) -> bool:
        """Repair any broken protection measures.
        
        Returns:
            bool: True if repair was successful
        """
        logger.info("Repairing extension protection")
        
        # Check if extension directory exists
        if not os.path.exists(self.extension_path):
            logger.warning("Extension directory missing - attempting restore from backup")
            if self.backup_path and os.path.exists(self.backup_path):
                return self.admin_utils.restore_extension_from_backup(self.backup_path, self.extension_path)
            else:
                logger.error("No backup available for restoration")
                return False
        
        # Reapply protections
        protection_results = self.apply_full_protection()
        
        success = all([
            protection_results["directory_protection"],
            protection_results["registry_protection"]
        ])
        
        if success:
            logger.info("Extension protection repaired successfully")
        else:
            logger.error("Failed to repair extension protection")
        
        return success
