"""
Adapter factory module.

This module provides factory functions for creating browser adapters.
"""

from typing import Type, TypeVar, Optional, Dict, Any

from focus_guard.core.browser.adapters.registry import register_adapter, get_adapter as _get_adapter
from focus_guard.core.browser.interfaces import (
    BrowserDetectorInterface,
    TabTrackerInterface,
    TabBlockerInterface,
    ExtensionManagerInterface
)
from .browser_detector import DefaultBrowserDetector
from .tab_tracker import DefaultTabTracker
from .tab_blocker import DefaultTabBlocker
from .extension_manager import DefaultExtensionManager

# Register default implementations
register_adapter(BrowserDetectorInterface, DefaultBrowserDetector)
register_adapter(TabTrackerInterface, DefaultTabTracker)
register_adapter(TabBlockerInterface, DefaultTabBlocker)
register_adapter(ExtensionManagerInterface, DefaultExtensionManager)

def create_browser_detector(**kwargs) -> BrowserDetectorInterface:
    """Create a browser detector instance.
    
    Args:
        **kwargs: Additional arguments to pass to the detector constructor
        
    Returns:
        BrowserDetectorInterface: A new browser detector instance
    """
    return _get_adapter(BrowserDetectorInterface, **kwargs)

def create_tab_tracker(**kwargs) -> TabTrackerInterface:
    """Create a tab tracker instance.
    
    Args:
        **kwargs: Additional arguments to pass to the tracker constructor
        
    Returns:
        TabTrackerInterface: A new tab tracker instance
    """
    return _get_adapter(TabTrackerInterface, **kwargs)

def create_tab_blocker(**kwargs) -> TabBlockerInterface:
    """Create a tab blocker instance.
    
    Args:
        **kwargs: Additional arguments to pass to the blocker constructor
        
    Returns:
        TabBlockerInterface: A new tab blocker instance
    """
    return _get_adapter(TabBlockerInterface, **kwargs)

def create_extension_manager(**kwargs) -> ExtensionManagerInterface:
    """Create an extension manager instance.
    
    Args:
        **kwargs: Additional arguments to pass to the manager constructor
        
    Returns:
        ExtensionManagerInterface: A new extension manager instance
    """
    return _get_adapter(ExtensionManagerInterface, **kwargs)

def register_custom_adapter(interface: Type, implementation: Type) -> None:
    """Register a custom adapter implementation.
    
    Args:
        interface: The interface class to register for
        implementation: The implementation class to use
    """
    register_adapter(interface, implementation)
