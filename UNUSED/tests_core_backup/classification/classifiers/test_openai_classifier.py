"""
Tests for the OpenAI classifier adapter in core_v2.

This module contains integration tests for the OpenAIClassifierAdapter class.
"""

import unittest
from unittest.mock import MagicMock, patch

from core_v2.domain.models import Domain, Category
from core_v2.classification.classifiers.openai import OpenAIClassifierAdapter
from core.domain_classifier.classifiers.llm_classifier import OpenAIDomainClassifier


class TestOpenAIClassifierAdapter(unittest.TestCase):
    """Tests for the OpenAIClassifierAdapter class."""
    
    def setUp(self):
        """Set up test fixtures.
        
        Creates a patch for the legacy OpenAI classifier and configures
        a mock instance to be returned when it's instantiated. This allows
        us to test the adapter's behavior without relying on the actual
        legacy classifier implementation.
        """
        # Create a patch for the legacy OpenAI classifier
        self.legacy_classifier_patcher = patch('core_v2.classification.classifiers.openai.OpenAIDomainClassifier')
        self.mock_legacy_class = self.legacy_classifier_patcher.start()
        
        # Create a mock instance that will be returned when OpenAIDomainClassifier is instantiated
        self.mock_legacy_instance = MagicMock()
        self.mock_legacy_class.return_value = self.mock_legacy_instance
        
        # Create the adapter (which will use our mocked legacy classifier)
        self.adapter = OpenAIClassifierAdapter()
    
    def test_name_property(self):
        """Test the name property.
        
        Verifies that the adapter's name property returns the expected value.
        """
        self.assertEqual(self.adapter.name, "openai_classifier")
    
    def test_classify_returns_none(self):
        """Test that the basic classify method returns None.
        
        The OpenAI classifier requires context to classify content, so the basic
        classify method should always return None.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Classify the domain
        category = self.adapter.classify(domain)
        
        # Verify that None is returned
        self.assertIsNone(category)
        
        # Verify that the legacy classifier was not called
        self.mock_legacy_instance.classify.assert_not_called()
    
    def test_classify_with_context_no_url(self):
        """Test classification with context when no URL is provided.
        
        Verifies that the adapter returns None when no URL is provided in the context.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Create a context without a URL
        context = {"metadata": {"title": "Some Content"}}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that None is returned
        self.assertIsNone(category)
        
        # Verify that the legacy classifier was not called
        self.mock_legacy_instance.can_classify.assert_not_called()
        self.mock_legacy_instance.classify.assert_not_called()
    
    def test_classify_with_context_cannot_classify(self):
        """Test classification with context when the legacy classifier cannot classify.
        
        Verifies that the adapter returns None when the legacy classifier indicates
        it cannot classify the URL.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Create a context with a URL
        context = {"url": "https://example.com", "metadata": {}}
        
        # Configure the mock legacy classifier to indicate it cannot classify this URL
        self.mock_legacy_instance.can_classify.return_value = False
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that None is returned
        self.assertIsNone(category)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://example.com", "example.com", {}
        )
        
        # Verify that the legacy classifier's classify was not called
        self.mock_legacy_instance.classify.assert_not_called()
    
    def test_classify_with_context_useful_content(self):
        """Test classification with context for useful content.
        
        Verifies that the adapter correctly calls the legacy classifier and maps
        the returned classification 'useful' to Category.EDUCATION.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Create a context with metadata
        context = {
            "url": "https://example.com/article",
            "metadata": {
                "title": "Educational Article",
                "description": "This is an educational article about programming"
            }
        }
        
        # Configure the mock legacy classifier
        self.mock_legacy_instance.can_classify.return_value = True
        self.mock_legacy_instance.classify.return_value = {"classification": "useful", "confidence": 0.9, "reason": "Educational content"}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the category from the legacy classifier is mapped correctly
        self.assertEqual(category, Category.EDUCATION)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://example.com/article", "example.com", context.get("metadata", {})
        )
        
        # Verify that the legacy classifier's classify was called with the correct arguments
        self.mock_legacy_instance.classify.assert_called_once_with(
            "https://example.com/article", "example.com", context.get("metadata", {})
        )
    
    def test_classify_with_context_distraction_content(self):
        """Test classification with context for distraction content.
        
        Verifies that the adapter correctly calls the legacy classifier and maps
        the returned classification 'distraction' to Category.ENTERTAINMENT.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Create a context with metadata
        context = {
            "url": "https://example.com/entertainment",
            "metadata": {
                "title": "Fun Article",
                "description": "This is an entertaining article"
            }
        }
        
        # Configure the mock legacy classifier
        self.mock_legacy_instance.can_classify.return_value = True
        self.mock_legacy_instance.classify.return_value = {"classification": "distraction", "confidence": 0.9, "reason": "Entertainment content"}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the category from the legacy classifier is mapped correctly
        self.assertEqual(category, Category.ENTERTAINMENT)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://example.com/entertainment", "example.com", context.get("metadata", {})
        )
        
        # Verify that the legacy classifier's classify was called with the correct arguments
        self.mock_legacy_instance.classify.assert_called_once_with(
            "https://example.com/entertainment", "example.com", context.get("metadata", {})
        )
    
    def test_classify_with_context_neutral_content(self):
        """Test classification with context for neutral content.
        
        Verifies that the adapter correctly calls the legacy classifier and maps
        the returned classification 'neutral' to None.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Create a context with metadata
        context = {
            "url": "https://example.com/neutral",
            "metadata": {
                "title": "Neutral Article",
                "description": "This is a neutral article"
            }
        }
        
        # Configure the mock legacy classifier
        self.mock_legacy_instance.can_classify.return_value = True
        self.mock_legacy_instance.classify.return_value = {"classification": "neutral", "confidence": 0.6, "reason": "Neutral content"}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that None is returned for neutral content
        self.assertIsNone(category)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://example.com/neutral", "example.com", context.get("metadata", {})
        )
        
        # Verify that the legacy classifier's classify was called with the correct arguments
        self.mock_legacy_instance.classify.assert_called_once_with(
            "https://example.com/neutral", "example.com", context.get("metadata", {})
        )
    
    def test_classify_with_context_legacy_returns_none(self):
        """Test classification with context when legacy classifier returns None.
        
        Verifies that the adapter returns None when the legacy classifier returns None.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Create a context with metadata
        context = {
            "url": "https://example.com/article",
            "metadata": {
                "title": "Some Article",
                "description": "This is an article"
            }
        }
        
        # Configure the mock legacy classifier
        self.mock_legacy_instance.can_classify.return_value = True
        self.mock_legacy_instance.classify.return_value = None
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that None is returned
        self.assertIsNone(category)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://example.com/article", "example.com", context.get("metadata", {})
        )
        
        # Verify that the legacy classifier's classify was called with the correct arguments
        self.mock_legacy_instance.classify.assert_called_once_with(
            "https://example.com/article", "example.com", context.get("metadata", {})
        )
    
    def test_classify_with_context_unknown_classification(self):
        """Test classification with context when legacy classifier returns an unknown classification.
        
        Verifies that the adapter returns None when the legacy classifier returns
        a classification that is not 'useful', 'distraction', or 'neutral'.
        """
        # Create a domain
        domain = Domain("example.com")
        
        # Create a context with metadata
        context = {
            "url": "https://example.com/article",
            "metadata": {
                "title": "Some Article",
                "description": "This is an article"
            }
        }
        
        # Configure the mock legacy classifier
        self.mock_legacy_instance.can_classify.return_value = True
        self.mock_legacy_instance.classify.return_value = {"classification": "unknown", "confidence": 0.5, "reason": "Unknown content"}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that None is returned for unknown classification
        self.assertIsNone(category)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://example.com/article", "example.com", context.get("metadata", {})
        )
        
        # Verify that the legacy classifier's classify was called with the correct arguments
        self.mock_legacy_instance.classify.assert_called_once_with(
            "https://example.com/article", "example.com", context.get("metadata", {})
        )
    
    def test_set_api_key(self):
        """Test setting the API key.
        
        Verifies that the adapter's set_api_key method correctly sets the API key
        on the legacy classifier.
        """
        # Set the API key
        api_key = "sk-test-api-key"
        self.adapter.set_api_key(api_key)
        
        # Verify that the legacy classifier's api_key was set
        self.assertEqual(self.mock_legacy_instance.api_key, api_key)
    
    def test_set_model(self):
        """Test setting the model.
        
        Verifies that the adapter's set_model method correctly sets the model
        on the legacy classifier.
        """
        # Set the model
        model_name = "gpt-4o-mini"
        self.adapter.set_model(model_name)
        
        # Verify that the legacy classifier's model_name was set
        self.assertEqual(self.mock_legacy_instance.model_name, model_name)
    
    def tearDown(self):
        """Clean up after tests.
        
        Stops the patch for the legacy OpenAI classifier to avoid affecting other tests.
        This ensures that the original OpenAIBaseClassifier class is restored
        after each test.
        """
        self.legacy_classifier_patcher.stop()


if __name__ == "__main__":
    unittest.main()
