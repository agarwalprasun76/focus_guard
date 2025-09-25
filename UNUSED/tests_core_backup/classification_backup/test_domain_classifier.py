"""
Tests for the domain classifier in core.

This module contains unit tests for the StandardDomainClassifier class.
"""

import unittest
from unittest.mock import MagicMock, patch

from focus_guard.core.domain.models import Domain, Category
from focus_guard.core.classification.domain_classifier import StandardDomainClassifier
from focus_guard.core.config.loader import ConfigurationLoader


class TestStandardDomainClassifier(unittest.TestCase):
    """Tests for the StandardDomainClassifier class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config loader
        self.mock_config_loader = MagicMock(spec=ConfigurationLoader)
        
        # Configure the mock to return test domain categories
        domain_categories = {
            "work": ["github.com", "gitlab.com", "jira.com"],
            "social": ["facebook.com", "twitter.com", "instagram.com"],
            "entertainment": ["youtube.com", "netflix.com", "hulu.com"],
            "shopping": ["amazon.com", "ebay.com", "etsy.com"],
            "news": ["nytimes.com", "cnn.com", "bbc.com"]
        }
        # Create a mock object with a categories attribute
        self.mock_config_loader.domain_categories = MagicMock()
        self.mock_config_loader.domain_categories.categories = domain_categories
        
        # Create the classifier with the mock config loader
        self.classifier = StandardDomainClassifier(self.mock_config_loader)
    
    def test_classify_exact_match(self):
        """Test classification with exact domain matches."""
        # Test work category
        domain = Domain("github.com")
        category = self.classifier.classify(domain)
        self.assertEqual(category, Category.PRODUCTIVITY)
        
        # Test social category
        domain = Domain("facebook.com")
        category = self.classifier.classify(domain)
        self.assertEqual(category, Category.SOCIAL_MEDIA)
        
        # Test entertainment category
        domain = Domain("youtube.com")
        category = self.classifier.classify(domain)
        self.assertEqual(category, Category.ENTERTAINMENT)
    
    def test_classify_subdomain_match(self):
        """Test classification with subdomain matches."""
        # Test work category with subdomain
        domain = Domain("docs.github.com")
        category = self.classifier.classify(domain)
        self.assertEqual(category, Category.PRODUCTIVITY)
        
        # Test social category with subdomain
        domain = Domain("mobile.twitter.com")
        category = self.classifier.classify(domain)
        self.assertEqual(category, Category.SOCIAL_MEDIA)
    
    def test_classify_no_match(self):
        """Test classification with no matching domain."""
        domain = Domain("example.com")
        category = self.classifier.classify(domain)
        self.assertIsNone(category)
    
    def test_classify_with_www(self):
        """Test classification with www prefix."""
        domain = Domain("www.github.com")
        category = self.classifier.classify(domain)
        self.assertEqual(category, Category.PRODUCTIVITY)
    
    def test_name_property(self):
        """Test the name property."""
        self.assertEqual(self.classifier.name, "standard_domain_classifier")
    
    def test_config_reload(self):
        """Test that the classifier reloads configuration."""
        # Initial classification
        domain = Domain("github.com")
        category = self.classifier.classify(domain)
        self.assertEqual(category, Category.PRODUCTIVITY)
        
        # Change the mock config to return different categories
        updated_categories = {
            "work": ["gitlab.com", "jira.com"],  # github.com removed
            "social": ["facebook.com", "twitter.com", "instagram.com"],
            "entertainment": ["youtube.com", "netflix.com", "hulu.com", "github.com"],  # github.com added here
        }
        # Update the categories on the mock
        self.mock_config_loader.domain_categories.categories = updated_categories
        
        # Simulate a configuration change by calling the registered callback
        # First, get the registered callback
        callback = self.mock_config_loader.register_change_callback.call_args[0][0]
        
        # Call the callback to simulate a config change
        callback()
        
        # Now github.com should be classified as entertainment
        category = self.classifier.classify(domain)
        self.assertEqual(category, Category.ENTERTAINMENT)


if __name__ == "__main__":
    unittest.main()
