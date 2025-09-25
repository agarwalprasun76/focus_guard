"""
Platform detection utility for cross-platform Focus Guard
Detects current platform and provides platform-specific implementations
"""
import platform
import sys
from typing import Optional


class PlatformDetector:
    """Cross-platform platform detection"""
    
    @staticmethod
    def detect_platform() -> str:
        """Detect current platform"""
        system = platform.system().lower()
        
        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        elif system == 'linux':
            return 'linux'
        else:
            return system
    
    @staticmethod
    def get_platform_info() -> dict:
        """Get detailed platform information"""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': sys.version
        }
    
    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows"""
        return platform.system().lower() == 'windows'
    
    @staticmethod
    def is_macos() -> bool:
        """Check if running on macOS"""
        return platform.system().lower() == 'darwin'
    
    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux"""
        return platform.system().lower() == 'linux'
