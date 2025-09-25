"""
ConfigManager: Handles loading, saving, and accessing configuration settings.
Provides a simple interface for working with the application configuration.
"""
import os
import json
import copy
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from core.logger.logger import get_logger

class ConfigManager:
    """
    Configuration manager for FocusGuard.
    
    Handles:
    - Loading configuration from JSON file
    - Saving configuration to JSON file
    - Providing default values for missing settings
    - Accessing configuration settings
    
    Example usage:
    ```python
    # Initialize with default config directory
    config_manager = ConfigManager()
    
    # Load the configuration
    config = config_manager.load_config()
    
    # Access configuration settings
    email_recipient = config["alert_system"]["providers"]["email"]["email_recipient"]
    
    # Update configuration settings
    config["alert_system"]["cooldown_period"] = 30
    config_manager.save_config(config)
    ```
    """
    
    def __init__(self, config_dir: Optional[str] = None, config_file: str = "focus_guard_config.json"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Path to the configuration directory. If None, uses the default.
            config_file: Name of the configuration file
        """
        # Set up logger
        self.logger = get_logger("config_manager")
        
        # Set configuration directory
        if config_dir is None:
            # Use default config directory
            self.config_dir = Path(os.path.abspath(os.path.join(
                os.path.dirname(__file__), '..', '..', 'config'
            )))
        else:
            self.config_dir = Path(config_dir)
            
        self.logger.debug(f"Using config directory: {self.config_dir}")
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        # Set configuration file path
        self.config_file = self.config_dir / config_file
        
        # Default configuration
        self.default_config = {
            "user": {
                "name": "Default User",
                "parent_email": "parent@example.com"
            },
            "alert_system": {
                "cooldown_period": 60,
                "escalation_threshold": 3,
                "escalation_window": 300,
                "providers": {
                    "popup": {
                        "enabled": True,
                        "popup_duration": 10
                    },
                    "sound": {
                        "enabled": True,
                        "volume": 0.8,
                        "repeat_count": 2,
                        "repeat_interval": 0.5
                    },
                    "email": {
                        "enabled": True,
                        "email_recipient": "",
                        "smtp_server": "smtp.gmail.com",
                        "smtp_port": 587,
                        "smtp_username": "focusguardapp@gmail.com",
                        "smtp_password": "",
                        "use_tls": True,
                        "from_name": "FocusGuard App",
                        "subject_prefix": "FocusGuard Alert",
                        "max_emails_per_day": 5,
                        "include_screenshot": True
                    }
                }
            },
            "distraction_detection": {
                "allowed_apps": ["Windsurf.exe", "code.exe", "explorer.exe", "notepad.exe"],
                "distraction_thresholds": {
                    "default": 10,
                    "social_media": 5,
                    "games": 5,
                    "video_streaming": 10
                },
                "categories": {
                    "social_media": [
                        "facebook.com",
                        "twitter.com",
                        "instagram.com",
                        "tiktok.com",
                        "snapchat.com"
                    ],
                    "games": [
                        "steam.exe",
                        "epicgameslauncher.exe",
                        "robloxplayer.exe",
                        "minecraft.exe"
                    ],
                    "video_streaming": [
                        "youtube.com",
                        "netflix.com",
                        "hulu.com",
                        "disney+",
                        "twitch.tv"
                    ]
                }
            },
            "monitoring": {
                "check_interval": 10,
                "session_duration": 3600,
                "screenshot_enabled": True,
                "screenshot_interval": 300
            },
            "data_storage": {
                "log_level": "INFO",
                "log_to_file": True,
                "history_retention_days": 30,
                "data_directory": ""
            }
        }
            
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Dict containing the JSON data, or empty dict if file doesn't exist or is invalid
        """
        try:
            if not file_path.exists():
                self.logger.warning(f"File not found: {file_path}")
                return {}
                
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in file: {file_path}")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading file {file_path}: {e}")
            return {}
            
    def _save_json_file(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """
        Save data to a JSON file.
        
        Args:
            file_path: Path to the JSON file
            data: Data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Error saving file {file_path}: {e}")
            return False
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load the configuration.
        
        Returns:
            Configuration dict
        """
        # Load config if it exists
        config = self._load_json_file(self.config_file)
        
        # If config doesn't exist, create a new one based on the default
        if not config:
            self.logger.info(f"Creating new configuration file: {self.config_file}")
            config = copy.deepcopy(self.default_config)
            
            # Save the new config
            self._save_json_file(self.config_file, config)
            
        return config
        
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save the configuration.
        
        Args:
            config: Configuration dict
            
        Returns:
            True if successful, False otherwise
        """
        return self._save_json_file(self.config_file, config)
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration.
        
        Returns:
            Default configuration dict
        """
        return copy.deepcopy(self.default_config)
    
    def reset_config(self) -> Dict[str, Any]:
        """
        Reset the configuration to default values.
        
        Returns:
            Default configuration dict
        """
        default_config = self.get_default_config()
        self.save_config(default_config)
        return default_config
    
    def get_config_path(self) -> Path:
        """
        Get the path to the configuration file.
        
        Returns:
            Path to the configuration file
        """
        return self.config_file
    
    def update_config_value(self, key_path: str, value: Any) -> bool:
        """
        Update a specific configuration value by its path.
        
        Args:
            key_path: Path to the configuration value (e.g., "alert_system.providers.email.enabled")
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load current config
            config = self.load_config()
            
            # Split the path into parts
            parts = key_path.split(".")
            
            # Navigate to the parent of the target
            current = config
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
                
            # Set the value
            current[parts[-1]] = value
            
            # Save the updated config
            return self.save_config(config)
        except Exception as e:
            self.logger.error(f"Error updating config value at {key_path}: {e}")
            return False
    
    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get a specific configuration value by its path.
        
        Args:
            key_path: Path to the configuration value (e.g., "alert_system.providers.email.enabled")
            default: Default value to return if the path doesn't exist
            
        Returns:
            Configuration value, or default if the path doesn't exist
        """
        try:
            # Load current config
            config = self.load_config()
            
            # Split the path into parts
            parts = key_path.split(".")
            
            # Navigate to the target
            current = config
            for part in parts:
                if not isinstance(current, dict) or part not in current:
                    return default
                current = current[part]
                
            return current
        except Exception as e:
            self.logger.error(f"Error getting config value at {key_path}: {e}")
            return default
