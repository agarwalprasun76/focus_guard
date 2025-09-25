"""
Windows-specific implementation for Focus Guard
Handles Windows-specific functionality while maintaining cross-platform interface
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

from focus_guard.windows_config import WindowsConfig
from focus_guard.core.coordinator import FocusGuardCoordinator


class WindowsImplementation:
    """Windows-specific implementation of Focus Guard functionality"""
    
    def __init__(self):
        self.config = WindowsConfig()
        self.coordinator = None
        self.is_monitoring = False
        
    def start_monitoring(self, config_path: Optional[str] = None, daemon: bool = False):
        """Start monitoring with Windows-specific settings"""
        try:
            # Load Windows-specific configuration
            if config_path:
                self.config = WindowsConfig(config_path)
            
            config_data = self.config.load_config()
            
            print(f"✅ Windows configuration loaded: {len(config_data)} settings")
            print(f"📊 Monitoring {len(config_data.get('blocked_domains', []))} blocked domains")
            
            # Initialize coordinator
            self.coordinator = FocusGuardCoordinator()
            
            if daemon:
                print("🔄 Running in daemon mode...")
                import threading
                monitor_thread = threading.Thread(target=self.coordinator.start)
                monitor_thread.daemon = True
                monitor_thread.start()
                print("✅ Focus Guard started in background")
            else:
                print("📋 Starting interactive monitoring...")
                self.coordinator.start()
                print("✅ Focus Guard monitoring active")
                
            self.is_monitoring = True
            
        except Exception as e:
            print(f"❌ Error starting Focus Guard: {e}")
            raise
            
    def stop_monitoring(self):
        """Stop monitoring"""
        try:
            if self.coordinator:
                self.coordinator.stop()
                print("✅ Focus Guard stopped")
                self.is_monitoring = False
        except Exception as e:
            print(f"❌ Error stopping Focus Guard: {e}")
            raise
            
    def show_status(self, format: str = 'simple'):
        """Show Windows-specific status"""
        try:
            config_data = self.config.load_config()
            
            if format == 'simple':
                print("✅ Status: Running" if self.is_monitoring else "📊 Status: Stopped")
                print(f"📋 Blocked domains: {len(config_data.get('blocked_domains', []))}")
                print(f"🔍 Check interval: {config_data.get('check_interval', 30)}s")
                print(f"🎯 Monitoring: {'Enabled' if config_data.get('monitoring_enabled', True) else 'Disabled'}")
                print(f"💻 Platform: Windows")
            else:
                print(json.dumps(config_data, indent=2))
                
        except Exception as e:
            print(f"❌ Error getting status: {e}")
            raise
            
    def open_config(self):
        """Open configuration with Windows-specific editor"""
        try:
            config_path = self.config.get_config_path()
            
            if not os.path.exists(config_path):
                # Create default config
                self.config.save_config(self.config.default_config)
                
            # Open with Windows default editor
            if os.name == 'nt':  # Windows
                os.system(f'notepad "{config_path}"')
            else:
                # Cross-platform fallback
                os.system(f'xdg-open "{config_path}"')
                
        except Exception as e:
            print(f"❌ Error opening configuration: {e}")
            raise
            
    def get_platform_info(self) -> Dict[str, Any]:
        """Get Windows-specific platform information"""
        return {
            "platform": "windows",
            "os_name": "Windows",
            "config_path": str(self.config.get_config_path()),
            "is_monitoring": self.is_monitoring,
            "features": [
                "system_tray",
                "windows_notifications",
                "registry_startup",
                "taskbar_integration"
            ]
        }
