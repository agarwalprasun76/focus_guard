"""
ConfigManager: Handles loading, saving, and accessing configuration settings.
Supports multiple user profiles and provides default values when settings are missing.
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
    - Loading configuration from JSON files
    - Saving configuration to JSON files
    - Providing default values for missing settings
    - Supporting multiple user profiles
    - Accessing configuration settings via dot notation
    
    Example usage:
    ```python
    # Initialize with default config directory
    config_manager = ConfigManager()
    
    # Load a specific user's configuration
    user_config = config_manager.load_user_config("user123")
    
    # Access configuration settings
    email_recipient = user_config["alert_system"]["providers"]["email"]["email_recipient"]
    
    # Update configuration settings
    user_config["alert_system"]["cooldown_period"] = 30
    config_manager.save_user_config(user_config)
    ```
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Path to the configuration directory. If None, uses the default.
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
        
        # Path to template config
        self.template_path = self.config_dir / "user_config_template.json"
        
        # Path to users directory
        self.users_dir = self.config_dir / "users"
        self.users_dir.mkdir(exist_ok=True)
        
        # Load template config
        self.template_config = self._load_json_file(self.template_path)
        if not self.template_config:
            self.logger.warning("Template config not found or invalid. Using empty template.")
            self.template_config = {}
            
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
            
    def list_users(self) -> List[str]:
        """
        List all available user IDs.
        
        Returns:
            List of user IDs
        """
        try:
            return [f.stem for f in self.users_dir.glob("*.json")]
        except Exception as e:
            self.logger.error(f"Error listing users: {e}")
            return []
            
    def user_exists(self, user_id: str) -> bool:
        """
        Check if a user configuration exists.
        
        Args:
            user_id: User ID
            
        Returns:
            True if the user configuration exists, False otherwise
        """
        return (self.users_dir / f"{user_id}.json").exists()
            
    def load_user_config(self, user_id: str) -> Dict[str, Any]:
        """
        Load a user's configuration.
        
        Args:
            user_id: User ID
            
        Returns:
            User configuration dict
        """
        # Load user config if it exists
        user_path = self.users_dir / f"{user_id}.json"
        user_config = self._load_json_file(user_path)
        
        # If user config doesn't exist, create a new one based on the template
        if not user_config:
            self.logger.info(f"Creating new configuration for user: {user_id}")
            user_config = copy.deepcopy(self.template_config)
            user_config["user_id"] = user_id
            
            # Save the new user config
            self._save_json_file(user_path, user_config)
            
        return user_config
        
    def save_user_config(self, config: Dict[str, Any]) -> bool:
        """
        Save a user's configuration.
        
        Args:
            config: User configuration dict (must contain "user_id" key)
            
        Returns:
            True if successful, False otherwise
        """
        # Ensure user_id is present
        user_id = config.get("user_id")
        if not user_id:
            self.logger.error("Cannot save user config: missing user_id")
            return False
            
        # Save user config
        user_path = self.users_dir / f"{user_id}.json"
        return self._save_json_file(user_path, config)
        
    def create_user(self, user_id: str, user_name: str, parent_email: str) -> Dict[str, Any]:
        """
        Create a new user configuration.
        
        Args:
            user_id: User ID
            user_name: User's name
            parent_email: Parent's email address
            
        Returns:
            New user configuration dict
        """
        # Check if user already exists
        if self.user_exists(user_id):
            self.logger.warning(f"User {user_id} already exists. Loading existing config.")
            return self.load_user_config(user_id)
            
        # Create new user config based on template
        user_config = copy.deepcopy(self.template_config)
        user_config["user_id"] = user_id
        user_config["user_name"] = user_name
        user_config["parent_email"] = parent_email
        
        # Set email recipient to parent email
        if "alert_system" in user_config and "providers" in user_config["alert_system"] and "email" in user_config["alert_system"]["providers"]:
            user_config["alert_system"]["providers"]["email"]["email_recipient"] = parent_email
        
        # Save new user config
        user_path = self.users_dir / f"{user_id}.json"
        if self._save_json_file(user_path, user_config):
            return user_config
        else:
            return {}
            
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user's configuration.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user_path = self.users_dir / f"{user_id}.json"
            if user_path.exists():
                user_path.unlink()
                return True
            else:
                self.logger.warning(f"User {user_id} does not exist.")
                return False
        except Exception as e:
            self.logger.error(f"Error deleting user {user_id}: {e}")
            return False
            
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration template.
        
        Returns:
            Default configuration dict
        """
        return copy.deepcopy(self.template_config)
        
    def update_template(self, new_template: Dict[str, Any]) -> bool:
        """
        Update the template configuration.
        
        Args:
            new_template: New template configuration
            
        Returns:
            True if successful, False otherwise
        """
        if self._save_json_file(self.template_path, new_template):
            self.template_config = new_template
            return True
        return False
        
    def get_app_config(self) -> Dict[str, Any]:
        """
        Get the global application configuration.
        
        Returns:
            Application configuration dict
        """
        app_config_path = self.config_dir / "app_config.json"
        app_config = self._load_json_file(app_config_path)
        
        # If app config doesn't exist, create a default one
        if not app_config:
            app_config = {
                "smtp_defaults": {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "smtp_username": "focusguardapp@gmail.com",
                    "use_tls": True,
                    "from_name": "FocusGuard App"
                },
                "data_directory": str(Path.home() / ".focusguard"),
                "log_level": "INFO",
                "default_check_interval": 10,
                "default_session_duration": 3600
            }
            self._save_json_file(app_config_path, app_config)
            
        return app_config
        
    def save_app_config(self, app_config: Dict[str, Any]) -> bool:
        """
        Save the global application configuration.
        
        Args:
            app_config: Application configuration dict
            
        Returns:
            True if successful, False otherwise
        """
        app_config_path = self.config_dir / "app_config.json"
        return self._save_json_file(app_config_path, app_config)
