"""
Browser adapter implementations.

This package contains implementations of browser-related interfaces.
"""

from typing import Type, TypeVar, Optional
from focus_guard.core.browser.interfaces import (
    BrowserDetectorInterface,
    TabTrackerInterface,
    TabBlockerInterface,
    ExtensionManagerInterface
)
from .registry import register_adapter, get_adapter as _get_adapter
from .factory import (
    create_browser_detector,
    create_tab_tracker,
    create_tab_blocker,
    create_extension_manager,
    register_custom_adapter
)

# Re-export interfaces and factory functions
__all__ = [
    # Interfaces
    'BrowserDetectorInterface',
    'TabTrackerInterface',
    'TabBlockerInterface',
    'ExtensionManagerInterface',
    
    # Factory functions
    'create_browser_detector',
    'create_tab_tracker',
    'create_tab_blocker',
    'create_extension_manager',
    'register_custom_adapter',
    'register_adapter'
]
