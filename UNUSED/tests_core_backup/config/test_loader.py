"""
Tests for the config loader in core_v2.

This module contains unit tests for the ConfigurationLoader class.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from core_v2.config.loader import ConfigurationLoader


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
        self.config_loader = ConfigurationLoader(config_dir=str(self.config_dir))
    
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
    
    def test_get_domain_categories(self):
        """Test getting domain categories."""
        # Get domain categories
        domain_categories = self.config_loader.get_domain_categories()
        
        # Verify the domain categories
        self.assertIn("work", domain_categories)
        self.assertIn("social", domain_categories)
        self.assertIn("entertainment", domain_categories)
        self.assertIn("shopping", domain_categories)
        self.assertIn("news", domain_categories)
        
        self.assertIn("github.com", domain_categories["work"])
        self.assertIn("facebook.com", domain_categories["social"])
        self.assertIn("youtube.com", domain_categories["entertainment"])
        self.assertIn("amazon.com", domain_categories["shopping"])
        self.assertIn("nytimes.com", domain_categories["news"])
    
    def test_get_blocked_categories(self):
        """Test getting blocked categories."""
        # Get blocked categories
        blocked_categories = self.config_loader.get_blocked_categories()
        
        # Verify the blocked categories
        self.assertIn("social", blocked_categories)
        self.assertIn("entertainment", blocked_categories)
        self.assertIn("shopping", blocked_categories)
        self.assertNotIn("work", blocked_categories)
        self.assertNotIn("news", blocked_categories)
    
    def test_get_whitelist(self):
        """Test getting whitelist."""
        # Get whitelist
        whitelist = self.config_loader.get_whitelist()
        
        # Verify the whitelist
        self.assertIn("github.com", whitelist)
        self.assertIn("gitlab.com", whitelist)
        self.assertNotIn("facebook.com", whitelist)
    
    def test_get_focus_mode_categories(self):
        """Test getting focus mode categories."""
        # Get focus mode categories
        focus_mode_categories = self.config_loader.get_focus_mode_categories()
        
        # Verify the focus mode categories
        self.assertIn("work", focus_mode_categories)
        self.assertIn("study", focus_mode_categories)
        
        self.assertIn("social", focus_mode_categories["work"])
        self.assertIn("entertainment", focus_mode_categories["work"])
        self.assertIn("shopping", focus_mode_categories["work"])
        self.assertNotIn("news", focus_mode_categories["work"])
        
        self.assertIn("social", focus_mode_categories["study"])
        self.assertIn("entertainment", focus_mode_categories["study"])
        self.assertIn("shopping", focus_mode_categories["study"])
        self.assertIn("news", focus_mode_categories["study"])
    
    def test_get_hosts_file_path(self):
        """Test getting hosts file path."""
        # Get hosts file path
        hosts_file_path = self.config_loader.get_hosts_file_path()
        
        # Verify the hosts file path
        self.assertEqual(hosts_file_path, "/path/to/hosts")
    
    def test_reload(self):
        """Test reloading the configuration."""
        # Get initial domain categories
        initial_categories = self.config_loader.get_domain_categories()
        self.assertIn("github.com", initial_categories["work"])
        
        # Update the domain categories config
        updated_domain_categories = {
            "work": ["gitlab.com", "jira.com"],  # github.com removed
            "social": ["facebook.com", "twitter.com", "instagram.com"],
            "entertainment": ["youtube.com", "netflix.com", "hulu.com", "github.com"],  # github.com added here
            "shopping": ["amazon.com", "ebay.com", "etsy.com"],
            "news": ["nytimes.com", "cnn.com", "bbc.com"]
        }
        
        with open(self.config_dir / "domain_categories.json", "w") as f:
            json.dump(updated_domain_categories, f)
        
        # Reload the configuration
        self.config_loader.reload()
        
        # Get updated domain categories
        updated_categories = self.config_loader.get_domain_categories()
        
        # Verify that github.com is now in entertainment, not work
        self.assertNotIn("github.com", updated_categories["work"])
        self.assertIn("github.com", updated_categories["entertainment"])
    
    def test_missing_config_file(self):
        """Test behavior when a config file is missing."""
        # Create a config loader with a nonexistent config directory
        config_loader = ConfigurationLoader(config_dir="/nonexistent/directory")
        
        # Get domain categories
        domain_categories = config_loader.get_domain_categories()
        
        # Verify that an empty dict is returned
        self.assertEqual(domain_categories, {})
    
    def test_invalid_json(self):
        """Test behavior when a config file contains invalid JSON."""
        # Create a file with invalid JSON
        with open(self.config_dir / "invalid.json", "w") as f:
            f.write("This is not valid JSON")
        
        # Create a config loader that tries to load the invalid file
        with patch("core_v2.config.loader.CONFIG_FILES", {"test_config": "invalid.json"}):
            config_loader = ConfigurationLoader(config_dir=str(self.config_dir))
            
            # Try to get the test config
            result = config_loader._load_config("test_config")
            
            # Verify that an empty dict is returned
            self.assertEqual(result, {})
    
    def test_default_config_dir(self):
        """Test using the default config directory."""
        # Create a config loader with the default config directory
        with patch("os.path.exists", return_value=True):
            with patch("os.path.join", return_value="/default/config/dir"):
                with patch("core_v2.config.loader.open", mock_open(read_data="{}")):
                    config_loader = ConfigurationLoader()
                    
                    # Verify that the config directory is set correctly
                    self.assertEqual(config_loader._config_dir, "/default/config/dir")


if __name__ == "__main__":
    unittest.main()
