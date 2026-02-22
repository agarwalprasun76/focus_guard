"""
Robust browser extension installer with retry logic and Windows admin protection.

This module provides enhanced extension installation capabilities with:
- Retry logic for failed installations
- Windows admin-level file protection
- Extension verification and auto-repair
- Installation status tracking
"""

import logging
import os
import shutil
import platform
import subprocess
import time
import json
import stat
import ctypes
import sys
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from focus_guard.core.browser.interfaces import ExtensionManagerInterface
from focus_guard.core.browser.models.browser import BrowserType
from focus_guard.core.browser.extension.manager import BrowserExtensionManager
from focus_guard.core.browser.extension.windows_admin_utils import WindowsAdminUtils
from focus_guard.core.browser.extension.process_manager import TabServerProcessManager, get_tab_server_process_manager

logger = logging.getLogger(__name__)


class InstallationStatus(Enum):
    """Extension installation status."""
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    FAILED = "failed"
    PROTECTED = "protected"


@dataclass
class InstallationResult:
    """Result of an extension installation attempt."""
    success: bool
    status: InstallationStatus
    attempts: int
    error_message: Optional[str] = None
    protection_applied: bool = False


class WindowsFileProtector:
    """Windows-specific file protection utilities."""
    
    @staticmethod
    def is_admin() -> bool:
        """Check if the current process has admin privileges."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    @staticmethod
    def request_admin_privileges():
        """Request admin privileges for the current process."""
        if platform.system() != "Windows":
            return False
            
        try:
            # Re-run the current script with admin privileges
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            return True
        except Exception as e:
            logger.error(f"Failed to request admin privileges: {e}")
            return False
    
    @staticmethod
    def protect_directory(directory_path: str) -> bool:
        """Apply Windows admin-level protection to a directory and its contents."""
        if platform.system() != "Windows":
            logger.warning("Windows file protection only available on Windows")
            return False
            
        if not WindowsFileProtector.is_admin():
            logger.warning("Admin privileges required for file protection")
            return False
            
        try:
            # Use icacls to set permissions - deny delete for non-admin users
            cmd = [
                "icacls", directory_path,
                "/grant", "Administrators:(OI)(CI)F",  # Full control for admins
                "/deny", "Users:(OI)(CI)D",           # Deny delete for regular users
                "/inheritance:r"                       # Remove inheritance
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Applied Windows protection to: {directory_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to protect directory {directory_path}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error protecting directory {directory_path}: {e}")
            return False
    
    @staticmethod
    def protect_file(file_path: str) -> bool:
        """Apply Windows admin-level protection to a specific file."""
        if platform.system() != "Windows":
            return False
            
        if not WindowsFileProtector.is_admin():
            return False
            
        try:
            # Use icacls to set file permissions
            cmd = [
                "icacls", file_path,
                "/grant", "Administrators:F",  # Full control for admins
                "/deny", "Users:D",            # Deny delete for regular users
                "/inheritance:r"               # Remove inheritance
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Applied Windows protection to file: {file_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to protect file {file_path}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error protecting file {file_path}: {e}")
            return False


class RobustExtensionInstaller(BrowserExtensionManager):
    """Enhanced extension installer with retry logic and protection."""
    
    def __init__(self, extension_dir: str = None, tab_server_url: str = "http://localhost:5000",
                 max_retries: int = 3, retry_delay: float = 2.0):
        """Initialize the robust extension installer.
        
        Args:
            extension_dir: Directory containing extension files
            tab_server_url: URL of the tab server
            max_retries: Maximum number of installation retry attempts
            retry_delay: Delay between retry attempts in seconds
        """
        super().__init__(extension_dir, tab_server_url)
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._installation_status: Dict[BrowserType, InstallationStatus] = {}
        self._file_protector = WindowsFileProtector()
        self._extension_manager = self  # Reference to self for compatibility
        
        # Apply protection to extension directory on initialization
        self._apply_extension_protection()
    
    def _apply_extension_protection(self) -> bool:
        """Apply Windows admin-level protection to extension files."""
        if platform.system() != "Windows":
            logger.info("File protection only available on Windows")
            return True
            
        if not os.path.exists(self._extension_dir):
            logger.warning(f"Extension directory not found: {self._extension_dir}")
            return False
        
        # Check admin privileges first
        if not self._file_protector.is_admin():
            logger.info("Not running as admin - skipping file protection")
            return False
        
        # Apply protection to the entire extension directory
        protection_applied = self._file_protector.protect_directory(self._extension_dir)
        
        if protection_applied:
            logger.info("Windows admin-level protection applied to extension directory")
        else:
            logger.warning("Failed to apply Windows protection - extension files may be vulnerable")
            
        return protection_applied
    
    def _install_extension_properly(self, browser_type: BrowserType) -> bool:
        """Actually install extension for a specific browser.
        
        Args:
            browser_type: The browser type to install for
            
        Returns:
            bool: True if installation succeeded
        """
        try:
            # Ensure tab server is running first
            if not self.ensure_tab_server_running():
                logger.error("Tab server is not running - cannot install extension")
                return False
            
            # Use the extension manager to install
            success = self._extension_manager.install_extension(browser_type)
            
            if not success:
                logger.warning(f"Extension manager failed to install for {browser_type}")
                # Try alternative installation method
                return self._try_alternative_installation(browser_type)
            
            return success
            
        except Exception as e:
            logger.error(f"Exception during extension installation for {browser_type}: {e}")
            return False
    
    def _try_alternative_installation(self, browser_type: BrowserType) -> bool:
        """Try alternative installation method when primary fails.
        
        Args:
            browser_type: The browser type to install for
            
        Returns:
            bool: True if alternative installation succeeded
        """
        try:
            logger.info(f"Trying alternative installation for {browser_type}")
            
            # For Chrome/Edge, try copying extension to browser extensions directory
            if browser_type in [BrowserType.CHROME, BrowserType.EDGE]:
                return self._install_via_directory_copy(browser_type)
            
            # For other browsers, fall back to user guide
            logger.info(f"No alternative installation available for {browser_type}")
            return False
            
        except Exception as e:
            logger.error(f"Alternative installation failed for {browser_type}: {e}")
            return False
    
    def _install_via_directory_copy(self, browser_type: BrowserType) -> bool:
        """Install extension by copying to browser extensions directory.
        
        Args:
            browser_type: The browser type to install for
            
        Returns:
            bool: True if copy installation succeeded
        """
        try:
            import shutil
            
            # Get browser extensions directory
            extensions_dir = self._get_browser_extensions_dir(browser_type)
            if not extensions_dir or not os.path.exists(extensions_dir):
                logger.error(f"Browser extensions directory not found for {browser_type}")
                return False
            
            # Create extension directory in browser
            extension_name = "focus_guard_extension"
            target_dir = os.path.join(extensions_dir, extension_name)
            
            # Remove existing if present
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            
            # Copy extension files
            shutil.copytree(self._extension_dir, target_dir)
            logger.info(f"Extension copied to {target_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"Directory copy installation failed: {e}")
            return False
    
    def _get_browser_extensions_dir(self, browser_type: BrowserType) -> str:
        """Get the extensions directory for a browser.
        
        Args:
            browser_type: The browser type
            
        Returns:
            str: Path to extensions directory or empty string if not found
        """
        import os
        
        user_profile = os.path.expanduser("~")
        
        if browser_type == BrowserType.CHROME:
            return os.path.join(user_profile, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Extensions")
        elif browser_type == BrowserType.EDGE:
            return os.path.join(user_profile, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Extensions")
        
        return ""
    
    def install_extension_robust(self, browser_type: BrowserType) -> InstallationResult:
        """Install extension with retry logic and verification.
        
        Args:
            browser_type: Type of browser to install for
            
        Returns:
            InstallationResult: Detailed installation result
        """
        logger.info(f"Starting robust installation for {browser_type}")
        self._installation_status[browser_type] = InstallationStatus.INSTALLING
        
        last_error = None
        
        for attempt in range(1, self._max_retries + 1):
            logger.info(f"Installation attempt {attempt}/{self._max_retries} for {browser_type}")
            
            try:
                # Check if already installed
                if self.is_extension_installed(browser_type):
                    logger.info(f"Extension already installed for {browser_type}")
                    self._installation_status[browser_type] = InstallationStatus.INSTALLED
                    return InstallationResult(
                        success=True,
                        status=InstallationStatus.INSTALLED,
                        attempts=attempt,
                        protection_applied=True
                    )
                
                # Attempt installation - this is the core issue
                logger.info(f"Attempting to install extension for {browser_type}")
                
                # The current _install_extension method only launches browsers, doesn't actually install
                # We need to implement proper installation logic here
                success = self._install_extension_properly(browser_type)
                
                if success:
                    # Verify installation
                    if self._verify_installation(browser_type):
                        logger.info(f"Extension successfully installed and verified for {browser_type}")
                        self._installation_status[browser_type] = InstallationStatus.INSTALLED
                        return InstallationResult(
                            success=True,
                            status=InstallationStatus.INSTALLED,
                            attempts=attempt,
                            protection_applied=True
                        )
                    else:
                        logger.warning(f"Installation succeeded but verification failed for {browser_type}")
                        last_error = "Installation verification failed"
                else:
                    last_error = f"Installation failed for {browser_type}"
                    logger.warning(last_error)
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Installation attempt {attempt} failed for {browser_type}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self._max_retries:
                logger.info(f"Waiting {self._retry_delay} seconds before retry...")
                time.sleep(self._retry_delay)
        
        # All attempts failed
        logger.error(f"All installation attempts failed for {browser_type}")
        self._installation_status[browser_type] = InstallationStatus.FAILED
        return InstallationResult(
            success=False,
            status=InstallationStatus.FAILED,
            attempts=self._max_retries,
            error_message=last_error,
            protection_applied=False
        )
    
    def _verify_installation(self, browser_type: BrowserType, timeout_seconds: int = 10) -> bool:
        """Verify that the extension was installed successfully.
        
        Args:
            browser_type: Type of browser to verify
            timeout_seconds: Timeout for verification
            
        Returns:
            bool: True if installation is verified
        """
        logger.info(f"Verifying installation for {browser_type}")
        
        # Give the browser time to process the extension
        time.sleep(2)
        
        # Check if extension is now detected as installed
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            # Clear cache and check again
            if browser_type in self._installed_extensions:
                del self._installed_extensions[browser_type]
                
            if self.is_extension_installed(browser_type):
                logger.info(f"Installation verified for {browser_type}")
                return True
                
            time.sleep(1)
        
        logger.warning(f"Installation verification timed out for {browser_type}")
        return False
    
    def ensure_tab_server_running(self, port: int = 5000) -> bool:
        """Ensure that the tab server is running.
        
        Args:
            port: Port to run the tab server on
            
        Returns:
            bool: True if the tab server is running
        """
        try:
            logger.info("Starting tab server...")
            # Get or create process manager
            process_manager = get_tab_server_process_manager()
            
            # Check if already running
            if process_manager.is_running():
                logger.info("Tab server is already running")
                return True
            
            # Start the tab server (no port parameter needed)
            success = process_manager.start()
            
            if success:
                logger.info("Tab server started successfully")
                # Give it a moment to fully start
                import time
                time.sleep(1)
                return True
            else:
                logger.error("Failed to start tab server")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring tab server is running: {e}")
            return False

    def install_for_detected_browsers_robust(self) -> Dict[BrowserType, InstallationResult]:
        """Install extensions for all detected browsers with robust retry logic.
        
        Returns:
            Dict[BrowserType, InstallationResult]: Installation results per browser
        """
        logger.info("Starting robust installation for all detected browsers")
        
        # Ensure tab server is running
        if not self.ensure_tab_server_running():
            logger.error("Cannot install extensions: Tab server is not running")
            return {}
        
        results = {}
        
        # Get all browser types that have detected paths
        for browser_type in self._browser_paths.keys():
            logger.info(f"Installing extension for detected browser: {browser_type}")
            result = self.install_extension_robust(browser_type)
            results[browser_type] = result
            
            # Log result
            if result.success:
                logger.info(f"✅ {browser_type}: Installed successfully in {result.attempts} attempts")
            else:
                logger.error(f"❌ {browser_type}: Failed after {result.attempts} attempts - {result.error_message}")
        
        return results
    
    def auto_repair_extension(self, browser_type: BrowserType) -> bool:
        """Automatically repair a broken or missing extension installation.
        
        Args:
            browser_type: Type of browser to repair
            
        Returns:
            bool: True if repair was successful
        """
        logger.info(f"Starting auto-repair for {browser_type}")
        
        # Check current status
        if self.is_extension_installed(browser_type):
            # Try to verify connection
            if self.verify_extension_connection(browser_type, timeout_seconds=10):
                logger.info(f"Extension for {browser_type} is working correctly")
                return True
            else:
                logger.warning(f"Extension installed but not connecting for {browser_type}")
        
        # Extension is missing or broken - attempt repair
        logger.info(f"Attempting to repair extension for {browser_type}")
        
        # Clear cached status
        if browser_type in self._installed_extensions:
            del self._installed_extensions[browser_type]
        
        # Attempt robust installation
        result = self.install_extension_robust(browser_type)
        
        if result.success:
            logger.info(f"Auto-repair successful for {browser_type}")
            return True
        else:
            logger.error(f"Auto-repair failed for {browser_type}: {result.error_message}")
            return False
    
    def get_installation_status(self, browser_type: BrowserType) -> InstallationStatus:
        """Get the current installation status for a browser.
        
        Args:
            browser_type: Type of browser to check
            
        Returns:
            InstallationStatus: Current status
        """
        return self._installation_status.get(browser_type, InstallationStatus.NOT_INSTALLED)
    
    def get_installation_summary(self) -> Dict[str, Any]:
        """Get a summary of installation status for all browsers.
        
        Returns:
            Dict[str, Any]: Installation summary
        """
        summary = {
            "total_browsers": len(self._browser_paths),
            "installed_count": 0,
            "failed_count": 0,
            "protection_applied": platform.system() == "Windows" and self._file_protector.is_admin(),
            "browsers": {}
        }
        
        for browser_type in self._browser_paths.keys():
            status = self.get_installation_status(browser_type)
            is_installed = self.is_extension_installed(browser_type)
            
            summary["browsers"][browser_type.name] = {
                "status": status.value,
                "installed": is_installed,
                "path": self._browser_paths.get(browser_type, "")
            }
            
            if is_installed:
                summary["installed_count"] += 1
            elif status == InstallationStatus.FAILED:
                summary["failed_count"] += 1
        
        return summary
    
    def ensure_extension_integrity(self) -> bool:
        """Ensure extension files are intact and protected.
        
        Returns:
            bool: True if integrity is ensured
        """
        logger.info("Checking extension integrity")
        
        # Check if extension directory exists
        if not os.path.exists(self._extension_dir):
            logger.error(f"Extension directory missing: {self._extension_dir}")
            return False
        
        # Check critical files
        critical_files = ["manifest.json", "background.js"]
        for file_name in critical_files:
            file_path = os.path.join(self._extension_dir, file_name)
            if not os.path.exists(file_path):
                logger.error(f"Critical extension file missing: {file_path}")
                return False
        
        # Only attempt protection if running as admin
        if platform.system() == "Windows" and self._file_protector.is_admin():
            protection_applied = self._apply_extension_protection()
            if not protection_applied:
                logger.warning("Failed to reapply Windows protection")
        
        logger.info("Extension integrity verified")
        return True
    
    def repair_all_extensions(self) -> Dict[BrowserType, bool]:
        """Repair extensions for all detected browsers.
        
        Returns:
            Dict[BrowserType, bool]: Repair results per browser
        """
        logger.info("Starting auto-repair for all detected browsers")
        
        # First ensure extension integrity
        if not self.ensure_extension_integrity():
            logger.error("Cannot repair extensions: Extension integrity check failed")
            return {}
        
        results = {}
        for browser_type in self._browser_paths.keys():
            results[browser_type] = self.auto_repair_extension(browser_type)
        
        return results


class ExtensionInstallationService:
    """High-level service for managing extension installations."""
    
    def __init__(self, extension_dir: str = None):
        """Initialize the installation service.
        
        Args:
            extension_dir: Directory containing extension files
        """
        self._installer = RobustExtensionInstaller(extension_dir)
        self._installation_log: List[Dict[str, Any]] = []
    
    def install_all_extensions(self) -> Dict[str, Any]:
        """Install extensions for all detected browsers with full robustness.
        
        Returns:
            Dict[str, Any]: Complete installation report
        """
        logger.info("Starting comprehensive extension installation")
        
        # Log installation attempt
        installation_record = {
            "timestamp": time.time(),
            "action": "install_all",
            "results": {}
        }
        
        # Ensure extension integrity first
        if not self._installer.ensure_extension_integrity():
            error_msg = "Extension integrity check failed"
            logger.error(error_msg)
            installation_record["error"] = error_msg
            self._installation_log.append(installation_record)
            return {"success": False, "error": error_msg}
        
        # Install for all detected browsers
        results = self._installer.install_for_detected_browsers_robust()
        installation_record["results"] = {
            browser_type.name: {
                "success": result.success,
                "attempts": result.attempts,
                "status": result.status.value,
                "error": result.error_message
            }
            for browser_type, result in results.items()
        }
        
        self._installation_log.append(installation_record)
        
        # Generate summary
        summary = self._installer.get_installation_summary()
        summary["installation_results"] = results
        summary["timestamp"] = installation_record["timestamp"]
        
        logger.info(f"Installation complete: {summary['installed_count']}/{summary['total_browsers']} browsers")
        return summary
    
    def verify_all_extensions(self) -> Dict[BrowserType, bool]:
        """Verify all installed extensions are working.
        
        Returns:
            Dict[BrowserType, bool]: Verification results per browser
        """
        logger.info("Verifying all extension connections")
        
        results = {}
        for browser_type in self._installer._browser_paths.keys():
            if self._installer.is_extension_installed(browser_type):
                results[browser_type] = self._installer.verify_extension_connection(browser_type)
            else:
                results[browser_type] = False
        
        return results
    
    def get_installation_log(self) -> List[Dict[str, Any]]:
        """Get the installation history log.
        
        Returns:
            List[Dict[str, Any]]: Installation log entries
        """
        return self._installation_log.copy()
    
    def create_installation_report(self) -> str:
        """Create a detailed installation report.
        
        Returns:
            str: Formatted installation report
        """
        summary = self._installer.get_installation_summary()
        
        report = []
        report.append("=== Focus Guard Extension Installation Report ===")
        report.append(f"Total Browsers Detected: {summary['total_browsers']}")
        report.append(f"Successfully Installed: {summary['installed_count']}")
        report.append(f"Failed Installations: {summary['failed_count']}")
        report.append(f"Windows Protection Applied: {summary['protection_applied']}")
        report.append("")
        
        report.append("Browser Details:")
        for browser_name, details in summary["browsers"].items():
            status_icon = "OK" if details["installed"] else "FAIL"
            report.append(f"  {status_icon} {browser_name}: {details['status']}")
            if details["path"]:
                report.append(f"    Path: {details['path']}")
        
        report.append("")
        report.append(f"Extension Directory: {self._installer._extension_dir}")
        
        if self._installation_log:
            report.append("")
            report.append("Recent Installation Attempts:")
            for entry in self._installation_log[-3:]:  # Show last 3 attempts
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["timestamp"]))
                report.append(f"  {timestamp}: {entry['action']}")
        
        return "\n".join(report)


def get_robust_extension_installer(extension_dir: str = None) -> RobustExtensionInstaller:
    """Get a singleton instance of the robust extension installer.
    
    Args:
        extension_dir: Directory containing extension files
        
    Returns:
        RobustExtensionInstaller: Installer instance
    """
    if not hasattr(get_robust_extension_installer, '_instance'):
        get_robust_extension_installer._instance = RobustExtensionInstaller(extension_dir)
    return get_robust_extension_installer._instance


def get_extension_installation_service(extension_dir: str = None) -> ExtensionInstallationService:
    """Get a singleton instance of the extension installation service.
    
    Args:
        extension_dir: Directory containing extension files
        
    Returns:
        ExtensionInstallationService: Service instance
    """
    if not hasattr(get_extension_installation_service, '_instance'):
        get_extension_installation_service._instance = ExtensionInstallationService(extension_dir)
    return get_extension_installation_service._instance
