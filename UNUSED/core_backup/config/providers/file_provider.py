"""
JSON file-based configuration provider.

This module provides a configuration provider implementation that stores
configuration data in JSON files with support for different scopes.
"""

import json
import os
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List
import time

from core_v2.config.interfaces import ConfigProvider, ConfigPath


class JsonFileProvider(ConfigProvider):
    """
    Configuration provider that uses JSON files.
    
    This provider stores configuration data in JSON files with support for
    different scopes (user, system, application).
    """
    
    def __init__(self, file_path: Optional[str] = None, scope: str = "user", user_id: Optional[str] = None):
        """
        Initialize the JSON file provider.
        
        Args:
            file_path: Path to the JSON file. If None, uses default based on scope.
            scope: Scope of the configuration ("user", "system", "app").
            user_id: User ID for user-specific configuration. If None, uses
                environment variable or "default".
        """
        self.scope = scope
        self._config: Dict[str, Any] = {}
        self._last_modified_time = 0
        
        if file_path is None:
            config_dir = self._get_config_dir()
            
            if scope == "user":
                # Use provided user ID, environment variable, or default
                user_id = user_id or os.environ.get("FOCUS_GUARD_USER_ID", "default")
                self.file_path = config_dir / "users" / f"{user_id}.json"
            elif scope == "system":
                self.file_path = config_dir / "system_config.json"
            else:  # app scope
                self.file_path = config_dir / "app_config.json"
        else:
            self.file_path = Path(file_path)
        
        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load initial configuration
        self._load()
    
    def _get_config_dir(self) -> Path:
        """
        Get the default configuration directory.
        
        Returns:
            The default configuration directory path.
        """
        if platform.system() == "Windows":
            base_dir = os.path.expandvars("%APPDATA%")
        elif platform.system() == "Darwin":  # macOS
            base_dir = os.path.expanduser("~/Library/Application Support")
        else:  # Linux and other Unix-like systems
            base_dir = os.path.expanduser("~/.config")
        
        return Path(base_dir) / "focus_guard"
    
    def _load(self) -> None:
        """Load configuration from the file."""
        if not self.file_path.exists():
            # Create empty configuration
            self._config = {}
            self._save()
            self._last_modified_time = time.time()
            return
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            self._last_modified_time = self.file_path.stat().st_mtime
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading configuration from {self.file_path}: {e}")
            # Create empty configuration on error
            self._config = {}
            self._save()
            self._last_modified_time = time.time()
    
    def _save(self) -> bool:
        """
        Save configuration to the file.
        
        Returns:
            True if the save was successful, False otherwise.
        """
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            self._last_modified_time = time.time()
            return True
        except IOError as e:
            print(f"Error saving configuration to {self.file_path}: {e}")
            return False
    
    def _check_for_changes(self) -> bool:
        """
        Check if the configuration file has been modified.
        
        Returns:
            True if the file has been modified, False otherwise.
        """
        if not self.file_path.exists():
            return False
        
        return self.file_path.stat().st_mtime > self._last_modified_time
    
    def _get_value_at_path(self, config: Dict[str, Any], path: ConfigPath, default: Any = None) -> Any:
        """
        Get a value from the configuration by path.
        
        Args:
            config: The configuration dictionary.
            path: The path to the configuration value.
            default: The default value to return if the path doesn't exist.
            
        Returns:
            The configuration value, or the default if not found.
        """
        if not path:
            return config
        
        parts = path.split('.')
        current = config
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        
        return current
    
    def _set_value_at_path(self, config: Dict[str, Any], path: ConfigPath, value: Any) -> bool:
        """
        Set a value in the configuration by path.
        
        Args:
            config: The configuration dictionary.
            path: The path to the configuration value.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        if not path:
            return False
        
        parts = path.split('.')
        current = config
        
        # Navigate to the parent of the target node
        for i, part in enumerate(parts[:-1]):
            if part not in current or not isinstance(current[part], dict):
                # Create missing parent nodes
                current[part] = {}
            current = current[part]
        
        # Set the value at the target node
        current[parts[-1]] = value
        return True
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from the provider.
        
        Returns:
            A dictionary containing the configuration data.
        """
        if self._check_for_changes():
            self._load()
        return self._config.copy()
    
    def save(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to the provider.
        
        Args:
            config: The configuration data to save.
            
        Returns:
            True if the save was successful, False otherwise.
        """
        self._config = config.copy()
        return self._save()
    
    def get_value(self, path: ConfigPath, default: Any = None) -> Any:
        """
        Get a configuration value by path.
        
        Args:
            path: The path to the configuration value.
            default: The default value to return if the path doesn't exist.
            
        Returns:
            The configuration value, or the default if not found.
        """
        if self._check_for_changes():
            self._load()
        return self._get_value_at_path(self._config, path, default)
    
    def set_value(self, path: ConfigPath, value: Any) -> bool:
        """
        Set a configuration value by path.
        
        Args:
            path: The path to the configuration value.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        if self._check_for_changes():
            self._load()
        
        result = self._set_value_at_path(self._config, path, value)
        if result:
            self._save()
        return result


class MultiFileProvider(ConfigProvider):
    """
    Configuration provider that uses multiple JSON files.
    
    This provider supports splitting configuration across multiple files,
    which can be useful for separating different configuration sections
    or for supporting external configuration files.
    """
    
    def __init__(self, base_dir: str, main_file: str = "config.json"):
        """
        Initialize the multi-file provider.
        
        Args:
            base_dir: Base directory for configuration files.
            main_file: Name of the main configuration file.
        """
        self.base_dir = Path(base_dir)
        self.main_file = main_file
        self.main_path = self.base_dir / main_file
        self._config: Dict[str, Any] = {}
        self._file_map: Dict[str, Path] = {}  # Maps section names to file paths
        self._last_modified_times: Dict[Path, float] = {}
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Load initial configuration
        self._load()
    
    def _load(self) -> None:
        """Load configuration from all files."""
        self._config = {}
        
        # Load main configuration file
        if self.main_path.exists():
            try:
                with open(self.main_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                self._last_modified_times[self.main_path] = self.main_path.stat().st_mtime
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading main configuration from {self.main_path}: {e}")
        
        # Load section files based on file map
        for section, file_path in self._file_map.items():
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        section_data = json.load(f)
                        self._config[section] = section_data
                    self._last_modified_times[file_path] = file_path.stat().st_mtime
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading section configuration from {file_path}: {e}")
    
    def _save(self) -> bool:
        """
        Save configuration to all files.
        
        Returns:
            True if all saves were successful, False otherwise.
        """
        success = True
        
        # Save main configuration (excluding sections in file map)
        main_config = {k: v for k, v in self._config.items() if k not in self._file_map}
        try:
            with open(self.main_path, "w", encoding="utf-8") as f:
                json.dump(main_config, f, indent=2, ensure_ascii=False)
            self._last_modified_times[self.main_path] = time.time()
        except IOError as e:
            print(f"Error saving main configuration to {self.main_path}: {e}")
            success = False
        
        # Save section files
        for section, file_path in self._file_map.items():
            if section in self._config:
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(self._config[section], f, indent=2, ensure_ascii=False)
                    self._last_modified_times[file_path] = time.time()
                except IOError as e:
                    print(f"Error saving section configuration to {file_path}: {e}")
                    success = False
        
        return success
    
    def _check_for_changes(self) -> bool:
        """
        Check if any configuration files have been modified.
        
        Returns:
            True if any file has been modified, False otherwise.
        """
        # Check main file
        if self.main_path.exists():
            main_mtime = self.main_path.stat().st_mtime
            if main_mtime > self._last_modified_times.get(self.main_path, 0):
                return True
        
        # Check section files
        for file_path in self._file_map.values():
            if file_path.exists():
                file_mtime = file_path.stat().st_mtime
                if file_mtime > self._last_modified_times.get(file_path, 0):
                    return True
        
        return False
    
    def register_section_file(self, section: str, file_name: str) -> None:
        """
        Register a section to be stored in a separate file.
        
        Args:
            section: The section name.
            file_name: The file name for the section.
        """
        file_path = self.base_dir / file_name
        self._file_map[section] = file_path
        
        # Load the section if the file exists
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    section_data = json.load(f)
                    self._config[section] = section_data
                self._last_modified_times[file_path] = file_path.stat().st_mtime
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading section configuration from {file_path}: {e}")
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from the provider.
        
        Returns:
            A dictionary containing the configuration data.
        """
        if self._check_for_changes():
            self._load()
        return self._config.copy()
    
    def save(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to the provider.
        
        Args:
            config: The configuration data to save.
            
        Returns:
            True if the save was successful, False otherwise.
        """
        self._config = config.copy()
        return self._save()
    
    def get_value(self, path: ConfigPath, default: Any = None) -> Any:
        """
        Get a configuration value by path.
        
        Args:
            path: The path to the configuration value.
            default: The default value to return if the path doesn't exist.
            
        Returns:
            The configuration value, or the default if not found.
        """
        if self._check_for_changes():
            self._load()
        
        if not path:
            return self._config
        
        parts = path.split('.')
        current = self._config
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        
        return current
    
    def set_value(self, path: ConfigPath, value: Any) -> bool:
        """
        Set a configuration value by path.
        
        Args:
            path: The path to the configuration value.
            value: The value to set.
            
        Returns:
            True if the value was set successfully, False otherwise.
        """
        if self._check_for_changes():
            self._load()
        
        if not path:
            return False
        
        parts = path.split('.')
        current = self._config
        
        # Navigate to the parent of the target node
        for i, part in enumerate(parts[:-1]):
            if part not in current or not isinstance(current[part], dict):
                # Create missing parent nodes
                current[part] = {}
            current = current[part]
        
        # Set the value at the target node
        current[parts[-1]] = value
        
        # Save the configuration
        return self._save()
