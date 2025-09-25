"""
Extension management adapter implementation.

This module provides the default implementation of the ExtensionManagerInterface.
"""

import os
import shutil
import logging
from typing import Optional, Dict, Any

from focus_guard.core.browser.interfaces import ExtensionManagerInterface
from focus_guard.core.browser.models.browser import BrowserType

logger = logging.getLogger(__name__)

class DefaultExtensionManager(ExtensionManagerInterface):
    """Default implementation of the ExtensionManagerInterface.
    
    This implementation handles browser extension installation and management.
    """
    
    def __init__(self):
        """Initialize the extension manager."""
        self._installed_extensions = {}  # browser_type -> installed status
        self._logger = logger.getChild('DefaultExtensionManager')
    
    def is_extension_installed(self, browser_type: BrowserType) -> bool:
        """Check if the extension is installed for a browser type.
        
        Args:
            browser_type: Type of browser to check
            
        Returns:
            bool: True if the extension is installed
        """
        # Check cache first
        if browser_type in self._installed_extensions:
            return self._installed_extensions[browser_type]
        
        # In a real implementation, this would check the browser's extension directory
        try:
            ext_path = self._get_extension_path(browser_type)
            installed = ext_path is not None and os.path.exists(ext_path)
            self._installed_extensions[browser_type] = installed
            return installed
        except Exception as e:
            self._logger.error(f"Error checking extension installation for {browser_type}: {e}")
            return False
    
    def install_extension(self, browser_type: BrowserType) -> bool:
        """Install the extension for a browser type.
        
        Args:
            browser_type: Type of browser to install for
            
        Returns:
            bool: True if the extension was installed successfully
        """
        try:
            ext_path = self._get_extension_path(browser_type)
            if ext_path is None:
                self._logger.error(f"Unsupported browser type: {browser_type}")
                return False
                
            # Create target directory if it doesn't exist
            os.makedirs(os.path.dirname(ext_path), exist_ok=True)
            
            # In a real implementation, this would copy the extension files
            # For now, we'll just create a marker file
            with open(ext_path, 'w') as f:
                f.write(f"Extension for {browser_type.name}")
            
            self._installed_extensions[browser_type] = True
            self._logger.info(f"Installed extension for {browser_type.name}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error installing extension for {browser_type}: {e}")
            return False
    
    def update_extension(self, browser_type: BrowserType) -> bool:
        """Update the extension for a browser type.
        
        Args:
            browser_type: Type of browser to update for
            
        Returns:
            bool: True if the extension was updated successfully
        """
        # For now, we'll just reinstall the extension
        return self.install_extension(browser_type)
    
    def _get_extension_path(self, browser_type: BrowserType) -> Optional[str]:
        """Get the path to the extension directory for a browser type.
        
        Args:
            browser_type: Browser type to get extension path for
            
        Returns:
            Optional[str]: Path to the extension directory, or None if not found
        """
        ext_dir = self._get_browser_extension_dir(browser_type)
        if ext_dir is None:
            return None
            
        return os.path.join(ext_dir, "focus_guard_extension")
    
    def _get_browser_extension_dir(self, browser_type: BrowserType) -> Optional[str]:
        """Get the browser-specific extension directory.
        
        Args:
            browser_type: Browser type to get extension directory for
            
        Returns:
            Optional[str]: Path to the browser-specific extension directory,
                         or None if unsupported
        """
        base_dir = self._get_extension_base_dir()
        
        if browser_type == BrowserType.CHROME:
            return os.path.join(base_dir, "Google", "Chrome", "Extensions")
        elif browser_type == BrowserType.FIREFOX:
            return os.path.join(base_dir, "Mozilla", "Firefox", "Profiles")
        elif browser_type == BrowserType.EDGE:
            return os.path.join(base_dir, "Microsoft", "Edge", "Extensions")
        elif browser_type == BrowserType.BRAVE:
            return os.path.join(base_dir, "BraveSoftware", "Brave-Browser", "Extensions")
        elif browser_type == BrowserType.OPERA:
            return os.path.join(base_dir, "Opera Software", "Opera Stable", "Extensions")
        else:
            return None
    
    def _get_extension_base_dir(self) -> str:
        """Get the base directory for extensions.
        
        Returns:
            str: Path to the base extension directory
        """
        # On Windows, extensions are typically stored in the AppData directory
        appdata = os.environ.get('APPDATA')
        if appdata is None:
            # Fall back to home directory if APPDATA is not set
            return os.path.expanduser('~')
            
        # Go to LocalAppData from AppData/Roaming
        return os.path.abspath(os.path.join(appdata, '..', 'Local'))
