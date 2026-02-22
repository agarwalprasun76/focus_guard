"""
Windows Configuration Module for Focus Guard MVP
Simple JSON-based configuration management for Windows

As of Section 7 consolidation, blocked_domains are read from DomainConfigManager
(domain_config.json) instead of being hardcoded here.
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _get_blocked_domains_from_manager() -> List[str]:
    """Get blocked domains from DomainConfigManager."""
    try:
        from focus_guard.core.domain.domain_config_manager import (
            get_domain_config_manager,
            CATEGORY_TO_ENUM,
        )
        mgr = get_domain_config_manager()
        blocked_cats = mgr.get_blocked_categories()
        domains = []
        for cat, cat_domains in mgr.get_domain_categories().items():
            enum_cat = CATEGORY_TO_ENUM.get(cat, cat.upper())
            if enum_cat in blocked_cats:
                domains.extend(cat_domains)
        return domains
    except Exception as e:
        logger.debug(f"Could not get blocked domains from DomainConfigManager: {e}")
        # Fallback to hardcoded defaults
        return [
            "facebook.com", "youtube.com", "twitter.com", "instagram.com",
            "tiktok.com", "reddit.com", "netflix.com", "twitch.tv"
        ]


class WindowsConfig:
    """Windows-specific configuration management"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize Windows configuration"""
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Use Windows-specific path
            self.config_path = Path.home() / 'AppData' / 'Local' / 'FocusGuard' / 'config.json'
        
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def default_config(self) -> Dict[str, Any]:
        """Default Windows configuration.
        
        Note: blocked_domains are loaded from DomainConfigManager when available.
        """
        return {
            "monitoring_enabled": True,
            "check_interval": 30,
            "blocked_domains": _get_blocked_domains_from_manager(),
            "allowed_apps": [
                "notepad.exe",
                "chrome.exe",
                "firefox.exe",
                "code.exe",
                "devenv.exe",
                "pycharm64.exe",
                "idea64.exe",
                "outlook.exe",
                "teams.exe"
            ],
            "notification_enabled": True,
            "auto_start": True,
            "minimize_to_tray": True,
            "log_level": "INFO",
            "max_log_size_mb": 10,
            "log_retention_days": 7,
            "windows_specific": {
                "use_windows_notifications": True,
                "registry_startup": True,
                "taskbar_integration": True,
                "system_tray": True
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config
            else:
                # Create default config
                config = self.default_config
                self.save_config(config)
                return config
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
            return self.default_config
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except (IOError, OSError) as e:
            print(f"Error saving config: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update specific configuration values"""
        try:
            config = self.load_config()
            config.update(updates)
            return self.save_config(config)
        except Exception as e:
            print(f"Error updating config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get specific configuration value"""
        config = self.load_config()
        return config.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """Set specific configuration value"""
        try:
            config = self.load_config()
            config[key] = value
            return self.save_config(config)
        except Exception as e:
            print(f"Error setting config value: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """Reset configuration to default values"""
        return self.save_config(self.default_config)
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure"""
        required_keys = ["monitoring_enabled", "check_interval", "blocked_domains"]
        
        for key in required_keys:
            if key not in config:
                return False
        
        # Validate types
        if not isinstance(config["monitoring_enabled"], bool):
            return False
        if not isinstance(config["check_interval"], int) or config["check_interval"] <= 0:
            return False
        if not isinstance(config["blocked_domains"], list):
            return False
        
        return True
    
    def get_config_path(self) -> str:
        """Get configuration file path"""
        return str(self.config_path)
    
    def create_config_template(self) -> str:
        """Create configuration template for user editing.
        
        Note: Blocked domains are now managed via DomainConfigManager
        (C:\\ProgramData\\FocusGuard\\domain_config.json).
        """
        template = """# Focus Guard Windows Configuration
# Edit this file to customize your experience

# Basic Settings
monitoring_enabled: true
check_interval: 30  # seconds between checks

# Blocked domains are now managed centrally in:
# C:\\ProgramData\\FocusGuard\\domain_config.json
# Use the Settings dialog or API to modify blocked domains.

# Allowed applications (these won't be blocked)
allowed_apps:
  - notepad.exe
  - chrome.exe
  - code.exe
  - outlook.exe

# Windows-specific settings
windows_specific:
  use_windows_notifications: true
  system_tray: true
  auto_start: true
"""
        return template
