"""
Tests for the config loader in core.

This module contains unit tests for the ConfigurationLoader class.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from focus_guard.core.config.loader import (
    ConfigurationLoader, 
    DomainCategoriesConfig, 
    BlockingConfig, 
    WhitelistConfig, 
    YouTubeConfig, 
    CacheConfig
)


class TestConfigurationLoader(unittest.TestCase):
    """Tests for the ConfigurationLoader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)
        
        # Create test configuration files
        self._create_test_config_files()
        
        # Create the config loader
        self.config_loader = ConfigurationLoader(config_path=str(self.config_dir / "app_config.json"))
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def _create_test_config_files(self):
        """Create test configuration files."""
        # Create domain categories config
        domain_categories = {
            "work": ["github.com", "gitlab.com", "jira.com"],
            "social": ["facebook.com", "twitter.com", "instagram.com"],
            "entertainment": ["youtube.com", "netflix.com", "hulu.com"],
            "shopping": ["amazon.com", "ebay.com", "etsy.com"],
            "news": ["nytimes.com", "cnn.com", "bbc.com"]
        }
        
        with open(self.config_dir / "domain_categories.json", "w") as f:
            json.dump(domain_categories, f)
        
        # Create blocking config
        blocking_config = {
            "blocked_categories": ["social", "entertainment", "shopping"],
            "whitelist": ["github.com", "gitlab.com"],
            "focus_mode_categories": {
                "work": ["social", "entertainment", "shopping"],
                "study": ["social", "entertainment", "shopping", "news"]
            }
        }
        
        with open(self.config_dir / "blocking.json", "w") as f:
            json.dump(blocking_config, f)
        
        # Create hosts file path config
        hosts_config = {
            "hosts_file_path": "/path/to/hosts"
        }
        
        with open(self.config_dir / "hosts.json", "w") as f:
            json.dump(hosts_config, f)
        
        # Create YouTube config
        youtube_config = {
            "enabled": True,
            "classification_method": "machine_learning",
            "block_categories": ["music", "gaming"]
        }
        
        with open(self.config_dir / "youtube.json", "w") as f:
            json.dump(youtube_config, f)
        
        # Create cache config
        cache_config = {
            "enabled": True,
            "ttl_seconds": 3600
        }
        
        with open(self.config_dir / "cache.json", "w") as f:
            json.dump(cache_config, f)
        
        # Create main app_config.json that the ConfigurationLoader expects
        app_config = {
            "domain_categories": domain_categories,
            "blocking": blocking_config,
            "whitelist": {"domains": ["github.com", "gitlab.com"]},
            "exclusion": {
                "use_stevenblack_hosts": True,
                "custom_excluded_domains": []
            },
            "youtube": youtube_config,
            "cache": cache_config
        }
        
        with open(self.config_dir / "app_config.json", "w") as f:
            json.dump(app_config, f)
    
    def test_get_domain_categories(self):
        """Test getting domain categories."""
        # Get domain categories using property
        domain_categories = self.config_loader.domain_categories
        
        # Verify the domain categories
        self.assertIsInstance(domain_categories, DomainCategoriesConfig)
        
        # Check specific categories
        work_domains = domain_categories.get_domains_for_category("work")
        self.assertIn("github.com", work_domains)
        self.assertIn("gitlab.com", work_domains)
        
        social_domains = domain_categories.get_domains_for_category("social")
        self.assertIn("facebook.com", social_domains)
        self.assertIn("twitter.com", social_domains)
        
        # Check category lookup
        category = domain_categories.get_category_for_domain("github.com")
        self.assertEqual(category, "work")
    
    def test_get_blocked_categories(self):
        """Test getting blocked categories."""
        # Get blocked categories using blocking property
        blocking_config = self.config_loader.blocking
        
        # Verify the blocked categories
        self.assertIsInstance(blocking_config, BlockingConfig)
        self.assertIsInstance(blocking_config.blocked_categories, list)
        self.assertIn("social", blocking_config.blocked_categories)
        self.assertIn("entertainment", blocking_config.blocked_categories)
        self.assertNotIn("work", blocking_config.blocked_categories)
        self.assertNotIn("news", blocking_config.blocked_categories)
    
    def test_get_whitelist(self):
        """Test getting whitelist."""
        # Get whitelist using property
        whitelist = self.config_loader.whitelist
        
        # Verify the whitelist
        self.assertIsInstance(whitelist, WhitelistConfig)
        self.assertIsInstance(whitelist.domains, list)
        self.assertIn("github.com", whitelist.domains)
        self.assertIn("gitlab.com", whitelist.domains)
        self.assertNotIn("facebook.com", whitelist.domains)
    
    def test_get_youtube_config(self):
        """Test getting YouTube configuration."""
        # Get YouTube config using property
        youtube_config = self.config_loader.youtube
        
        # Verify the YouTube config
        self.assertIsInstance(youtube_config, YouTubeConfig)
        self.assertIsInstance(youtube_config.enabled, bool)
        self.assertIsInstance(youtube_config.classification_method, str)
        self.assertIsInstance(youtube_config.block_categories, list)
        self.assertIn("music", youtube_config.block_categories)
        self.assertIn("gaming", youtube_config.block_categories)
    
    def test_get_cache_config(self):
        """Test getting cache configuration."""
        # Get cache config using property
        cache_config = self.config_loader.cache
        
        # Verify the cache config
        self.assertIsInstance(cache_config, CacheConfig)
        self.assertIsInstance(cache_config.enabled, bool)
        self.assertIsInstance(cache_config.ttl_seconds, int)
        self.assertTrue(cache_config.enabled)
        self.assertEqual(cache_config.ttl_seconds, 3600)
    
    def test_reload(self):
        """Test reloading the configuration."""
        # Get initial domain categories
        initial_categories = self.config_loader.domain_categories
        
        # Wait a bit to ensure file modification time difference
        import time
        time.sleep(0.1)
        
        # Modify the configuration file with new data
        config_file = self.config_dir / "domain_categories.json"
        with open(config_file, "w") as f:
            json.dump({
                "work": ["github.com", "gitlab.com", "jira.com", "confluence.com"],
                "social": ["facebook.com", "twitter.com", "instagram.com", "linkedin.com"]
            }, f)
        
        # Also update the main app_config.json to include the new domain categories
        app_config_file = self.config_dir / "app_config.json"
        with open(app_config_file, "r") as f:
            app_config = json.load(f)
        
        app_config["domain_categories"] = {
            "work": ["github.com", "gitlab.com", "jira.com", "confluence.com"],
            "social": ["facebook.com", "twitter.com", "instagram.com", "linkedin.com"]
        }
        
        with open(app_config_file, "w") as f:
            json.dump(app_config, f)
        
        # Reload the configuration
        self.config_loader.reload()
        
        # Get updated domain categories
        updated_categories = self.config_loader.domain_categories
        
        # Verify the categories were updated
        work_domains = updated_categories.get_domains_for_category("work")
        self.assertIn("confluence.com", work_domains)
        
        social_domains = updated_categories.get_domains_for_category("social")
        self.assertIn("linkedin.com", social_domains)
    
    def test_missing_config_file(self):
        """Test behavior when a config file is missing."""
        # Create a config loader with a nonexistent config file
        config_loader = ConfigurationLoader(config_path="/nonexistent/directory/config.json")
        
        # Get domain categories using property
        domain_categories = config_loader.domain_categories
        
        # Verify that default config is used
        self.assertIsInstance(domain_categories, DomainCategoriesConfig)
    
    def test_invalid_json(self):
        """Test behavior when a config file contains invalid JSON."""
        # Create a file with invalid JSON
        invalid_config_path = self.config_dir / "invalid.json"
        with open(invalid_config_path, "w") as f:
            f.write("This is not valid JSON")
        
        # Create a config loader that tries to load the invalid file
        # The current implementation returns None for config sections when JSON is invalid
        config_loader = ConfigurationLoader(config_path=str(invalid_config_path))
        
        # Since the JSON is invalid, the config sections will be None
        # This tests the current behavior - the loader fails gracefully but doesn't provide fallback
        domain_categories = config_loader.domain_categories
        
        # Current implementation returns None when config loading fails
        self.assertIsNone(domain_categories)
    
    def test_default_config_dir(self):
        """Test using the default config directory."""
        # Create a config loader with the default config directory
        with patch("os.path.exists", return_value=True):
            with patch("os.path.join", return_value="/default/config/dir"):
                with patch("builtins.open", mock_open(read_data="{}")):
                    config_loader = ConfigurationLoader(config_path="/default/config/dir/app_config.json")
                    
                    # Verify that the config loader was created successfully
                    self.assertIsInstance(config_loader, ConfigurationLoader)


if __name__ == "__main__":
    unittest.main()
