"""
Tests for the YouTube classifier adapter in core_v2.

This module contains unit tests for the YouTubeClassifierAdapter class.
"""

import unittest
from unittest.mock import MagicMock, patch

from core_v2.domain.models import Domain, Category
from core_v2.classification.classifiers.youtube import YouTubeClassifierAdapter


class TestYouTubeClassifierAdapter(unittest.TestCase):
    """Tests for the YouTubeClassifierAdapter class."""
    
    def setUp(self):
        """Set up test fixtures.
        
        Creates a patch for the legacy YouTube classifier and configures
        a mock instance to be returned when it's instantiated. This allows
        us to test the adapter's behavior without relying on the actual
        legacy classifier implementation.
        """
        # Create a patch for the legacy YouTube classifier
        self.legacy_classifier_patcher = patch('core_v2.classification.classifiers.youtube.LegacyYouTubeClassifier')
        self.mock_legacy_class = self.legacy_classifier_patcher.start()
        
        # Create a mock instance that will be returned when LegacyYouTubeClassifier is instantiated
        self.mock_legacy_instance = MagicMock()
        self.mock_legacy_class.return_value = self.mock_legacy_instance
        
        # Create the adapter (which will use our mocked legacy classifier)
        self.adapter = YouTubeClassifierAdapter()
    
    def test_name_property(self):
        """Test the name property.
        
        Verifies that the adapter's name property returns the expected value.
        """
        self.assertEqual(self.adapter.name, "youtube_classifier")
    
    def test_classify_non_youtube_domain(self):
        """Test classification of a non-YouTube domain.
        
        Verifies that the adapter returns None when classifying a non-YouTube domain
        and does not call the legacy classifier.
        """
        # Create a non-YouTube domain
        domain = Domain("example.com")
        
        # Classify the domain
        category = self.adapter.classify(domain)
        
        # Verify that None is returned
        self.assertIsNone(category)
        
        # Verify that the legacy classifier was not called
        self.mock_legacy_instance.classify.assert_not_called()
    
    def test_classify_youtube_domain_without_context(self):
        """Test classification of a YouTube domain without context.
        
        Verifies that the adapter returns the default category (ENTERTAINMENT)
        when classifying a YouTube domain without context and does not call
        the legacy classifier.
        """
        # Create a YouTube domain
        domain = Domain("youtube.com")
        
        # Classify the domain
        category = self.adapter.classify(domain)
        
        # Verify that the default category is returned
        self.assertEqual(category, Category.ENTERTAINMENT)
        
        # Verify that the legacy classifier was not called
        self.mock_legacy_instance.classify.assert_not_called()
    
    def test_classify_with_context_non_youtube_domain(self):
        """Test classification with context for a non-YouTube domain.
        
        Verifies that the adapter returns None when classifying a non-YouTube domain
        with context and does not call the legacy classifier.
        """
        # Create a non-YouTube domain
        domain = Domain("example.com")
        
        # Create a context
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
    
    def test_classify_with_context_youtube_domain_no_metadata(self):
        """Test classification with context for a YouTube domain without metadata.
        
        Verifies that the adapter returns None when classifying a YouTube domain
        with context but without metadata, when the legacy classifier indicates
        it cannot classify the URL.
        """
        # Create a YouTube domain
        domain = Domain("youtube.com")
        
        # Create a context without metadata
        context = {"url": "https://youtube.com"}
        
        # Configure the mock legacy classifier to indicate it cannot classify this URL
        self.mock_legacy_instance.can_classify.return_value = False
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that None is returned when can_classify returns False
        self.assertIsNone(category)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://youtube.com", "youtube.com", {}
        )
        
        # Verify that the legacy classifier's classify was not called
        self.mock_legacy_instance.classify.assert_not_called()
    
    def test_classify_with_context_youtube_domain_with_metadata_education(self):
        """Test classification with context for a YouTube domain with metadata (education).
        
        Verifies that the adapter correctly calls the legacy classifier when
        classifying a YouTube domain with context and metadata, and maps the
        returned classification 'useful' to Category.EDUCATION.
        """
        # Create a YouTube domain
        domain = Domain("youtube.com")
        
        # Create a context with metadata
        context = {
            "url": "https://www.youtube.com/watch?v=12345",
            "metadata": {
                "title": "Educational Video",
                "description": "This is an educational video about programming",
                "type": "youtube",
                "video_id": "12345"
            }
        }
        
        # Configure the mock legacy classifier
        self.mock_legacy_instance.can_classify.return_value = True
        self.mock_legacy_instance.classify.return_value = {"classification": "useful"}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the category from the legacy classifier is mapped correctly
        self.assertEqual(category, Category.EDUCATION)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://www.youtube.com/watch?v=12345", "youtube.com", context.get("metadata", {})
        )
        
        # Verify that the legacy classifier's classify was called with the correct arguments
        self.mock_legacy_instance.classify.assert_called_once_with(
            "https://www.youtube.com/watch?v=12345", "youtube.com", context.get("metadata", {})
        )
    
    def test_classify_with_context_youtube_domain_with_metadata_entertainment(self):
        """Test classification with context for a YouTube domain with metadata (entertainment).
        
        Verifies that the adapter correctly calls the legacy classifier when
        classifying a YouTube domain with context and metadata, and maps the
        returned classification 'distraction' to Category.ENTERTAINMENT.
        """
        # Create a YouTube domain
        domain = Domain("youtube.com")
        
        # Create a context with metadata
        context = {
            "url": "https://www.youtube.com/watch?v=12345",
            "metadata": {
                "title": "Funny Cat Video",
                "description": "This is a funny cat video",
                "type": "youtube",
                "video_id": "12345"
            }
        }
        
        # Configure the mock legacy classifier
        self.mock_legacy_instance.can_classify.return_value = True
        self.mock_legacy_instance.classify.return_value = {"classification": "distraction"}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the category from the legacy classifier is mapped correctly
        self.assertEqual(category, Category.ENTERTAINMENT)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://www.youtube.com/watch?v=12345", "youtube.com", context.get("metadata", {})
        )
        
        # Verify that the legacy classifier's classify was called with the correct arguments
        self.mock_legacy_instance.classify.assert_called_once_with(
            "https://www.youtube.com/watch?v=12345", "youtube.com", context.get("metadata", {})
        )
    
    def test_classify_with_context_youtube_domain_legacy_returns_none(self):
        """Test classification with context when legacy classifier returns None.
        
        Verifies that the adapter returns the default category (ENTERTAINMENT)
        when the legacy classifier returns None for a YouTube domain with context
        and metadata.
        """
        # Create a YouTube domain
        domain = Domain("youtube.com")
        
        # Create a context with metadata
        context = {
            "url": "https://www.youtube.com/watch?v=12345",
            "metadata": {
                "title": "Some Video",
                "description": "This is a video",
                "type": "youtube",
                "video_id": "12345"
            }
        }
        
        # Configure the mock legacy classifier
        self.mock_legacy_instance.can_classify.return_value = True
        self.mock_legacy_instance.classify.return_value = None
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the default category is returned
        self.assertEqual(category, Category.ENTERTAINMENT)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://www.youtube.com/watch?v=12345", "youtube.com", context.get("metadata", {})
        )
        
        # Verify that the legacy classifier's classify was called with the correct arguments
        self.mock_legacy_instance.classify.assert_called_once_with(
            "https://www.youtube.com/watch?v=12345", "youtube.com", context.get("metadata", {})
        )
    
    def test_classify_with_context_youtube_domain_unknown_classification(self):
        """Test classification with context when legacy classifier returns an unknown classification.
        
        Verifies that the adapter returns the default category (ENTERTAINMENT)
        when the legacy classifier returns a classification that is not 'useful' or 'distraction'.
        """
        # Create a YouTube domain
        domain = Domain("youtube.com")
        
        # Create a context with metadata
        context = {
            "url": "https://www.youtube.com/watch?v=12345",
            "metadata": {
                "title": "Some Video",
                "description": "This is a video",
                "type": "youtube",
                "video_id": "12345"
            }
        }
        
        # Configure the mock legacy classifier
        self.mock_legacy_instance.can_classify.return_value = True
        self.mock_legacy_instance.classify.return_value = {"classification": "unknown"}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the default category is returned
        self.assertEqual(category, Category.ENTERTAINMENT)
        
        # Verify that the legacy classifier's can_classify was called
        self.mock_legacy_instance.can_classify.assert_called_once_with(
            "https://www.youtube.com/watch?v=12345", "youtube.com", context.get("metadata", {})
        )
        
        # Verify that the legacy classifier's classify was called with the correct arguments
        self.mock_legacy_instance.classify.assert_called_once_with(
            "https://www.youtube.com/watch?v=12345", "youtube.com", context.get("metadata", {})
        )
    
    def test_set_classification_method(self):
        """Test setting the classification method.
        
        Verifies that the adapter's set_classification_method method correctly
        sets the classification_method attribute on the legacy classifier.
        """
        # Set the classification method
        self.adapter.set_classification_method("llm")
        
        # Verify that the legacy classifier's classification_method was set
        self.assertEqual(self.mock_legacy_instance.classification_method, "llm")
        
    def test_classify_with_context_no_url(self):
        """Test classification with context when no URL is provided.
        
        Verifies that the adapter falls back to the basic classify method
        when no URL is provided in the context.
        """
        # Create a YouTube domain
        domain = Domain("youtube.com")
        
        # Create a context without a URL
        context = {"metadata": {"title": "Some Video"}}
        
        # Classify the domain with context
        category = self.adapter.classify_with_context(domain, context)
        
        # Verify that the default category is returned (from classify method)
        self.assertEqual(category, Category.ENTERTAINMENT)
        
        # Verify that the legacy classifier was not called
        self.mock_legacy_instance.can_classify.assert_not_called()
        self.mock_legacy_instance.classify.assert_not_called()
    
    def tearDown(self):
        """Clean up after tests.
        
        Stops the patch for the legacy YouTube classifier to avoid affecting other tests.
        This ensures that the original LegacyYouTubeClassifier class is restored
        after each test.
        """
        self.legacy_classifier_patcher.stop()


if __name__ == "__main__":
    unittest.main()
