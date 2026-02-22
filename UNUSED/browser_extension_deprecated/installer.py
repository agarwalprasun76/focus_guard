"""
Extension installer module.

This module provides functionality for installing and setting up browser extensions
programmatically within the Focus Guard application.
"""

import os
import sys
import time
import logging
import threading
from typing import List, Optional, Dict, Any, Tuple

from focus_guard.core.browser.models.browser import BrowserType
from focus_guard.core.browser.extension.manager import BrowserExtensionManager
from focus_guard.core.browser.extension.robust_installer import (
    RobustExtensionInstaller, ExtensionInstallationService, InstallationResult
)
from focus_guard.core.browser.extension.windows_admin_utils import (
    WindowsAdminUtils, ExtensionProtectionManager
)
from focus_guard.core.browser.extension.tab_server import get_tab_server
from focus_guard.core.browser.extension.process_manager import get_tab_server_process_manager
from focus_guard.core.browser.extension.interfaces import TabServerConfig

# Import user installation guide if available
USER_GUIDE_AVAILABLE = False
try:
    from focus_guard.core.browser.extension.user_installation.launcher import launch_guide_async, launch_guide_for_browser
    USER_GUIDE_AVAILABLE = True
except ImportError:
    # User installation guide not available
    pass

logger = logging.getLogger(__name__)


class ExtensionInstaller:
    """Main extension installer class that manages the installation process."""
    
    def __init__(self, offer_user_guide: bool = True, tab_server_config: Optional[TabServerConfig] = None,
                 use_robust_installer: bool = True):
        """Initialize the extension installer.
        
        Args:
            offer_user_guide: Whether to offer user installation guide for manual installation
            tab_server_config: Configuration for the tab server
            use_robust_installer: Whether to use the robust installer with retry logic
        """
        self._offer_user_guide = offer_user_guide
        self._tab_server_config = tab_server_config or TabServerConfig()
        
        # Use robust installer if requested
        if use_robust_installer:
            self._extension_manager = RobustExtensionInstaller()
            self._installation_service = ExtensionInstallationService()
            self._protection_manager = ExtensionProtectionManager(self._extension_manager._extension_dir)
        else:
            self._extension_manager = BrowserExtensionManager()
            self._installation_service = None
            self._protection_manager = None
            
        self._process_manager = get_tab_server_process_manager()
        self._tab_server = None
        self._installation_lock = threading.Lock()
        self._use_robust_installer = use_robust_installer
        
    def ensure_tab_server_running(self, port: int = 5000) -> bool:
        """Ensure that the tab server is running.
        
        Args:
            port: Port to run the tab server on
            
        Returns:
            bool: True if the tab server is running
        """
        if self._tab_server is not None and self._tab_server.is_running():
            logger.info("Tab server is already running")
            return True
            
        try:
            # Create a new tab server instance with proper configuration
            config = TabServerConfig(port=port)
            self._tab_server = TabServer(config=config)
            
            # Start the tab server in a separate thread
            self._tab_server_thread = threading.Thread(
                target=self._tab_server.start,
                daemon=True
            )
            self._tab_server_thread.start()
            
            # Wait for the server to start
            for _ in range(10):  # Try for up to 5 seconds
                if self._tab_server.is_running():
                    logger.info(f"Tab server started successfully on port {port}")
                    return True
                time.sleep(0.5)
                
            logger.error("Tab server failed to start within the timeout period")
            return False
        except Exception as e:
            logger.error(f"Error starting tab server: {e}")
            return False
    
    def stop_tab_server(self) -> bool:
        """Stop the tab server if it's running.
        
        Returns:
            bool: True if the tab server was stopped successfully
        """
        if self._tab_server is None:
            logger.info("Tab server is not running")
            return True
            
        try:
            self._tab_server.stop()
            if self._tab_server_thread and self._tab_server_thread.is_alive():
                self._tab_server_thread.join(timeout=5.0)
            
            logger.info("Tab server stopped successfully")
            self._tab_server = None
            self._tab_server_thread = None
            return True
        except Exception as e:
            logger.error(f"Error stopping tab server: {e}")
            return False
    
    def install_extension(self, browser_type: BrowserType) -> Tuple[bool, bool]:
        """Install the extension for a browser type.
        
        Args:
            browser_type: Type of browser to install for
            
        Returns:
            Tuple[bool, bool]: (success, user_guide_launched)
        """
        logger.info(f"Installing extension for browser type: {browser_type}")
        
        with self._installation_lock:
            # Ensure tab server is running before installing extension
            if not self.ensure_tab_server_running():
                logger.error("Cannot install extension: Tab server is not running")
                return False, False
            
            # Use robust installer if available
            if self._use_robust_installer and self._installation_service:
                result = self._extension_manager.install_extension_robust(browser_type)
                success = result.success
                
                # Log detailed result
                if result.success:
                    logger.info(f"Robust installation successful for {browser_type} in {result.attempts} attempts")
                else:
                    logger.error(f"Robust installation failed for {browser_type}: {result.error_message}")
            else:
                # Fall back to standard installation
                success = self._extension_manager.install_extension(browser_type)
            
            # If installation failed or we know it's temporary (Chrome/Edge), offer user guide
            user_guide_launched = False
            if self._offer_user_guide and USER_GUIDE_AVAILABLE:
                if not success or browser_type in [BrowserType.CHROME, BrowserType.EDGE]:
                    logger.info(f"Offering user installation guide for {browser_type.name}")
                    user_guide_launched = self.launch_user_installation_guide_for_browser(browser_type)
                
            return success, user_guide_launched
    
    def install_for_detected_browsers(self) -> Dict[BrowserType, Dict[str, bool]]:
        """Install the extension for all detected browsers.
        
        Returns:
            Dict[BrowserType, Dict[str, bool]]: Dictionary mapping browser types to installation results
                                              with 'success' and 'user_guide_launched' keys
        """
        # Ensure tab server is running
        if not self.ensure_tab_server_running():
            logger.error("Cannot install extensions: Tab server is not running")
            return {}
        
        # Use robust installation service if available
        if self._use_robust_installer and self._installation_service:
            logger.info("Using robust installation service for all browsers")
            installation_summary = self._installation_service.install_all_extensions()
            
            # Convert to expected format
            results = {}
            if "installation_results" in installation_summary:
                for browser_type, result in installation_summary["installation_results"].items():
                    results[browser_type] = {
                        'success': result.success,
                        'user_guide_launched': False  # Robust installer handles this internally
                    }
            
            return results
        else:
            # Fall back to standard installation
            results = {}
            
            # Get all browser types that have detected paths
            for browser_type in self._extension_manager._browser_paths.keys():
                logger.info(f"Installing extension for detected browser: {browser_type}")
                success, user_guide_launched = self.install_extension(browser_type)
                results[browser_type] = {
                    'success': success,
                    'user_guide_launched': user_guide_launched
                }
                
            return results
    
    def check_extension_connections(self, timeout: int = 30) -> Dict[BrowserType, bool]:
        """Check if extensions are connected to the tab server.
        
        Args:
            timeout: Timeout in seconds to wait for connections
            
        Returns:
            Dict[BrowserType, bool]: Dictionary mapping browser types to connection status
        """
        if self._tab_server is None or not self._tab_server.is_running():
            logger.error("Cannot check connections: Tab server is not running")
            return {}
            
        # Wait for extensions to connect
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Get status from tab server
            status = self._tab_server.get_status()
            
            # Check if any browsers are connected
            if status.get("extension_connected", False):
                # Return the status of each browser
                browser_statuses = status.get("browser_statuses", {})
                result = {}
                
                # Process each browser status
                for browser_name, browser_status in browser_statuses.items():
                    # Convert browser name to uppercase for BrowserType enum lookup
                    browser_type_name = browser_name.upper()
                    
                    # Only include browsers that are in our BrowserType enum
                    if hasattr(BrowserType, browser_type_name):
                        # Check if this browser has updated recently (within 30 seconds)
                        last_update = browser_status.get("last_update", 0)
                        is_connected = (time.time() - last_update) < 30
                        result[BrowserType[browser_type_name]] = is_connected
                
                return result
                
            # Sleep before checking again
            time.sleep(1)
            
        # Timeout reached, return empty dict
        logger.warning(f"No extensions connected within {timeout} seconds")
        return {}
    
    def verify_installation(self, browser_type: BrowserType, timeout: int = 30) -> bool:
        """Verify that the extension is installed and connected.
        
        Args:
            browser_type: Type of browser to verify
            timeout: Timeout in seconds to wait for connection
            
        Returns:
            bool: True if the extension is installed and connected
        """
        # Check if extension is installed
        if not self._extension_manager.is_extension_installed(browser_type):
            logger.warning(f"Extension not installed for {browser_type}")
            return False
            
        # Check if extension is connected to tab server
        connections = self.check_extension_connections(timeout)
        return connections.get(browser_type, False)
    
    def get_extension_dir(self) -> str:
        """Get the extension directory.
        
        Returns:
            str: Path to the extension directory
        """
        return self._extension_manager._extension_dir
        
    def launch_user_installation_guide(self) -> bool:
        """Launch the user installation guide UI.
        
        Returns:
            bool: True if the guide was launched successfully
        """
        if not self._offer_user_guide or not USER_GUIDE_AVAILABLE:
            logger.error("User installation guide is not available")
            return False
            
        try:
            # Launch the full user installation guide UI
            launch_guide_async(self._extension_manager._extension_dir)
            return True
        except Exception as e:
            logger.error(f"Error launching user installation guide: {e}")
            return False
    
    def install_with_protection(self) -> Dict[str, Any]:
        """Install extensions with full Windows protection and verification.
        
        Returns:
            Dict[str, Any]: Complete installation report with protection status
        """
        logger.info("Starting protected extension installation")
        
        if not self._use_robust_installer:
            logger.warning("Robust installer not enabled - using standard installation")
            return {"error": "Robust installer not enabled"}
        
        # Apply protection first
        protection_results = self._protection_manager.apply_full_protection()
        logger.info(f"Protection applied: {protection_results}")
        
        # Install extensions
        installation_summary = self._installation_service.install_all_extensions()
        
        # Verify installations
        verification_results = self._installation_service.verify_all_extensions()
        
        # Create comprehensive report
        report = {
            "protection": protection_results,
            "installation": installation_summary,
            "verification": verification_results,
            "report": self._installation_service.create_installation_report()
        }
        
        return report
    
    def verify_and_repair_extensions(self) -> Dict[BrowserType, bool]:
        """Verify all extensions and repair if necessary.
        
        Returns:
            Dict[BrowserType, bool]: Repair results per browser
        """
        if not self._use_robust_installer:
            logger.warning("Robust installer not enabled")
            return {}
        
        logger.info("Starting extension verification and repair")
        
        # First verify protection integrity
        if self._protection_manager:
            protection_status = self._protection_manager.verify_protection()
            logger.info(f"Protection status: {protection_status}")
            
            # Repair protection if needed
            if not all(protection_status.values()):
                logger.info("Repairing extension protection")
                self._protection_manager.repair_protection()
        
        # Repair extensions
        return self._extension_manager.repair_all_extensions()
    
    def get_installation_status_report(self) -> str:
        """Get a detailed status report of all extension installations.
        
        Returns:
            str: Formatted status report
        """
        if self._use_robust_installer and self._installation_service:
            return self._installation_service.create_installation_report()
        else:
            # Create basic report for standard installer
            report = []
            report.append("=== Focus Guard Extension Status (Standard) ===")
            
            for browser_type in self._extension_manager._browser_paths.keys():
                installed = self._extension_manager.is_extension_installed(browser_type)
                status_icon = "✅" if installed else "❌"
                report.append(f"  {status_icon} {browser_type.name}: {'Installed' if installed else 'Not Installed'}")
            
            return "\n".join(report)
        
    def launch_user_installation_guide_for_browser(self, browser_type: BrowserType) -> bool:
        """Launch the user installation guide for a specific browser.
        
        Args:
            browser_type: Type of browser to install extension for
        
        Returns:
            bool: True if the guide was launched successfully
        """
        if not self._offer_user_guide or not USER_GUIDE_AVAILABLE:
            logger.error("User installation guide is not available")
            return False
            
        try:
            # Check if the browser type is supported by the installation guide
            # This prevents errors with browser types that might be missing in the guide
            from focus_guard.core.browser.extension.user_installation.guide import ExtensionInstallationGuide
            guide = ExtensionInstallationGuide(self._extension_manager._extension_dir)
            
            # Only proceed if the browser type is in the extension pages dictionary
            if browser_type in guide._extension_pages:
                # Launch the browser-specific installation guide
                launch_guide_for_browser(browser_type, self._extension_manager._extension_dir)
                return True
            else:
                logger.warning(f"Browser type {browser_type.name} not supported by installation guide")
                # Fall back to generic installation guide
                self.launch_user_installation_guide()
                return True
        except Exception as e:
            logger.error(f"Error launching user installation guide for {browser_type.name}: {e}")
            return False
