"""
Basic integration tests for the classification module.

This module contains basic integration tests for the classification system,
focusing on core functionality including:
- Classifier registry operations
- Classification pipeline operations
- YouTube rule-based classifier tests
- Basic configuration changes

These tests use synchronous testing patterns and complement the advanced
async integration tests in test_advanced_integration.py.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.classification import (
    ClassifierRegistry,
    ClassificationPipeline
)
from focus_guard.core.classification.classifiers.domains.youtube_rules import (
    RuleBasedYouTubeClassifier
)

# Skip if optional dependencies are not available
try:
    from focus_guard.core.classification.classifiers.domains.youtube_llm import (
        LLMBasedYouTubeClassifier
    )
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class TestClassificationIntegration:
    """Integration tests for the classification system."""
    
    @pytest.fixture
    def registry(self):
        """Create a classifier registry with test classifiers."""
        registry = ClassifierRegistry()
        
        # Add a mock rule-based classifier
        rule_classifier = RuleBasedYouTubeClassifier()
        registry.register(rule_classifier)
        
        # Add LLM-based classifier if available
        if HAS_LLM:
            # Create a mock LLM client
            mock_llm_client = MagicMock()
            mock_llm_client.generate.return_value = "{\"category\": \"ENTERTAINMENT\", \"confidence\": 0.9, \"reason\": \"Entertainment content\", \"is_distracting\": true, \"content_type\": \"video\"}"
            llm_classifier = LLMBasedYouTubeClassifier(llm_client=mock_llm_client)
            registry.register(llm_classifier)
        
        return registry
    
    @pytest.fixture
    def pipeline(self, registry):
        """Create a classification pipeline with test classifiers."""
        pipeline = ClassificationPipeline(registry)
        pipeline.add_classifier("youtube_rule_based")
        
        if HAS_LLM:
            pipeline.add_classifier("youtube_llm")
            
        return pipeline
    
    @pytest.mark.parametrize("url,expected_category", [
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", Category.ENTERTAINMENT),
        ("https://youtube.com/watch?v=abc123", Category.ENTERTAINMENT),
    ])
    def test_youtube_classification(self, pipeline, url, expected_category):
        """Test that YouTube URLs are classified correctly."""
        domain = Domain("youtube.com")
        context = {"url": url, "title": "Funny video compilation"}  # Add title for proper classification
        
        result = pipeline.classify(domain, context)
        assert result is not None
        assert result.category == expected_category
    
    def test_basic_classification_priority(self, registry):
        """Test that classifiers are called in priority order."""
        # Create mock classifiers with different priorities
        high_priority = MagicMock()
        high_priority.name = "high_priority"
        high_priority.classify.return_value = Category.EDUCATION
        
        low_priority = MagicMock()
        low_priority.name = "low_priority"
        low_priority.classify.return_value = Category.ENTERTAINMENT
        
        # Register classifiers
        registry.register(high_priority)
        registry.register(low_priority)
        
        # Create pipeline with specific order
        pipeline = ClassificationPipeline(registry)
        pipeline.add_classifier("high_priority")
        pipeline.add_classifier("low_priority")
        
        # Classify a domain
        domain = Domain("test.com")
        result = pipeline.classify(domain)
        
        # Should return the result from the first classifier that returns a value
        assert result is not None
        assert result.category == Category.EDUCATION
        
        # Only the first classifier should have been called
        high_priority.classify.assert_called_once()
        low_priority.classify.assert_not_called()
    
    @pytest.mark.skipif(not HAS_LLM, reason="LLM dependencies not available")
    def test_youtube_classifier_fallback(self, registry):
        """Test that the YouTube classifier falls back to LLM when rules don't match."""

        # Create a new registry for this test
        test_registry = ClassifierRegistry()

        # Create a real rule-based classifier
        rule_classifier = RuleBasedYouTubeClassifier()
        test_registry.register(rule_classifier)

        # Create a mock LLM client
        mock_llm_client = MagicMock()

        # Create the classifier with mock LLM client
        llm_classifier = LLMBasedYouTubeClassifier(llm_client=mock_llm_client)
        test_registry.register(llm_classifier)

        # Create pipeline with both classifiers
        pipeline = ClassificationPipeline(test_registry)
        pipeline.add_classifier("youtube_rule_based")
        pipeline.add_classifier("youtube_llm")

        # Test with a URL that might not match any rules
        domain = Domain("youtube.com")
        context = {
            "url": "https://youtube.com/watch?v=xyz789",
            "title": "Advanced Machine Learning Tutorial"
        }

        # Create a proper Classification result with EDUCATION category
        expected_classification = Classification(
            domain=Domain("youtube.com"),
            category=Category.EDUCATION,
            confidence=0.85,
            metadata={"reason": "Educational content"}
        )

        # Mock the rule-based classifier to return None
        with patch.object(rule_classifier, 'classify', return_value=None):
            # Mock the LLM classifier's classify method to return the expected classification
            # Since the LLM classifier returns a Classification object, we need to mock appropriately
            with patch.object(llm_classifier, 'classify', return_value=Category.EDUCATION):
                result = pipeline.classify(domain, context)

                # Verify the result
                assert result is not None
                assert result.category == Category.EDUCATION
                assert result.domain == Domain("youtube.com")
                assert result.confidence == 1.0  # Default confidence from pipeline
    
    def test_configuration_changes(self, registry):
        """Test that configuration changes affect classification."""
        # Create a mock classifier that uses configuration
        mock_classifier = MagicMock()
        mock_classifier.name = "configurable"
        mock_classifier.classify.return_value = Category.PRODUCTIVITY
        
        # Register the classifier
        registry.register(mock_classifier)
        
        # Create pipeline
        pipeline = ClassificationPipeline(registry)
        pipeline.add_classifier("configurable")
        
        # First classification with default config
        domain = Domain("example.com")
        result1 = pipeline.classify(domain)
        
        # Change the classifier's behavior
        mock_classifier.classify.return_value = Category.ENTERTAINMENT
        
        # Second classification should reflect the change
        result2 = pipeline.classify(domain)
        
        assert result1 is not None
        assert result2 is not None
        assert result1.category == Category.PRODUCTIVITY
        assert result2.category == Category.ENTERTAINMENT
