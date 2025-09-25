"""
Browser component factory.

This module provides a factory for creating and configuring browser components.
"""

import logging
from typing import Optional, Dict, Any

from core_v2.browser.interfaces import (
    BrowserDetectorInterface,
    TabTrackerInterface,
    TabBlockerInterface,
    ExtensionManagerInterface,
    UsageTrackerInterface
)
from core_v2.browser.adapter import (
    BrowserDetector,
    TabTracker,
    TabBlocker
)
from core_v2.browser.integration.tab_tracker import BrowserTabTracker
from core_v2.browser.integration.tab_blocker import BrowserTabBlocker
from core_v2.browser.extension.manager import BrowserExtensionManager
from core_v2.browser.usage.tracker import BrowserUsageTracker

logger = logging.getLogger(__name__)


class BrowserComponentFactory:
    """Factory for creating browser components."""
    
    @staticmethod
    def create_browser_detector(config: Optional[Dict[str, Any]] = None) -> BrowserDetectorInterface:
        """Create a browser detector instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            BrowserDetectorInterface: Browser detector instance
        """
        logger.debug("Creating browser detector")
        return BrowserDetector()
    
    @staticmethod
    def create_tab_tracker(
        config: Optional[Dict[str, Any]] = None,
        use_extension: bool = True
    ) -> TabTrackerInterface:
        """Create a tab tracker instance.
        
        Args:
            config: Optional configuration dictionary
            use_extension: Whether to use the extension-based implementation
            
        Returns:
            TabTrackerInterface: Tab tracker instance
        """
        logger.debug(f"Creating tab tracker (use_extension={use_extension})")
        
        if use_extension:
            extension_server_url = config.get("extension_server_url") if config else None
            return BrowserTabTracker(extension_server_url=extension_server_url)
        else:
            return TabTracker()
    
    @staticmethod
    def create_tab_blocker(
        config: Optional[Dict[str, Any]] = None,
        use_extension: bool = True
    ) -> TabBlockerInterface:
        """Create a tab blocker instance.
        
        Args:
            config: Optional configuration dictionary
            use_extension: Whether to use the extension-based implementation
            
        Returns:
            TabBlockerInterface: Tab blocker instance
        """
        logger.debug(f"Creating tab blocker (use_extension={use_extension})")
        
        if use_extension:
            extension_server_url = config.get("extension_server_url") if config else None
            return BrowserTabBlocker(extension_server_url=extension_server_url)
        else:
            return TabBlocker()
    
    @staticmethod
    def create_extension_manager(
        config: Optional[Dict[str, Any]] = None
    ) -> ExtensionManagerInterface:
        """Create an extension manager instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            ExtensionManagerInterface: Extension manager instance
        """
        logger.debug("Creating extension manager")
        
        extension_dir = config.get("extension_dir") if config else None
        return BrowserExtensionManager(extension_dir=extension_dir)
    
    @staticmethod
    def create_usage_tracker(
        config: Optional[Dict[str, Any]] = None
    ) -> UsageTrackerInterface:
        """Create a usage tracker instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            UsageTrackerInterface: Usage tracker instance
        """
        logger.debug("Creating usage tracker")
        
        storage_dir = config.get("storage_dir") if config else None
        return BrowserUsageTracker(storage_dir=storage_dir)
    
    @classmethod
    def create_all_components(
        cls,
        config: Optional[Dict[str, Any]] = None,
        use_extension: bool = True
    ) -> Dict[str, Any]:
        """Create all browser components.
        
        Args:
            config: Optional configuration dictionary
            use_extension: Whether to use the extension-based implementations
            
        Returns:
            Dict[str, Any]: Dictionary containing all components
        """
        logger.info(f"Creating all browser components (use_extension={use_extension})")
        
        return {
            "browser_detector": cls.create_browser_detector(config),
            "tab_tracker": cls.create_tab_tracker(config, use_extension),
            "tab_blocker": cls.create_tab_blocker(config, use_extension),
            "extension_manager": cls.create_extension_manager(config),
            "usage_tracker": cls.create_usage_tracker(config)
        }
