"""
Platform-specific implementations for activity monitoring.

This module provides platform detection and factory methods for instantiating
the appropriate platform-specific activity monitor implementation.
"""

from typing import Optional, Type
import sys
from core_v2.activity.platform.base import PlatformActivityMonitor


def get_platform_implementation() -> PlatformActivityMonitor:
    """
    Factory function to get the appropriate platform implementation.
    
    Returns:
        PlatformActivityMonitor: An instance of the appropriate platform-specific
                                implementation of PlatformActivityMonitor.
                                
    Raises:
        RuntimeError: If no supported platform implementation is found.
    """
    # Try each implementation in order of preference
    implementations = []
    
    # Import all available implementations
    try:
        from core_v2.activity.platform.windows import WindowsActivityMonitor
        implementations.append(WindowsActivityMonitor)
    except ImportError:
        pass
        
    try:
        from core_v2.activity.platform.linux import LinuxActivityMonitor
        implementations.append(LinuxActivityMonitor)
    except ImportError:
        pass
        
    try:
        from core_v2.activity.platform.macos import MacOSActivityMonitor
        implementations.append(MacOSActivityMonitor)
    except ImportError:
        pass
    
    # Try to find a supported implementation
    for impl_class in implementations:
        if impl_class.is_supported():
            return impl_class()
            
    raise RuntimeError("No supported platform implementation found for activity monitoring.")
