"""
Configuration loading and management.

This module provides functionality for loading, validating, and accessing
user configuration settings that control the behavior of the system.
"""

import json
import os
import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Callable

# Type alias for configuration change callback functions
ConfigChangeCallback = Callable[[], None]


@dataclass
class ConfigSection:
    """Base class for configuration sections."""
    pass


@dataclass
class DomainCategoriesConfig(ConfigSection):
    """Configuration for domain categories."""
    
    categories: Dict[str, List[str]]
    
    def get_domains_for_category(self, category: str) -> List[str]:
        """
        Get all domains for a specific category.
        
        Args:
            category: The category to get domains for.
            
        Returns:
            A list of domains in the category.
        """
        return self.categories.get(category, [])
    
    def get_category_for_domain(self, domain: str) -> Optional[str]:
        """
        Get the category for a specific domain.
        
        Args:
            domain: The domain to get the category for.
            
        Returns:
            The category of the domain, or None if not found.
        """
        for category, domains in self.categories.items():
            if domain in domains:
                return category
        return None


@dataclass
class WhitelistConfig(ConfigSection):
    """Configuration for domain whitelist."""
    
    domains: List[str]
    
    def is_whitelisted(self, domain: str) -> bool:
        """
        Check if a domain is whitelisted.
        
        Args:
            domain: The domain to check.
            
        Returns:
            True if the domain is whitelisted, False otherwise.
        """
        return domain in self.domains


@dataclass
class BlockingConfig(ConfigSection):
    """Configuration for domain blocking."""
    
    blocked_categories: List[str]
    whitelist: List[str] = None
    
    def is_category_blocked(self, category: str) -> bool:
        """
        Check if a category is blocked.
        
        Args:
            category: The category to check.
            
        Returns:
            True if the category is blocked, False otherwise.
        """
        return category in self.blocked_categories


@dataclass
class ExclusionConfig(ConfigSection):
    """Configuration for domain exclusion."""
    
    use_stevenblack_hosts: bool
    custom_excluded_domains: List[str]
    
    def is_custom_excluded(self, domain: str) -> bool:
        """
        Check if a domain is in the custom exclusion list.
        
        Args:
            domain: The domain to check.
            
        Returns:
            True if the domain is excluded, False otherwise.
        """
        return domain in self.custom_excluded_domains


@dataclass
class YouTubeConfig(ConfigSection):
    """Configuration for YouTube classification."""
    
    enabled: bool
    classification_method: str  # 'rule_based', 'llm', or 'openai'
    block_categories: List[str]
    
    def should_classify_youtube(self) -> bool:
        """
        Check if YouTube classification is enabled.
        
        Returns:
            True if YouTube classification is enabled, False otherwise.
        """
        return self.enabled
    
    def is_youtube_category_blocked(self, category: str) -> bool:
        """
        Check if a YouTube category is blocked.
        
        Args:
            category: The YouTube category to check.
            
        Returns:
            True if the category is blocked, False otherwise.
        """
        return category in self.block_categories


@dataclass
class CacheConfig(ConfigSection):
    """Configuration for caching."""
    
    enabled: bool
    ttl_seconds: int
    
    def should_use_cache(self) -> bool:
        """
        Check if caching is enabled.
        
        Returns:
            True if caching is enabled, False otherwise.
        """
        return self.enabled


class ConfigurationLoader:
    """
    Loads and manages user configuration.
    
    This class is responsible for loading configuration from disk,
    validating it, and providing access to configuration sections.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_path: Optional path to the configuration file.
                If not provided, the default path will be used.
        """
        self._config_path = config_path or self._get_default_config_path()
        self._config: Dict[str, Any] = {}
        self._last_modified_time = 0
        self._change_callbacks: List[ConfigChangeCallback] = []
        
        # Configuration sections
        self._domain_categories: Optional[DomainCategoriesConfig] = None
        self._whitelist: Optional[WhitelistConfig] = None
        self._blocking: Optional[BlockingConfig] = None
        self._exclusion: Optional[ExclusionConfig] = None
        self._youtube: Optional[YouTubeConfig] = None
        self._cache: Optional[CacheConfig] = None
        
        # Load initial configuration
        self.reload()
    
    def _get_default_config_path(self) -> str:
        """
        Get the default path for the configuration file.
        
        Returns:
            The default configuration file path.
        """
        if platform.system() == "Windows":
            base_dir = os.path.expandvars("%APPDATA%")
        else:
            base_dir = os.path.expanduser("~/.config")
        
        return os.path.join(base_dir, "focus_guard", "config.json")
    
    def reload(self) -> bool:
        """
        Reload the configuration from disk.
        
        Returns:
            True if the configuration was reloaded, False otherwise.
        """
        config_path = Path(self._config_path)
        config_dir = config_path.parent
        
        # Check if the main config file exists
        if not config_path.exists():
            # Create default configuration
            self._config = self._get_default_config()
            self._save_config()
            self._last_modified_time = time.time()
            self._parse_config()
            return True
        
        # Check if any config files have been modified
        main_config_modified = config_path.stat().st_mtime > self._last_modified_time
        
        # Check for domain_categories.json
        domain_categories_path = config_dir / "domain_categories.json"
        domain_categories_modified = False
        if domain_categories_path.exists():
            domain_categories_modified = domain_categories_path.stat().st_mtime > self._last_modified_time
        
        # Check for blocking.json
        blocking_path = config_dir / "blocking.json"
        blocking_modified = False
        if blocking_path.exists():
            blocking_modified = blocking_path.stat().st_mtime > self._last_modified_time
        
        # If no files have been modified, return False
        if not (main_config_modified or domain_categories_modified or blocking_modified):
            return False
        
        # Load the main configuration
        try:
            with open(config_path, "r") as f:
                self._config = json.load(f)
            
            # Load domain categories if the file exists
            if domain_categories_path.exists():
                try:
                    with open(domain_categories_path, "r") as f:
                        domain_categories = json.load(f)
                        self._config["domain_categories"] = domain_categories
                        print(f"Loaded domain categories from {domain_categories_path}")
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading domain categories: {e}")
            
            # Load blocking config if the file exists
            if blocking_path.exists():
                try:
                    with open(blocking_path, "r") as f:
                        blocking = json.load(f)
                        self._config["blocking"] = blocking
                        print(f"Loaded blocking config from {blocking_path}")
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading blocking config: {e}")
            
            # Update the last modified time
            self._last_modified_time = time.time()
            
            # Parse the configuration
            self._parse_config()
            
            # Notify change listeners
            self._notify_change()
            
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def _save_config(self) -> bool:
        """
        Save the configuration to disk.
        
        Returns:
            True if the configuration was saved, False otherwise.
        """
        config_path = Path(self._config_path)
        
        # Create parent directories if they don't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, "w") as f:
                json.dump(self._config, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration.
        
        Returns:
            The default configuration dictionary.
        """
        return {
            "domain_categories": {
                "social_media": [
                    "facebook.com",
                    "twitter.com",
                    "instagram.com",
                    "linkedin.com",
                    "reddit.com",
                    "pronto.io"
                ],
                "entertainment": [
                    "youtube.com",
                    "netflix.com",
                    "hulu.com",
                    "disney.com",
                    "twitch.tv"
                ],
                "productivity": [
                    "github.com",
                    "gitlab.com",
                    "bitbucket.org",
                    "stackoverflow.com",
                    "docs.google.com"
                ]
            },
            "whitelist": {
                "domains": []
            },
            "blocking": {
                "blocked_categories": ["social_media", "entertainment"]
            },
            "exclusion": {
                "use_stevenblack_hosts": True,
                "custom_excluded_domains": []
            },
            "youtube": {
                "enabled": True,
                "classification_method": "rule_based",
                "block_categories": ["entertainment", "gaming"]
            },
            "cache": {
                "enabled": True,
                "ttl_seconds": 3600
            }
        }
    
    def _parse_config(self) -> None:
        """Parse the configuration and create section objects."""
        # Domain categories
        categories = self._config.get("domain_categories", {})
        self._domain_categories = DomainCategoriesConfig(categories)
        
        # Whitelist
        whitelist = self._config.get("whitelist", {})
        self._whitelist = WhitelistConfig(whitelist.get("domains", []))
        
        # Blocking
        blocking = self._config.get("blocking", {})
        self._blocking = BlockingConfig(
            blocked_categories=blocking.get("blocked_categories", []),
            whitelist=blocking.get("whitelist", []))
        
        
        # Exclusion
        exclusion = self._config.get("exclusion", {})
        self._exclusion = ExclusionConfig(
            exclusion.get("use_stevenblack_hosts", True),
            exclusion.get("custom_excluded_domains", [])
        )
        
        # YouTube
        youtube = self._config.get("youtube", {})
        self._youtube = YouTubeConfig(
            youtube.get("enabled", True),
            youtube.get("classification_method", "rule_based"),
            youtube.get("block_categories", [])
        )
        
        # Cache
        cache = self._config.get("cache", {})
        self._cache = CacheConfig(
            cache.get("enabled", True),
            cache.get("ttl_seconds", 3600)
        )
    
    def register_change_callback(self, callback: ConfigChangeCallback) -> None:
        """
        Register a callback to be notified when the configuration changes.
        
        Args:
            callback: The callback function to register.
        """
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)
    
    def unregister_change_callback(self, callback: ConfigChangeCallback) -> None:
        """
        Unregister a change callback.
        
        Args:
            callback: The callback function to unregister.
        """
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
    
    def _notify_change(self) -> None:
        """Notify all registered callbacks of a configuration change."""
        for callback in self._change_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error in configuration change callback: {e}")
    
    @property
    def domain_categories(self) -> DomainCategoriesConfig:
        """Get the domain categories configuration."""
        return self._domain_categories
    
    @property
    def whitelist(self) -> WhitelistConfig:
        """Get the whitelist configuration."""
        return self._whitelist
    
    @property
    def blocking(self) -> BlockingConfig:
        """Get the blocking configuration."""
        return self._blocking
        
    def get_blocking_config(self) -> BlockingConfig:
        """Get the blocking configuration.
        
        Returns:
            The blocking configuration.
        """
        return self._blocking
    
    @property
    def exclusion(self) -> ExclusionConfig:
        """Get the exclusion configuration."""
        return self._exclusion
    
    @property
    def youtube(self) -> YouTubeConfig:
        """Get the YouTube configuration."""
        return self._youtube
    
    @property
    def cache(self) -> CacheConfig:
        """Get the cache configuration."""
        return self._cache
    
    def update_config(self, section: str, updates: Dict[str, Any]) -> bool:
        """
        Update a section of the configuration.
        
        Args:
            section: The section to update.
            updates: The updates to apply.
            
        Returns:
            True if the configuration was updated, False otherwise.
        """
        if section not in self._config:
            return False
        
        # Update the configuration
        self._config[section].update(updates)
        
        # Save the configuration
        if self._save_config():
            self._last_modified_time = time.time()
            self._parse_config()
            self._notify_change()
            return True
        
        return False
