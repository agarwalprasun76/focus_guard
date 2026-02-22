"""
Extension manager module.

This module provides functionality for managing browser extensions.
"""

import logging
import os
import shutil
import platform
import subprocess
import time
import webbrowser
import requests
from pathlib import Path
from typing import Dict, Optional, List, Any

from focus_guard.core.browser.interfaces import ExtensionManagerInterface
from focus_guard.core.browser.models.browser import BrowserType
from focus_guard.core.tab_server_endpoint import resolve_tab_server_base_url
try:
    from focus_guard.core.browser.extension.tab_server import get_tab_server
except ImportError:
    def get_tab_server(*a, **kw): return None

try:
    from focus_guard.core.browser.extension.process_manager import get_tab_server_process_manager
except ImportError:
    class _StubPM:
        def is_running(self): return False
        def start(self): return False
        def stop(self): return False
    def get_tab_server_process_manager(*a, **kw): return _StubPM()

logger = logging.getLogger(__name__)


class BrowserExtensionManager(ExtensionManagerInterface):
    """Browser extension manager implementation."""
    
    def __init__(self, extension_dir: str = None, tab_server_url: Optional[str] = None):
        """Initialize the browser extension manager.
        
        Args:
            extension_dir: Directory containing extension files
            tab_server_url: URL of the tab server
        """
        self._extension_dir = extension_dir or self._get_default_extension_dir()
        self._tab_server_url = tab_server_url or resolve_tab_server_base_url()
        self._installed_extensions: Dict[BrowserType, bool] = {}
        
        # Extension IDs are typically derived from the extension's public key
        # For development/unpacked extensions, we use the extension directory path
        self._extension_ids: Dict[BrowserType, str] = {
            BrowserType.CHROME: "focus_guard_chrome_extension",
            BrowserType.FIREFOX: "focus_guard_firefox_extension",
            BrowserType.EDGE: "focus_guard_edge_extension",
            BrowserType.BRAVE: "focus_guard_brave_extension",
            BrowserType.OPERA: "focus_guard_opera_extension",
            BrowserType.SAFARI: "focus_guard_safari_extension",
        }
        
        # Browser executable paths
        self._browser_paths: Dict[BrowserType, str] = {}
        self._detect_browser_paths()
        
        # Process manager for the tab server
        self._process_manager = get_tab_server_process_manager()
        
    def is_extension_installed(self, browser_type: BrowserType) -> bool:
        """Check if the extension is installed for a browser type.
        
        Args:
            browser_type: Type of browser to check
            
        Returns:
            bool: True if the extension is installed
        """
        # Check if we have cached the result
        if browser_type in self._installed_extensions:
            return self._installed_extensions[browser_type]
        
        # Check if the extension is installed
        installed = self._check_extension_installed(browser_type)
        self._installed_extensions[browser_type] = installed
        return installed
    
    def install_extension(self, browser_type: BrowserType) -> bool:
        """Install the extension for a browser type.
        
        Args:
            browser_type: Type of browser to install for
            
        Returns:
            bool: True if the extension was installed successfully
        """
        logger.info(f"Installing extension for browser type: {browser_type}")
        
        # Check if the extension is already installed
        if self.is_extension_installed(browser_type):
            logger.info(f"Extension already installed for {browser_type}")
            return True
        
        # Install the extension
        success = self._install_extension(browser_type)
        if success:
            self._installed_extensions[browser_type] = True
            logger.info(f"Extension installed successfully for {browser_type}")
        else:
            logger.warning(f"Failed to install extension for {browser_type}")
        
        return success
    
    def update_extension(self, browser_type: BrowserType) -> bool:
        """Update the extension for a browser type.
        
        Args:
            browser_type: Type of browser to update for
            
        Returns:
            bool: True if the extension was updated successfully
        """
        logger.info(f"Updating extension for browser type: {browser_type}")
        
        # Check if the extension is installed
        if not self.is_extension_installed(browser_type):
            logger.warning(f"Cannot update extension for {browser_type}: not installed")
            return False
        
        # Update the extension
        success = self._update_extension(browser_type)
        if success:
            logger.info(f"Extension updated successfully for {browser_type}")
        else:
            logger.warning(f"Failed to update extension for {browser_type}")
        
        return success
        
    def verify_extension_connection(self, browser_type: BrowserType, timeout_seconds: int = 30) -> bool:
        """Verify that the extension is properly connected to the tab server.
        
        Args:
            browser_type: Type of browser to verify
            timeout_seconds: Timeout for verification
            
        Returns:
            bool: True if connection is verified, False otherwise
        """
        logger.info(f"Verifying extension connection for browser type: {browser_type}")
        
        # Check if the extension is installed
        if not self.is_extension_installed(browser_type):
            logger.warning(f"Cannot verify extension connection for {browser_type}: not installed")
            return False
        
        # Get the browser name from the browser type
        browser_name = self._get_browser_name_from_type(browser_type)
        if not browser_name:
            logger.warning(f"Unknown browser type: {browser_type}")
            return False
        
        # Try to verify connection directly through the tab server object
        tab_server = get_tab_server()
        if tab_server:
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                if tab_server.is_extension_connected(browser_name):
                    logger.info(f"Extension connection verified for {browser_type}")
                    return True
                time.sleep(1)
        
        # Fall back to HTTP API if direct access fails
        try:
            tab_server_url = self._tab_server_url
            start_time = time.time()
            
            while time.time() - start_time < timeout_seconds:
                try:
                    response = requests.get(f"{tab_server_url}/api/status")
                    if response.status_code == 200:
                        status_data = response.json()
                        
                        if browser_name:
                            # Check specific browser connection status
                            browser_statuses = status_data.get('browser_statuses', {})
                            if browser_statuses.get(browser_name, {}).get('connected', False):
                                logger.info(f"Extension connection verified for {browser_type}")
                                return True
                        else:
                            # Check overall extension connection status
                            if status_data.get('extension_connected', False):
                                logger.info(f"Extension connection verified")
                                return True
                except Exception:
                    # Ignore exceptions and continue polling
                    pass
                    
                time.sleep(1)
                
            logger.warning(f"Extension connection verification timed out for {browser_type}")
            return False
        except Exception as e:
            logger.error(f"Error verifying extension connection: {e}")
            return False
    
    def _detect_browser_paths(self) -> None:
        """Detect installed browsers and their paths."""
        system = platform.system()
        
        if system == "Windows":
            # Windows browser detection
            chrome_paths = [
                os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google\\Chrome\\Application\\chrome.exe"),
                os.path.join(os.environ.get("ProgramFiles", ""), "Google\\Chrome\\Application\\chrome.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google\\Chrome\\Application\\chrome.exe")
            ]
            
            edge_paths = [
                os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft\\Edge\\Application\\msedge.exe"),
                os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft\\Edge\\Application\\msedge.exe")
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    self._browser_paths[BrowserType.CHROME] = path
                    break
                    
            for path in edge_paths:
                if os.path.exists(path):
                    self._browser_paths[BrowserType.EDGE] = path
                    break
        
        elif system == "Darwin":  # macOS
            self._browser_paths[BrowserType.CHROME] = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            self._browser_paths[BrowserType.EDGE] = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        
        else:  # Linux
            # Try to find browsers using 'which' command
            try:
                chrome_path = subprocess.check_output(["which", "google-chrome"]).decode().strip()
                self._browser_paths[BrowserType.CHROME] = chrome_path
            except subprocess.CalledProcessError:
                pass
                
            try:
                edge_path = subprocess.check_output(["which", "microsoft-edge"]).decode().strip()
                self._browser_paths[BrowserType.EDGE] = edge_path
            except subprocess.CalledProcessError:
                pass
        
        # Log detected browsers
        for browser_type, path in self._browser_paths.items():
            logger.info(f"Detected {browser_type} at: {path}")
    
    def _get_default_extension_dir(self) -> str:
        """Get the default extension directory.
        
        Returns:
            str: Default extension directory
        """
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Use the new extension directory in core
        extension_dir = os.path.join(current_dir, "webextension_mv3")
        
        # If the directory doesn't exist, fall back to the legacy location
        if not os.path.exists(extension_dir):
            # Navigate up to the project root and then to the legacy extensions directory
            project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            extension_dir = os.path.join(project_root, "core", "browser_detection", "webextension_mv3")
            logger.warning(f"New extension directory not found, falling back to legacy path: {extension_dir}")
        
        return extension_dir
    
    def _check_extension_installed(self, browser_type: BrowserType) -> bool:
        """Check if the extension is installed for a browser type.
        
        Args:
            browser_type: Type of browser to check
            
        Returns:
            bool: True if the extension is installed
        """
        # This would be replaced with actual extension installation check logic
        # For now, we'll just check if the extension directory exists
        extension_id = self._extension_ids.get(browser_type)
        if not extension_id:
            return False
        
        # Check based on browser type
        if browser_type == BrowserType.CHROME:
            return self._check_chrome_extension_installed(extension_id)
        elif browser_type == BrowserType.FIREFOX:
            return self._check_firefox_extension_installed(extension_id)
        elif browser_type == BrowserType.EDGE:
            return self._check_edge_extension_installed(extension_id)
        elif browser_type == BrowserType.BRAVE:
            return self._check_chrome_extension_installed(extension_id)  # Brave uses Chrome extensions
        elif browser_type == BrowserType.OPERA:
            return self._check_opera_extension_installed(extension_id)
        elif browser_type == BrowserType.SAFARI:
            return self._check_safari_extension_installed(extension_id)
        
        return False
    
    def _install_extension(self, browser_type: BrowserType) -> bool:
        """Install the extension for a browser type.
        
        Args:
            browser_type: Type of browser to install for
            
        Returns:
            bool: True if the extension was installed successfully
        """
        if not os.path.exists(self._extension_dir):
            logger.error(f"Extension directory not found: {self._extension_dir}")
            return False
            
        # Check if manifest.json exists
        manifest_path = os.path.join(self._extension_dir, 'manifest.json')
        if not os.path.exists(manifest_path):
            logger.error(f"Manifest file not found: {manifest_path}")
            return False
            
        # Check if browser is detected
        if browser_type not in self._browser_paths:
            logger.error(f"Browser {browser_type} not detected")
            return False
            
        browser_path = self._browser_paths[browser_type]
        
        try:
            if browser_type in [BrowserType.CHROME, BrowserType.BRAVE]:
                return self._install_chrome_extension(browser_path)
            elif browser_type == BrowserType.EDGE:
                return self._install_edge_extension(browser_path)
            elif browser_type == BrowserType.FIREFOX:
                return self._install_firefox_extension()
            else:
                logger.warning(f"Automatic installation not supported for {browser_type}")
                return self._open_extension_page(browser_type)
        except Exception as e:
            logger.error(f"Error installing extension for {browser_type}: {e}")
            return False
    
    def _update_extension(self, browser_type: BrowserType) -> bool:
        """Update the extension for a browser type.
        
        Args:
            browser_type: Type of browser to update for
            
        Returns:
            bool: True if the extension was updated successfully
        """
        # For unpacked extensions, updating is the same as installing
        # since we're just pointing to the extension directory
        return self._install_extension(browser_type)
    
    def _check_chrome_extension_installed(self, extension_id: str) -> bool:
        """Check if a Chrome extension is installed.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            bool: True if the extension is installed
        """
        # For development/unpacked extensions, we need to check if the extension
        # is loaded in the browser, which is challenging to do programmatically
        # We'll use a more reliable approach by checking for the existence of a
        # preferences file that mentions our extension
        
        if platform.system() == "Windows":
            preferences_path = os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Google", "Chrome", "User Data", "Default", "Preferences"
            )
        elif platform.system() == "Darwin":  # macOS
            preferences_path = os.path.join(
                os.path.expanduser("~"), "Library", "Application Support",
                "Google", "Chrome", "Default", "Preferences"
            )
        else:  # Linux
            preferences_path = os.path.join(
                os.path.expanduser("~"), ".config",
                "google-chrome", "Default", "Preferences"
            )
        
        if not os.path.exists(preferences_path):
            return False
            
        try:
            import json
            with open(preferences_path, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
                
            # Check if our extension is in the extensions list
            extensions = preferences.get('extensions', {}).get('settings', {})
            for ext_id, ext_data in extensions.items():
                # For unpacked extensions, the path will contain our extension directory
                if 'path' in ext_data and self._extension_dir.lower() in ext_data['path'].lower():
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error checking Chrome extension: {e}")
            return False
    
    def _check_firefox_extension_installed(self, extension_id: str) -> bool:
        """Check if a Firefox extension is installed.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            bool: True if the extension is installed
        """
        # This would be replaced with actual Firefox extension check logic
        # For now, we'll just return False
        return False
    
    def _check_edge_extension_installed(self, extension_id: str) -> bool:
        """Check if an Edge extension is installed.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            bool: True if the extension is installed
        """
        # Edge uses a similar structure to Chrome for extensions
        if platform.system() == "Windows":
            preferences_path = os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Microsoft", "Edge", "User Data", "Default", "Preferences"
            )
        elif platform.system() == "Darwin":  # macOS
            preferences_path = os.path.join(
                os.path.expanduser("~"), "Library", "Application Support",
                "Microsoft Edge", "Default", "Preferences"
            )
        else:  # Linux
            preferences_path = os.path.join(
                os.path.expanduser("~"), ".config",
                "microsoft-edge", "Default", "Preferences"
            )
        
        if not os.path.exists(preferences_path):
            return False
            
        try:
            import json
            with open(preferences_path, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
                
            # Check if our extension is in the extensions list
            extensions = preferences.get('extensions', {}).get('settings', {})
            for ext_id, ext_data in extensions.items():
                # For unpacked extensions, the path will contain our extension directory
                if 'path' in ext_data and self._extension_dir.lower() in ext_data['path'].lower():
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error checking Edge extension: {e}")
            return False
    
    def _check_opera_extension_installed(self, extension_id: str) -> bool:
        """Check if an Opera extension is installed.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            bool: True if the extension is installed
        """
        # This would be replaced with actual Opera extension check logic
        # For now, we'll just return False
        return False
    
    def _check_safari_extension_installed(self, extension_id: str) -> bool:
        """Check if a Safari extension is installed.
        
        Args:
            extension_id: ID of the extension
            
        Returns:
            bool: True if the extension is installed
        """
        # Safari extension installation is more complex and requires App Store
        # For now, we'll just return False
        return False
        
    def _install_chrome_extension(self, browser_path: str) -> bool:
        """Install extension for Chrome or Chromium-based browsers.
        
        Args:
            browser_path: Path to the browser executable
            
        Returns:
            bool: True if installation was successful
        """
        if not os.path.exists(browser_path):
            logger.error(f"Browser executable not found: {browser_path}")
            return False
            
        try:
            # Chrome can install extensions by launching with the --load-extension flag
            # This will open Chrome with the extension loaded
            cmd = [browser_path, f"--load-extension={self._extension_dir}", "--no-first-run"]
            
            # Start Chrome with our extension
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Chrome launched with extension: {self._extension_dir}")
            
            return True
        except Exception as e:
            logger.error(f"Error installing Chrome extension: {e}")
            return False
            
    def _install_edge_extension(self, browser_path: str) -> bool:
        """Install extension for Microsoft Edge.
        
        Args:
            browser_path: Path to the browser executable
            
        Returns:
            bool: True if installation was successful
        """
        if not os.path.exists(browser_path):
            logger.error(f"Browser executable not found: {browser_path}")
            return False
            
        try:
            # Edge extensions cannot be permanently installed by copying files
            # Use developer mode loading which is the standard approach for unpacked extensions
            logger.info("Installing Edge extension using developer mode loading")
            return self._launch_edge_with_extension(browser_path)
            
        except Exception as e:
            logger.error(f"Error installing Edge extension: {e}")
            return False
    
    def _copy_extension_to_edge_directory(self) -> bool:
        """Copy extension to Edge extensions directory for permanent installation."""
        try:
            import shutil
            
            # Get Edge extensions directory
            user_profile = os.path.expanduser("~")
            edge_extensions_dir = os.path.join(
                user_profile, "AppData", "Local", "Microsoft", "Edge", 
                "User Data", "Default", "Extensions"
            )
            
            if not os.path.exists(edge_extensions_dir):
                logger.error(f"Edge extensions directory not found: {edge_extensions_dir}")
                return False
            
            # Create extension directory with a unique ID
            extension_id = "focus_guard_extension"
            target_dir = os.path.join(edge_extensions_dir, extension_id)
            
            # Remove existing if present
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            
            # Copy extension files
            shutil.copytree(self._extension_dir, target_dir)
            logger.info(f"Extension copied to Edge directory: {target_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy extension to Edge directory: {e}")
            return False
    
    def _launch_edge_with_extension(self, browser_path: str) -> bool:
        """Launch Edge with extension loaded."""
        try:
            # Edge can load extensions by launching with the --load-extension flag
            cmd = [browser_path, f"--load-extension={self._extension_dir}", "--no-first-run"]
            
            # Start Edge with our extension
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Edge launched with extension: {self._extension_dir}")
            
            return True
        except Exception as e:
            logger.error(f"Error launching Edge with extension: {e}")
            return False
            
    def _install_firefox_extension(self) -> bool:
        """Install extension for Firefox.
        
        Returns:
            bool: True if installation was successful
        """
        # Firefox extension installation is more complex
        # For now, we'll just open the extension page
        return self._open_extension_page(BrowserType.FIREFOX)
        
    def _open_extension_page(self, browser_type: BrowserType) -> bool:
        """Open the extension page for manual installation.
        
        Args:
            browser_type: Type of browser
            
        Returns:
            bool: True if browser was opened successfully
        """
        try:
            if browser_type == BrowserType.CHROME:
                webbrowser.get('chrome').open('chrome://extensions/')
            elif browser_type == BrowserType.EDGE:
                webbrowser.get('edge').open('edge://extensions/')
            elif browser_type == BrowserType.FIREFOX:
                webbrowser.get('firefox').open('about:addons')
            else:
                # Fallback to default browser
                if browser_type == BrowserType.BRAVE:
                    webbrowser.open('brave://extensions/')
                elif browser_type == BrowserType.OPERA:
                    webbrowser.open('opera://extensions/')
                else:
                    logger.warning(f"No specific extension page for {browser_type}")
                    return False
                    
            logger.info(f"Opened extension page for {browser_type}")
            return True
        except Exception as e:
            logger.error(f"Error opening extension page for {browser_type}: {e}")
            return False
            
    def _get_browser_name_from_type(self, browser_type: BrowserType) -> str:
        """Get the browser name from the browser type.
        
        Args:
            browser_type: Type of browser
            
        Returns:
            str: Browser name
        """
        browser_name_map = {
            BrowserType.CHROME: "chrome",
            BrowserType.FIREFOX: "firefox",
            BrowserType.EDGE: "edge",
            BrowserType.BRAVE: "brave",
            BrowserType.OPERA: "opera",
            BrowserType.SAFARI: "safari"
        }
        
        return browser_name_map.get(browser_type, "")
