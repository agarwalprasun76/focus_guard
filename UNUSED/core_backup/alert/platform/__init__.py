"""
Platform factory for alert functionality.

This module provides a factory function to get the appropriate platform
implementation for the current operating system.
"""

import sys
import logging
from typing import Type, List, Optional

from core_v2.alert.platform.base import PlatformAlertInterface

# Configure logging
logger = logging.getLogger(__name__)

# Global platform instance (singleton)
_platform_instance: Optional[PlatformAlertInterface] = None


def get_platform_implementation() -> PlatformAlertInterface:
    """
    Factory function to get the appropriate platform implementation.
    
    This function detects the current operating system and returns the
    appropriate platform implementation. If no suitable implementation
    is found, it falls back to a stub implementation.
    
    Returns:
        PlatformAlertInterface: Platform-specific implementation
    """
    global _platform_instance
    
    # Return cached instance if available
    if _platform_instance is not None:
        return _platform_instance
    
    # List of platform implementations to try, in order of preference
    implementations: List[Type[PlatformAlertInterface]] = []
    
    # Import all available implementations
    if sys.platform == "win32":
        try:
            from core_v2.alert.platform.windows import WindowsAlertPlatform
            implementations.append(WindowsAlertPlatform)
        except ImportError as e:
            logger.warning(f"Failed to import WindowsAlertPlatform: {e}")
    
    elif sys.platform == "darwin":
        try:
            from core_v2.alert.platform.macos import MacOSAlertPlatform
            implementations.append(MacOSAlertPlatform)
        except ImportError as e:
            logger.warning(f"Failed to import MacOSAlertPlatform: {e}")
    
    elif sys.platform.startswith("linux"):
        try:
            from core_v2.alert.platform.linux import LinuxAlertPlatform
            implementations.append(LinuxAlertPlatform)
        except ImportError as e:
            logger.warning(f"Failed to import LinuxAlertPlatform: {e}")
    
    # Find the first supported implementation
    for impl in implementations:
        if impl.is_supported():
            logger.info(f"Using platform implementation: {impl.__name__}")
            _platform_instance = impl()
            return _platform_instance
    
    # Fall back to stub implementation if no supported implementation found
    try:
        from core_v2.alert.platform.stub import StubAlertPlatform
        logger.warning("No supported platform implementation found, using stub implementation")
        _platform_instance = StubAlertPlatform()
        return _platform_instance
    except ImportError as e:
        logger.error(f"Failed to import StubAlertPlatform: {e}")
        raise RuntimeError("No alert platform implementation available") from e
