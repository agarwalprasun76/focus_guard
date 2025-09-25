"""
Integration tests for the core_v2 module.

This module contains integration tests that verify the interaction
between different components of the core_v2 module.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path

from core_v2.api import ClassifierBlockerAPI
from core_v2.domain.models import Category
from core_v2.config.loader import ConfigurationLoader


class TestCoreV2Integration(unittest.TestCase):
    """Integration tests for the core_v2 module."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name) / "config"
        self.config_dir.mkdir(exist_ok=True, parents=True)
        
        # Ensure the config directory has the correct permissions
        os.chmod(self.temp_dir.name, 0o755)  # rwxr-xr-x
        os.chmod(str(self.config_dir), 0o755)  # rwxr-xr-x
        
        # Create test configuration files
        self._create_test_config_files()
        
        # Create a real API instance
        self.api = ClassifierBlockerAPI()
        
        # Replace the API's config loader with one that uses our test config
        # Use a specific config file path, not just the directory
        config_file_path = str(self.config_dir / "config.json")
        self.api._config_loader = ConfigurationLoader(config_path=config_file_path)
        
        # Reload the configuration to use our test config
        self.api.reload_configuration()
    
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
        
        # Create domain categories file with proper permissions
        domain_categories_path = self.config_dir / "domain_categories.json"
        with open(domain_categories_path, "w") as f:
            json.dump(domain_categories, f)
        os.chmod(str(domain_categories_path), 0o644)  # rw-r--r--
        
        # Create blocking config
        blocking_config = {
            "blocked_categories": ["social", "entertainment", "shopping"],
            "whitelist": ["github.com", "gitlab.com"],
            "focus_mode_categories": {
                "work": ["social", "entertainment", "shopping"],
                "study": ["social", "entertainment", "shopping", "news"]
            }
        }
        
        # Create blocking config file with proper permissions
        blocking_config_path = self.config_dir / "blocking.json"
        with open(blocking_config_path, "w") as f:
            json.dump(blocking_config, f)
        os.chmod(str(blocking_config_path), 0o644)  # rw-r--r--
    
    def test_classify_and_block_workflow(self):
        """Test the full classify and block workflow."""
        # Test classification of domains
        self.assertEqual(self.api.classify_domain("github.com"), Category.PRODUCTIVITY)
        self.assertEqual(self.api.classify_domain("facebook.com"), Category.SOCIAL_MEDIA)
        self.assertEqual(self.api.classify_domain("youtube.com"), Category.ENTERTAINMENT)
        
        # Test blocking of domains
        self.assertFalse(self.api.should_block_tab("https://github.com"))  # Whitelisted
        self.assertTrue(self.api.should_block_tab("https://facebook.com"))  # Social media
        
        # YouTube blocking is context-dependent, so we need to provide entertainment context
        entertainment_metadata = {
            "title": "Funny Cat Videos",
            "description": "A compilation of funny cat videos",
            "type": "youtube",
            "video_id": "67890"
        }
        self.assertTrue(self.api.should_block_tab("https://youtube.com", entertainment_metadata))  # Entertainment
        
        # Test getting blocking reasons
        self.assertIsNone(self.api.get_blocking_reason("https://github.com"))
        self.assertIsNotNone(self.api.get_blocking_reason("https://facebook.com"))
        # YouTube blocking reason is context-dependent
        self.assertIsNotNone(self.api.get_blocking_reason("https://youtube.com", entertainment_metadata))
    
    def test_subdomain_classification(self):
        """Test classification of subdomains."""
        # Test that subdomains inherit the category of their parent domain
        self.assertEqual(self.api.classify_domain("docs.github.com"), Category.PRODUCTIVITY)
        self.assertEqual(self.api.classify_domain("mobile.twitter.com"), Category.SOCIAL_MEDIA)
        
        # Test blocking of subdomains
        self.assertFalse(self.api.should_block_tab("https://docs.github.com"))  # Whitelisted
        self.assertTrue(self.api.should_block_tab("https://mobile.twitter.com"))  # Social media
    
    def test_context_aware_classification(self):
        """Test context-aware classification."""
        # Create a context with metadata for educational content
        educational_context = {
            "url": "https://www.youtube.com/watch?v=12345",
            "metadata": {
                "title": "Educational Video",
                "description": "This is an educational video about programming",
                "type": "youtube",
                "video_id": "12345"
            }
        }
        
        # Test classification with educational context
        category = self.api.classify_domain_with_context("youtube.com", educational_context)
        self.assertEqual(category, Category.EDUCATION)  # Educational YouTube content
        
        # Test blocking with educational context - should NOT be blocked
        self.assertFalse(self.api.should_block_tab("https://www.youtube.com/watch?v=12345", educational_context["metadata"]))
        
        # Create a context with metadata for entertainment content
        entertainment_context = {
            "url": "https://www.youtube.com/watch?v=67890",
            "metadata": {
                "title": "Funny Cat Videos",
                "description": "A compilation of funny cat videos",
                "type": "youtube",
                "video_id": "67890"
            }
        }
        
        # Test classification with entertainment context
        category = self.api.classify_domain_with_context("youtube.com", entertainment_context)
        self.assertEqual(category, Category.ENTERTAINMENT)  # Entertainment YouTube content
        
        # Test blocking with entertainment context - should be blocked
        self.assertTrue(self.api.should_block_tab("https://www.youtube.com/watch?v=67890", entertainment_context["metadata"]))
    
    def test_config_reload(self):
        """Test reloading configuration."""
        # Initial classification
        self.assertEqual(self.api.classify_domain("facebook.com"), Category.SOCIAL_MEDIA)
        self.assertTrue(self.api.should_block_tab("https://facebook.com"))
        
        # Update the domain categories config
        domain_categories = {
            "work": ["github.com", "gitlab.com", "jira.com", "facebook.com"],  # Added facebook.com to work
            "social": ["twitter.com", "instagram.com"],  # Removed facebook.com
            "entertainment": ["youtube.com", "netflix.com", "hulu.com"]
        }
        
        with open(self.config_dir / "domain_categories.json", "w") as f:
            json.dump(domain_categories, f)
        
        # Reload the configuration
        self.api.reload_configuration()
        
        # Facebook should now be classified as work and not blocked
        self.assertEqual(self.api.classify_domain("facebook.com"), Category.PRODUCTIVITY)
        self.assertFalse(self.api.should_block_tab("https://facebook.com"))


if __name__ == "__main__":
    unittest.main()
