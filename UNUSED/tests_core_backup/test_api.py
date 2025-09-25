"""
Tests for the main API class in core_v2.

This module contains unit tests for the ClassifierBlockerAPI class.
"""

import unittest
from unittest.mock import MagicMock, patch

from core_v2.api import ClassifierBlockerAPI
from core_v2.domain.models import Domain, Category
from core_v2.blocking.base import BlockingDecision


class TestClassifierBlockerAPI(unittest.TestCase):
    """Tests for the ClassifierBlockerAPI class."""
    
    @patch('core_v2.api.ConfigurationLoader')
    @patch('core_v2.api.ClassifierRegistry')
    @patch('core_v2.api.BlockingStrategyRegistry')
    @patch('core_v2.api.BlockingPipeline')
    @patch('core_v2.api.StandardDomainClassifier')
    @patch('core_v2.api.YouTubeClassifierAdapter')
    @patch('core_v2.api.DomainExcluderStrategy')
    @patch('core_v2.api.CategoryBlockerStrategy')
    def setUp(self, mock_category_blocker, mock_domain_excluder, mock_youtube_classifier, 
              mock_standard_classifier, mock_pipeline, mock_blocking_registry, 
              mock_classifier_registry, mock_config_loader):
        """Set up test fixtures."""
        # Set up mocks
        self.mock_config_loader = mock_config_loader.return_value
        self.mock_classifier_registry = mock_classifier_registry.return_value
        self.mock_blocking_registry = mock_blocking_registry.return_value
        self.mock_pipeline = mock_pipeline.return_value
        
        # Set up classifier mocks
        self.mock_standard_classifier = mock_standard_classifier.return_value
        self.mock_youtube_classifier = mock_youtube_classifier.return_value
        
        # Set up blocking strategy mocks
        self.mock_domain_excluder = mock_domain_excluder.return_value
        self.mock_category_blocker = mock_category_blocker.return_value
        
        # Create the API instance
        self.api = ClassifierBlockerAPI()
        
        # Replace the API's pipeline with our mock
        self.api._blocking_pipeline = self.mock_pipeline
    
    def test_classify_domain(self):
        """Test domain classification."""
        # Set up the mock classifier registry to return a list with our mock classifier
        self.mock_classifier_registry.get_all.return_value = [self.mock_standard_classifier]
        
        # Configure the mock classifier to return a category
        self.mock_standard_classifier.classify.return_value = Category.PRODUCTIVITY
        self.mock_standard_classifier.name = "standard_domain_classifier"
        
        # Call the method
        result = self.api.classify_domain("github.com")
        
        # Verify the result
        self.assertEqual(result, Category.PRODUCTIVITY)
        
        # Verify that the classifier was called with the correct domain
        self.mock_standard_classifier.classify.assert_called_once()
        domain_arg = self.mock_standard_classifier.classify.call_args[0][0]
        self.assertIsInstance(domain_arg, Domain)
        self.assertEqual(domain_arg.value, "github.com")
    
    def test_classify_domain_no_match(self):
        """Test domain classification with no matching category."""
        # Set up the mock classifier registry to return a list with our mock classifier
        self.mock_classifier_registry.get_all.return_value = [self.mock_standard_classifier]
        
        # Configure the mock classifier to return None
        self.mock_standard_classifier.classify.return_value = None
        
        # Call the method
        result = self.api.classify_domain("example.com")
        
        # Verify the result
        self.assertIsNone(result)
    
    def test_should_block_tab(self):
        """Test tab blocking."""
        # Configure the mock pipeline to return a blocking decision
        self.mock_pipeline.should_block_with_context.return_value = BlockingDecision(
            should_block=True,
            reason="Test blocking reason"
        )
        
        # Call the method
        result = self.api.should_block_tab("https://facebook.com")
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify that the pipeline was called with the correct domain and context
        self.mock_pipeline.should_block_with_context.assert_called_once()
        domain_arg = self.mock_pipeline.should_block_with_context.call_args[0][0]
        self.assertIsInstance(domain_arg, Domain)
        self.assertEqual(domain_arg.value, "facebook.com")
    
    def test_should_block_tab_no_block(self):
        """Test tab blocking with no block decision."""
        # Configure the mock pipeline to return a non-blocking decision
        self.mock_pipeline.should_block_with_context.return_value = BlockingDecision(
            should_block=False,
            reason=None
        )
        
        # Call the method
        result = self.api.should_block_tab("https://github.com")
        
        # Verify the result
        self.assertFalse(result)
    
    def test_get_blocking_reason(self):
        """Test getting the blocking reason."""
        # Configure the mock pipeline to return a blocking decision
        self.mock_pipeline.should_block.return_value = BlockingDecision(
            should_block=True,
            reason="Test blocking reason"
        )
        
        # Call the method
        result = self.api.get_blocking_reason("https://facebook.com")
        
        # Verify the result
        self.assertEqual(result, "Test blocking reason")
    
    def test_get_blocking_reason_no_block(self):
        """Test getting the blocking reason when not blocked."""
        # Configure the mock pipeline to return a non-blocking decision
        self.mock_pipeline.should_block.return_value = BlockingDecision(
            should_block=False,
            reason=None
        )
        
        # Call the method
        result = self.api.get_blocking_reason("https://github.com")
        
        # Verify the result
        self.assertIsNone(result)
    
    def test_reload_configuration(self):
        """Test reloading the configuration."""
        # Call the method
        self.api.reload_configuration()
        
        # Verify that the config loader was reloaded
        self.mock_config_loader.reload.assert_called_once()
        
        # Verify that the blocking pipeline reloaded all strategies
        self.mock_pipeline.reload_all_strategies.assert_called_once()


if __name__ == "__main__":
    unittest.main()
