"""
Tests for the compatibility layer in core_v2.

This module contains unit tests for the compatibility functions and classes
that ease the transition from the old core module to the new core_v2 module.
"""

import unittest
from unittest.mock import MagicMock, patch

from core_v2.domain.models import Category
from core_v2.compat import (
    DomainCategory,
    map_category_to_legacy,
    classify_domain,
    should_block_tab,
    get_blocking_reason,
    reload_configuration,
    DomainClassifierCompat,
    BlockingManagerCompat
)


class TestCompatibilityLayer(unittest.TestCase):
    """Tests for the compatibility layer."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create patch objects
        self.api_patcher = patch('core_v2.compat.api')
        
        # Start the patches
        self.mock_api = self.api_patcher.start()
        
        # Configure the mock API
        self.mock_api.classify_domain = MagicMock()
        self.mock_api.should_block_tab = MagicMock()
        self.mock_api.get_blocking_reason = MagicMock()
        self.mock_api.reload_configuration = MagicMock()
        
        # Create compatibility instances
        self.domain_classifier_compat = DomainClassifierCompat()
        self.blocking_manager_compat = BlockingManagerCompat()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Stop the patchers
        self.api_patcher.stop()
    
    def test_map_category_to_legacy(self):
        """Test mapping a core_v2 Category to a legacy DomainCategory."""
        # Test mapping from core_v2 Category to legacy DomainCategory
        self.assertEqual(map_category_to_legacy(Category.PRODUCTIVITY), DomainCategory.WORK)
        self.assertEqual(map_category_to_legacy(Category.SOCIAL_MEDIA), DomainCategory.SOCIAL)
        self.assertEqual(map_category_to_legacy(Category.ENTERTAINMENT), DomainCategory.ENTERTAINMENT)
        self.assertEqual(map_category_to_legacy(Category.SHOPPING), DomainCategory.SHOPPING)
        self.assertEqual(map_category_to_legacy(Category.NEWS), DomainCategory.NEWS)
        self.assertEqual(map_category_to_legacy(Category.EDUCATION), DomainCategory.EDUCATION)
        self.assertEqual(map_category_to_legacy(Category.TECHNOLOGY), DomainCategory.TECHNOLOGY)
        self.assertEqual(map_category_to_legacy(Category.FINANCE), DomainCategory.FINANCE)
        self.assertEqual(map_category_to_legacy(Category.GAMING), DomainCategory.GAMING)
        self.assertEqual(map_category_to_legacy(Category.ADULT), DomainCategory.ADULT)
        self.assertEqual(map_category_to_legacy(Category.UNKNOWN), DomainCategory.OTHER)
        self.assertIsNone(map_category_to_legacy(None))
    
    def test_classify_domain(self):
        """Test the classify_domain compatibility function."""
        # Configure the mock API
        self.mock_api.classify_domain.return_value = Category.SOCIAL_MEDIA
        
        # Call the compatibility function
        result = classify_domain("facebook.com")
        
        # Verify that the API was called with the correct domain
        self.mock_api.classify_domain.assert_called_once_with("facebook.com")
        
        # Verify that the result was mapped correctly
        self.assertEqual(result, DomainCategory.SOCIAL)
    
    def test_classify_domain_none(self):
        """Test the classify_domain compatibility function when the API returns None."""
        # Configure the mock API
        self.mock_api.classify_domain.return_value = None
        
        # Call the compatibility function
        result = classify_domain("unknown.com")
        
        # Verify that the API was called with the correct domain
        self.mock_api.classify_domain.assert_called_once_with("unknown.com")
        
        # Verify that None was returned
        self.assertIsNone(result)
    
    def test_should_block_tab(self):
        """Test the should_block_tab compatibility function."""
        # Configure the mock API
        self.mock_api.should_block_tab.return_value = True
        
        # Call the compatibility function
        result = should_block_tab("https://facebook.com")
        
        # Verify that the API was called with the correct URL
        self.mock_api.should_block_tab.assert_called_once_with("https://facebook.com", None)
        
        # Verify that the result was returned correctly
        self.assertTrue(result)
    
    def test_should_block_tab_with_metadata(self):
        """Test the should_block_tab compatibility function with metadata."""
        # Configure the mock API
        self.mock_api.should_block_tab.return_value = True
        
        # Create metadata
        metadata = {"focus_mode": "work"}
        
        # Call the compatibility function
        result = should_block_tab("https://facebook.com", metadata)
        
        # Verify that the API was called with the correct URL and metadata
        self.mock_api.should_block_tab.assert_called_once_with("https://facebook.com", metadata)
        
        # Verify that the result was returned correctly
        self.assertTrue(result)
    
    def test_get_blocking_reason(self):
        """Test the get_blocking_reason compatibility function."""
        # Configure the mock API
        self.mock_api.get_blocking_reason.return_value = "Domain category is blocked"
        
        # Call the compatibility function
        result = get_blocking_reason("https://facebook.com")
        
        # Verify that the API was called with the correct URL
        self.mock_api.get_blocking_reason.assert_called_once_with("https://facebook.com")
        
        # Verify that the result was returned correctly
        self.assertEqual(result, "Domain category is blocked")
    
    def test_reload_configuration(self):
        """Test the reload_configuration compatibility function."""
        # Call the compatibility function
        reload_configuration()
        
        # Verify that the API was called
        self.mock_api.reload_configuration.assert_called_once()
    
    def test_domain_classifier_compat_classify_domain(self):
        """Test the DomainClassifierCompat.classify_domain method."""
        # Configure the mock API
        self.mock_api.classify_domain.return_value = Category.SOCIAL_MEDIA
        
        # Call the compatibility method
        result = self.domain_classifier_compat.classify_domain("facebook.com")
        
        # Verify that the API was called with the correct domain
        self.mock_api.classify_domain.assert_called_once_with("facebook.com")
        
        # Verify that the result was mapped correctly
        self.assertEqual(result, DomainCategory.SOCIAL)
    
    def test_domain_classifier_compat_reload_config(self):
        """Test the DomainClassifierCompat.reload_config method."""
        # Call the compatibility method
        self.domain_classifier_compat.reload_config()
        
        # Verify that the API was called
        self.mock_api.reload_configuration.assert_called_once()
    
    def test_blocking_manager_compat_should_block_tab(self):
        """Test the BlockingManagerCompat.should_block_tab method."""
        # Configure the mock API
        self.mock_api.should_block_tab.return_value = True
        
        # Call the compatibility method
        result = self.blocking_manager_compat.should_block_tab("https://facebook.com")
        
        # Verify that the API was called with the correct URL
        self.mock_api.should_block_tab.assert_called_once_with("https://facebook.com", None)
        
        # Verify that the result was returned correctly
        self.assertTrue(result)
    
    def test_blocking_manager_compat_get_blocking_reason(self):
        """Test the BlockingManagerCompat.get_blocking_reason method."""
        # Configure the mock API
        self.mock_api.get_blocking_reason.return_value = "Domain category is blocked"
        
        # Call the compatibility method
        result = self.blocking_manager_compat.get_blocking_reason("https://facebook.com")
        
        # Verify that the API was called with the correct URL
        self.mock_api.get_blocking_reason.assert_called_once_with("https://facebook.com")
        
        # Verify that the result was returned correctly
        self.assertEqual(result, "Domain category is blocked")
    
    def test_blocking_manager_compat_reload_config(self):
        """Test the BlockingManagerCompat.reload_config method."""
        # Call the compatibility method
        self.blocking_manager_compat.reload_config()
        
        # Verify that the API was called
        self.mock_api.reload_configuration.assert_called_once()


if __name__ == "__main__":
    unittest.main()
