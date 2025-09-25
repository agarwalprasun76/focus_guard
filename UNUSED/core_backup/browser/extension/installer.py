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

from core_v2.browser.extension.manager import BrowserExtensionManager
from core_v2.browser.models.browser import BrowserType
from core_v2.browser.extension.tab_server import TabServer
from core_v2.browser.extension.interfaces import TabServerConfig

# Import user installation guide if available
USER_GUIDE_AVAILABLE = False
try:
    from core_v2.browser.extension.user_installation.launcher import launch_guide_async, launch_guide_for_browser
    USER_GUIDE_AVAILABLE = True
except ImportError:
    # User installation guide not available
    pass

logger = logging.getLogger(__name__)


class ExtensionInstaller:
    """Extension installer for Focus Guard browser extensions."""
    
    def __init__(self, extension_dir: str = None, offer_user_guide: bool = True):
        """Initialize the extension installer.
        
        Args:
            extension_dir: Directory containing extension files
            offer_user_guide: Whether to offer the user installation guide when needed
        """
        self._extension_manager = BrowserExtensionManager(extension_dir)
        self._tab_server: Optional[TabServer] = None
        self._tab_server_thread: Optional[threading.Thread] = None
        
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
            Tuple[bool, bool]: (installation_success, user_guide_launched)
        """
        # Ensure tab server is running before installing extension
        if not self.ensure_tab_server_running():
            logger.error("Cannot install extension: Tab server is not running")
            return False, False
        
        # Install the extension programmatically
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
                return {
                    BrowserType[browser.upper()]: status.get("connected", False)
                    for browser, status in browser_statuses.items()
                    if hasattr(BrowserType, browser.upper())
                }
                
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
            # Launch the browser-specific installation guide
            launch_guide_for_browser(browser_type, self._extension_manager._extension_dir)
            return True
        except Exception as e:
            logger.error(f"Error launching user installation guide for {browser_type.name}: {e}")
            return False
