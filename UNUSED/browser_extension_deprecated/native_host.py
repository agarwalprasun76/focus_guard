"""
Native Messaging Host Manager for browser extensions.

This module provides functionality for setting up, registering, and validating
native messaging hosts for browser extensions.
"""

import os
import sys
import json
import logging
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Constants for native messaging host
NATIVE_HOST_NAME = "com.focusguard.native_host"
NATIVE_HOST_DESCRIPTION = "FocusGuard Native Messaging Host"


class NativeMessagingHostManager:
    """
    Manager for native messaging host setup and validation.
    
    This class provides methods for:
    - Setting up native messaging host manifests for different browsers
    - Registering the native messaging host with the browser
    - Validating the native messaging host installation
    - Troubleshooting common issues
    """
    
    def __init__(self, app_dir: str = None):
        """
        Initialize the NativeMessagingHostManager.
        
        Args:
            app_dir: Directory where the application is installed.
                    If None, the current directory is used.
        """
        self._app_dir = app_dir or os.path.abspath(os.path.dirname(__file__))
        self._os_name = platform.system().lower()
        self._native_host_path = self._get_native_host_path()
        
    def _get_native_host_path(self) -> str:
        """
        Get the path to the native messaging host executable.
        
        Returns:
            str: Path to the native messaging host executable.
        """
        if self._os_name == "windows":
            # On Windows, we use a .bat wrapper or direct .exe
            # Check if .exe exists first, then fall back to .bat
            exe_path = os.path.join(self._app_dir, "focus_guard_native_host.exe")
            bat_path = os.path.join(self._app_dir, "focus_guard_native_host.bat")
            py_path = os.path.join(self._app_dir, "focus_guard_native_host.py")
            
            if os.path.exists(exe_path):
                return exe_path
            elif os.path.exists(bat_path):
                return bat_path
            else:
                return py_path
        else:
            # On Linux/macOS, we use the Python script directly
            return os.path.join(self._app_dir, "focus_guard_native_host.py")
    
    def create_manifest(self, browser: str) -> Dict:
        """
        Create a native messaging host manifest for the specified browser.
        
        Args:
            browser: Browser name ('chrome', 'firefox', 'edge', etc.)
            
        Returns:
            Dict: Manifest data
        """
        allowed_origins = self._get_allowed_origins(browser)
        
        manifest = {
            "name": NATIVE_HOST_NAME,
            "description": NATIVE_HOST_DESCRIPTION,
            "path": self._native_host_path,
            "type": "stdio",
            "allowed_origins": allowed_origins
        }
        
        # Firefox uses different keys
        if browser.lower() == "firefox":
            manifest["allowed_extensions"] = allowed_origins
            del manifest["allowed_origins"]
        
        return manifest
    
    def _get_allowed_origins(self, browser: str) -> List[str]:
        """
        Get the allowed origins for the specified browser.
        
        Args:
            browser: Browser name
            
        Returns:
            List[str]: List of allowed origins
        """
        # Extension IDs for different browsers
        # These should be updated with actual extension IDs when deployed
        if browser.lower() == "chrome":
            return ["chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/"]
        elif browser.lower() == "edge":
            return ["chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/"]
        elif browser.lower() == "firefox":
            return ["focusguard@example.com"]
        else:
            return []
    
    def get_manifest_path(self, browser: str) -> str:
        """
        Get the path where the native messaging host manifest should be installed.
        
        Args:
            browser: Browser name
            
        Returns:
            str: Path to the manifest file
        """
        if self._os_name == "windows":
            if browser.lower() in ["chrome", "edge"]:
                # Chrome and Edge use the registry on Windows
                return ""
            elif browser.lower() == "firefox":
                appdata = os.environ.get("APPDATA", "")
                return os.path.join(appdata, "Mozilla", "NativeMessagingHosts", f"{NATIVE_HOST_NAME}.json")
        elif self._os_name == "darwin":  # macOS
            if browser.lower() in ["chrome", "edge"]:
                return os.path.expanduser(f"~/Library/Application Support/Google/Chrome/NativeMessagingHosts/{NATIVE_HOST_NAME}.json")
            elif browser.lower() == "firefox":
                return os.path.expanduser(f"~/Library/Application Support/Mozilla/NativeMessagingHosts/{NATIVE_HOST_NAME}.json")
        else:  # Linux
            if browser.lower() in ["chrome", "edge"]:
                return os.path.expanduser(f"~/.config/google-chrome/NativeMessagingHosts/{NATIVE_HOST_NAME}.json")
            elif browser.lower() == "firefox":
                return os.path.expanduser(f"~/.mozilla/native-messaging-hosts/{NATIVE_HOST_NAME}.json")
        
        return ""
    
    def install_manifest(self, browser: str) -> bool:
        """
        Install the native messaging host manifest for the specified browser.
        
        Args:
            browser: Browser name
            
        Returns:
            bool: True if installation was successful, False otherwise
        """
        try:
            manifest = self.create_manifest(browser)
            
            if self._os_name == "windows" and browser.lower() in ["chrome", "edge"]:
                # On Windows, Chrome and Edge use the registry
                return self._install_manifest_registry(browser, manifest)
            else:
                # Other browsers use file-based manifests
                manifest_path = self.get_manifest_path(browser)
                if not manifest_path:
                    logger.error(f"Could not determine manifest path for {browser}")
                    return False
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
                
                # Write manifest file
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f, indent=2)
                
                logger.info(f"Installed native messaging host manifest for {browser} at {manifest_path}")
                return True
        except Exception as e:
            logger.error(f"Error installing native messaging host manifest for {browser}: {e}")
            return False
    
    def _install_manifest_registry(self, browser: str, manifest: Dict) -> bool:
        """
        Install the native messaging host manifest in the Windows registry.
        
        Args:
            browser: Browser name
            manifest: Manifest data
            
        Returns:
            bool: True if installation was successful, False otherwise
        """
        try:
            import winreg
            
            # Determine registry key based on browser
            if browser.lower() == "chrome":
                key_path = r"SOFTWARE\Google\Chrome\NativeMessagingHosts"
            elif browser.lower() == "edge":
                key_path = r"SOFTWARE\Microsoft\Edge\NativeMessagingHosts"
            else:
                logger.error(f"Unsupported browser for registry installation: {browser}")
                return False
            
            # Create a temporary manifest file
            temp_manifest_path = os.path.join(
                os.environ.get("TEMP", os.getcwd()),
                f"{NATIVE_HOST_NAME}.json"
            )
            
            with open(temp_manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Create registry key
            registry_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\{NATIVE_HOST_NAME}")
            winreg.SetValueEx(registry_key, "", 0, winreg.REG_SZ, temp_manifest_path)
            winreg.CloseKey(registry_key)
            
            logger.info(f"Installed native messaging host registry key for {browser}")
            return True
        except ImportError:
            logger.error("winreg module not available, cannot install registry key")
            return False
        except Exception as e:
            logger.error(f"Error installing registry key for {browser}: {e}")
            return False
    
    def uninstall_manifest(self, browser: str) -> bool:
        """
        Uninstall the native messaging host manifest for the specified browser.
        
        Args:
            browser: Browser name
            
        Returns:
            bool: True if uninstallation was successful, False otherwise
        """
        try:
            if self._os_name == "windows" and browser.lower() in ["chrome", "edge"]:
                # On Windows, Chrome and Edge use the registry
                return self._uninstall_manifest_registry(browser)
            else:
                # Other browsers use file-based manifests
                manifest_path = self.get_manifest_path(browser)
                if not manifest_path or not os.path.exists(manifest_path):
                    logger.info(f"No manifest found for {browser} at {manifest_path}")
                    return True
                
                # Remove manifest file
                os.remove(manifest_path)
                logger.info(f"Removed native messaging host manifest for {browser} at {manifest_path}")
                return True
        except Exception as e:
            logger.error(f"Error uninstalling native messaging host manifest for {browser}: {e}")
            return False
    
    def _uninstall_manifest_registry(self, browser: str) -> bool:
        """
        Uninstall the native messaging host manifest from the Windows registry.
        
        Args:
            browser: Browser name
            
        Returns:
            bool: True if uninstallation was successful, False otherwise
        """
        try:
            import winreg
            
            # Determine registry key based on browser
            if browser.lower() == "chrome":
                key_path = r"SOFTWARE\Google\Chrome\NativeMessagingHosts"
            elif browser.lower() == "edge":
                key_path = r"SOFTWARE\Microsoft\Edge\NativeMessagingHosts"
            else:
                logger.error(f"Unsupported browser for registry uninstallation: {browser}")
                return False
            
            # Delete registry key
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\{NATIVE_HOST_NAME}")
                logger.info(f"Removed native messaging host registry key for {browser}")
            except FileNotFoundError:
                logger.info(f"No registry key found for {browser}")
            
            return True
        except ImportError:
            logger.error("winreg module not available, cannot uninstall registry key")
            return False
        except Exception as e:
            logger.error(f"Error uninstalling registry key for {browser}: {e}")
            return False
    
    def is_installed(self, browser: str) -> bool:
        """
        Check if the native messaging host is installed for the specified browser.
        
        Args:
            browser: Browser name
            
        Returns:
            bool: True if installed, False otherwise
        """
        try:
            if self._os_name == "windows" and browser.lower() in ["chrome", "edge"]:
                # On Windows, Chrome and Edge use the registry
                return self._is_installed_registry(browser)
            else:
                # Other browsers use file-based manifests
                manifest_path = self.get_manifest_path(browser)
                return manifest_path and os.path.exists(manifest_path)
        except Exception as e:
            logger.error(f"Error checking if native messaging host is installed for {browser}: {e}")
            return False
    
    def _is_installed_registry(self, browser: str) -> bool:
        """
        Check if the native messaging host is installed in the Windows registry.
        
        Args:
            browser: Browser name
            
        Returns:
            bool: True if installed, False otherwise
        """
        try:
            import winreg
            
            # Determine registry key based on browser
            if browser.lower() == "chrome":
                key_path = r"SOFTWARE\Google\Chrome\NativeMessagingHosts"
            elif browser.lower() == "edge":
                key_path = r"SOFTWARE\Microsoft\Edge\NativeMessagingHosts"
            else:
                logger.error(f"Unsupported browser for registry check: {browser}")
                return False
            
            # Check if registry key exists
            try:
                registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\{NATIVE_HOST_NAME}")
                winreg.CloseKey(registry_key)
                return True
            except FileNotFoundError:
                return False
        except ImportError:
            logger.error("winreg module not available, cannot check registry")
            return False
        except Exception as e:
            logger.error(f"Error checking registry key for {browser}: {e}")
            return False
    
    def validate_installation(self, browser: str) -> Tuple[bool, str]:
        """
        Validate the native messaging host installation for the specified browser.
        
        Args:
            browser: Browser name
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        # Check if native host executable exists
        if not os.path.exists(self._native_host_path):
            return False, f"Native host executable not found at {self._native_host_path}"
        
        # Check if manifest is installed
        if not self.is_installed(browser):
            return False, f"Native messaging host manifest not installed for {browser}"
        
        # Check if native host executable has correct permissions
        if self._os_name != "windows":
            if not os.access(self._native_host_path, os.X_OK):
                return False, f"Native host executable is not executable: {self._native_host_path}"
        
        return True, f"Native messaging host is properly installed for {browser}"
    
    def diagnose_issues(self, browser: str) -> List[str]:
        """
        Diagnose common issues with native messaging host setup.
        
        Args:
            browser: Browser name
            
        Returns:
            List[str]: List of issues found
        """
        issues = []
        
        # Check if native host executable exists
        if not os.path.exists(self._native_host_path):
            issues.append(f"Native host executable not found at {self._native_host_path}")
        
        # Check if manifest is installed
        if not self.is_installed(browser):
            issues.append(f"Native messaging host manifest not installed for {browser}")
        
        # Check if native host executable has correct permissions
        if self._os_name != "windows" and os.path.exists(self._native_host_path):
            if not os.access(self._native_host_path, os.X_OK):
                issues.append(f"Native host executable is not executable: {self._native_host_path}")
        
        # Check if browser is running
        if self._is_browser_running(browser):
            issues.append(f"{browser.capitalize()} is currently running. Some changes may require a browser restart.")
        
        return issues
    
    def _is_browser_running(self, browser: str) -> bool:
        """
        Check if the specified browser is currently running.
        
        Args:
            browser: Browser name
            
        Returns:
            bool: True if running, False otherwise
        """
        # Define process names for each browser
        browser_processes = {
            "chrome": ["chrome.exe", "Google Chrome"],
            "edge": ["msedge.exe", "Microsoft Edge"],
            "firefox": ["firefox.exe", "Mozilla Firefox"]
        }
        
        # Get the process names to check for this browser
        process_names = browser_processes.get(browser.lower(), [browser.lower()])
        
        try:
            if self._os_name == "windows":
                import psutil
                for proc in psutil.process_iter(['name']):
                    process_name = proc.info['name'].lower()
                    # Check if any of the browser's process names match
                    if any(p.lower() in process_name for p in process_names):
                        return True
                
                # Alternative method using tasklist
                try:
                    output = subprocess.check_output(["tasklist", "/FO", "CSV"]).decode("utf-8").lower()
                    return any(p.lower() in output for p in process_names)
                except Exception:
                    # Fall back to psutil results if tasklist fails
                    pass
                    
            elif self._os_name == "darwin":  # macOS
                for p in process_names:
                    cmd = ["pgrep", "-i", p]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        return True
            else:  # Linux
                for p in process_names:
                    cmd = ["pgrep", "-i", p]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        return True
        except Exception as e:
            logger.error(f"Error checking if {browser} is running: {e}")
            return False
        
        return False
    
    def install_for_all_browsers(self) -> Dict[str, bool]:
        """
        Install the native messaging host for all supported browsers.
        
        Returns:
            Dict[str, bool]: Dictionary mapping browser names to installation success
        """
        browsers = ["chrome", "edge", "firefox"]
        results = {}
        
        for browser in browsers:
            results[browser] = self.install_manifest(browser)
        
        return results
    
    def uninstall_for_all_browsers(self) -> Dict[str, bool]:
        """
        Uninstall the native messaging host for all supported browsers.
        
        Returns:
            Dict[str, bool]: Dictionary mapping browser names to uninstallation success
        """
        browsers = ["chrome", "edge", "firefox"]
        results = {}
        
        for browser in browsers:
            results[browser] = self.uninstall_manifest(browser)
        
        return results
    
    def get_installation_status(self) -> Dict[str, bool]:
        """
        Get the installation status for all supported browsers.
        
        Returns:
            Dict[str, bool]: Dictionary mapping browser names to installation status
        """
        browsers = ["chrome", "edge", "firefox"]
        status = {}
        
        for browser in browsers:
            status[browser] = self.is_installed(browser)
        
        return status
    
    def get_native_host_executable(self) -> str:
        """
        Get the path to the native messaging host executable.
        
        Returns:
            str: Path to the native messaging host executable
        """
        return self._native_host_path
