"""
Tests for the base classification interfaces and classes.
"""
import pytest
from unittest.mock import MagicMock

from focus_guard.core.classification.base import (
    Classifier,
    ClassifierRegistry,
    ClassificationPipeline,
    ContextAwareClassifier
)
from focus_guard.core.domain.models import Domain, Category, Classification


class TestClassifierProtocol:
    """Tests for the Classifier protocol."""
    
    def test_classifier_protocol_requires_name_property(self):
        """Test that Classifier protocol requires a name property."""
        class ValidClassifier:
            @property
            def name(self):
                return "test"
                
            def classify(self, domain):
                pass
                
        # Should not raise
        assert isinstance(ValidClassifier(), Classifier)
        
        class MissingName:
            def classify(self, domain):
                pass
                
        assert not isinstance(MissingName(), Classifier)
    
    def test_classifier_protocol_requires_classify_method(self):
        """Test that Classifier protocol requires a classify method."""
        class MissingClassify:
            @property
            def name(self):
                return "test"
                
        assert not isinstance(MissingClassify(), Classifier)


class TestClassifierRegistry:
    """Tests for the ClassifierRegistry class."""
    
    def test_register_classifier(self, mock_classifier):
        """Test registering a classifier."""
        registry = ClassifierRegistry()
        registry.register(mock_classifier)
        assert registry.get("mock_classifier") is mock_classifier
    
    def test_register_duplicate_classifier(self, mock_classifier):
        """Test registering a duplicate classifier raises an error."""
        registry = ClassifierRegistry()
        registry.register(mock_classifier)
        
        with pytest.raises(ValueError):
            registry.register(mock_classifier)
    
    def test_unregister_classifier(self, mock_classifier):
        """Test unregistering a classifier."""
        registry = ClassifierRegistry()
        registry.register(mock_classifier)
        registry.unregister("mock_classifier")
        assert registry.get("mock_classifier") is None
    
    def test_get_nonexistent_classifier(self):
        """Test getting a non-existent classifier returns None."""
        registry = ClassifierRegistry()
        assert registry.get("nonexistent") is None
    
    def test_clear_classifiers(self, mock_classifier):
        """Test clearing all classifiers from the registry."""
        registry = ClassifierRegistry()
        registry.register(mock_classifier)
        registry.clear()
        assert registry.get("mock_classifier") is None


class TestClassificationPipeline:
    """Tests for the ClassificationPipeline class."""
    
    def test_add_classifier(self, classifier_registry, mock_classifier):
        """Test adding a classifier to the pipeline."""
        pipeline = ClassificationPipeline(classifier_registry)
        pipeline.add_classifier("mock_classifier")
        assert "mock_classifier" in pipeline._pipeline
    
    def test_add_nonexistent_classifier(self, classifier_registry):
        """Test adding a non-existent classifier raises an error."""
        pipeline = ClassificationPipeline(classifier_registry)
        with pytest.raises(ValueError):
            pipeline.add_classifier("nonexistent")
    
    def test_remove_classifier(self, classifier_registry, mock_classifier):
        """Test removing a classifier from the pipeline."""
        pipeline = ClassificationPipeline(classifier_registry)
        pipeline.add_classifier("mock_classifier")
        pipeline.remove_classifier("mock_classifier")
        assert "mock_classifier" not in pipeline._pipeline
    
    def test_classify_without_context(self, classification_pipeline, mock_domain, mock_classifier):
        """Test classification without providing context."""
        result = classification_pipeline.classify(mock_domain)
        assert result is not None
        assert result.category == Category.ENTERTAINMENT
        mock_classifier.classify.assert_called_once_with(mock_domain)
    
    def test_classify_with_context(self, classification_pipeline, mock_domain, mock_context_aware_classifier):
        """Test classification with context provided."""
        context = {"url": "https://example.com/page", "title": "Test Page"}
        
        # Configure the mock to return a specific classification
        expected_classification = Classification(
            domain=mock_domain,
            category=Category.ENTERTAINMENT,
            confidence=0.95,
            metadata={"classifier": "mock_context_aware"}
        )
        mock_context_aware_classifier.classify_with_context.return_value = expected_classification
        
        # Override the name for this test
        mock_context_aware_classifier.name = "test_context_classifier"
        
        # Register the mock classifier in the registry
        classification_pipeline._registry.register(mock_context_aware_classifier)
        
        # Add the mock classifier to the pipeline
        classification_pipeline.add_classifier("test_context_classifier")
        
        # Ensure the regular classifier returns None so context-aware is used
        regular_classifier = classification_pipeline._registry.get("mock_classifier")
        if regular_classifier:
            regular_classifier.classify.return_value = None
        
        result = classification_pipeline.classify(mock_domain, context)
        
        assert result is not None
        assert result.category == Category.ENTERTAINMENT
        mock_context_aware_classifier.classify_with_context.assert_called_once_with(mock_domain, context)
    
    def test_classification_order(self, classifier_registry, mock_domain):
        """Test that classifiers are called in the order they were added."""
        # Create two mock classifiers
        first = MagicMock(spec=Classifier)
        first.name = "first"
        first.classify.return_value = None  # First classifier returns None
        
        second = MagicMock(spec=Classifier)
        second.name = "second"
        second.classify.return_value = Category.PRODUCTIVITY  # Second classifier returns a category
        
        # Register both classifiers
        classifier_registry.register(first)
        classifier_registry.register(second)
        
        # Create pipeline and add classifiers in specific order
        pipeline = ClassificationPipeline(classifier_registry)
        pipeline.add_classifier("first")
        pipeline.add_classifier("second")
        
        # Classify and verify order
        result = pipeline.classify(mock_domain)
        
        # Both classifiers should have been called
        first.classify.assert_called_once()
        second.classify.assert_called_once()
        
        # The result should come from the second classifier
        assert result is not None
        assert result.category == Category.PRODUCTIVITY
