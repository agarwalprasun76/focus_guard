"""
Unit tests for the classification base classes.

This module tests the core interfaces and classes for domain classification,
including abstract base classes, registry functionality, and the classification pipeline.
The tests ensure that the classification system works correctly for both regular
and context-aware classifiers, and that the pipeline properly handles various scenarios
like missing classifiers and context-aware classification.
"""

import unittest
from unittest.mock import Mock, patch

from focus_guard.core.classification.base import (
    Classifier,
    ContextAwareClassifier,
    ClassifierRegistry,
    ClassificationPipeline,
)
from focus_guard.core.domain.models import Domain, Category


class MockClassifier(Classifier):
    """Mock implementation of Classifier for testing.
    
    This is a concrete implementation of the Classifier abstract base class
    used for testing purposes. It returns a predefined category when classifying domains.
    """

    def __init__(self, name, category=None):
        self._name = name
        self._category = category

    def classify(self, domain):
        return self._category

    @property
    def name(self):
        return self._name


class MockContextAwareClassifier(ContextAwareClassifier):
    """Mock implementation of ContextAwareClassifier for testing.
    
    This is a concrete implementation of the ContextAwareClassifier abstract base class
    used for testing purposes. It returns different predefined categories based on
    whether context is provided or not.
    """

    def __init__(self, name, category=None, context_category=None):
        self._name = name
        self._category = category
        self._context_category = context_category

    def classify(self, domain):
        return self._category

    def classify_with_context(self, domain, context):
        return self._context_category

    @property
    def name(self):
        return self._name


class TestClassifier(unittest.TestCase):
    """Tests for the Classifier abstract base class.
    
    These tests verify that the Classifier interface can be properly implemented
    and used, ensuring that concrete implementations can be created and function
    as expected.
    """

    def test_classifier_interface(self):
        """Test that a concrete classifier can be instantiated and used.
        
        This test verifies that a concrete implementation of the Classifier
        interface can be created and used to classify domains.
        """
        domain = Domain("example.com")
        category = Category.SOCIAL_MEDIA
        classifier = MockClassifier("test_classifier", category)

        self.assertEqual(classifier.name, "test_classifier")
        self.assertEqual(classifier.classify(domain), category)


class TestContextAwareClassifier(unittest.TestCase):
    """Tests for the ContextAwareClassifier abstract base class.
    
    These tests verify that the ContextAwareClassifier interface can be properly
    implemented and used, ensuring that concrete implementations can handle both
    regular classification and context-aware classification.
    """

    def test_context_aware_classifier_interface(self):
        """Test that a concrete context-aware classifier can be instantiated and used.
        
        This test verifies that a concrete implementation of the ContextAwareClassifier
        interface can be created and used to classify domains with and without context.
        """
        domain = Domain("example.com")
        category = Category.SOCIAL_MEDIA
        context_category = Category.ENTERTAINMENT
        context = {"path": "/videos"}
        
        classifier = MockContextAwareClassifier(
            "test_context_classifier", category, context_category
        )

        self.assertEqual(classifier.name, "test_context_classifier")
        self.assertEqual(classifier.classify(domain), category)
        self.assertEqual(classifier.classify_with_context(domain, context), context_category)
        
    def test_abstract_methods(self):
        """Test that abstract methods in base classes raise NotImplementedError.
        
        This test verifies that attempting to use the abstract methods directly
        without proper implementation raises the appropriate exception.
        """
        # Create a test class that inherits from Classifier but doesn't implement abstract methods
        class IncompleteClassifier(Classifier):
            pass
            
        # Create a test class that inherits from ContextAwareClassifier but doesn't implement abstract methods
        class IncompleteContextAwareClassifier(ContextAwareClassifier):
            pass
        
        # Verify that instantiating these classes raises TypeError
        with self.assertRaises(TypeError):
            IncompleteClassifier()
            
        with self.assertRaises(TypeError):
            IncompleteContextAwareClassifier()
            
    def test_partial_classifier_implementation(self):
        """Test partial implementation of Classifier abstract methods.
        
        This test verifies that even with partial implementation of abstract methods,
        the remaining abstract methods still need to be implemented.
        """
        # Create a test class that implements only the name property
        class NameOnlyClassifier(Classifier):
            @property
            def name(self):
                return "name_only"
                
        # Create a test class that implements only the classify method
        class ClassifyOnlyClassifier(Classifier):
            def classify(self, domain):
                return Category.SOCIAL_MEDIA
        
        # Verify that instantiating these classes raises TypeError
        with self.assertRaises(TypeError):
            NameOnlyClassifier()
            
        with self.assertRaises(TypeError):
            ClassifyOnlyClassifier()
            
    def test_partial_context_aware_classifier_implementation(self):
        """Test partial implementation of ContextAwareClassifier abstract methods.
        
        This test verifies that even with partial implementation of abstract methods,
        the remaining abstract methods still need to be implemented.
        """
        # Create a test class that implements only some methods
        class PartialContextAwareClassifier(ContextAwareClassifier):
            @property
            def name(self):
                return "partial_context"
                
            def classify(self, domain):
                return Category.SOCIAL_MEDIA
        
        # Verify that instantiating this class raises TypeError
        # because classify_with_context is not implemented
        with self.assertRaises(TypeError):
            PartialContextAwareClassifier()


class TestClassifierRegistry(unittest.TestCase):
    """Tests for the ClassifierRegistry class.
    
    These tests verify that the ClassifierRegistry correctly manages classifiers,
    including registration, unregistration, and retrieval operations. The registry
    is a central component that stores all available classifiers for use in
    classification pipelines.
    """

    def setUp(self):
        """Set up test fixtures.
        
        Creates a registry and test classifiers with predefined categories.
        """
        self.registry = ClassifierRegistry()
        self.classifier1 = MockClassifier("classifier1", Category.SOCIAL_MEDIA)
        self.classifier2 = MockClassifier("classifier2", Category.PRODUCTIVITY)

    def test_register(self):
        """Test registering classifiers."""
        self.registry.register(self.classifier1)
        self.assertEqual(self.registry.get("classifier1"), self.classifier1)

        self.registry.register(self.classifier2)
        self.assertEqual(self.registry.get("classifier2"), self.classifier2)

    def test_unregister(self):
        """Test unregistering classifiers."""
        self.registry.register(self.classifier1)
        self.registry.register(self.classifier2)

        self.registry.unregister("classifier1")
        self.assertIsNone(self.registry.get("classifier1"))
        self.assertEqual(self.registry.get("classifier2"), self.classifier2)
        
    def test_unregister_nonexistent(self):
        """Test unregistering a non-existent classifier.
        
        This test verifies that unregistering a classifier that doesn't exist
        doesn't raise an exception and has no effect on the registry.
        """
        # Register a classifier
        self.registry.register(self.classifier1)
        
        # Unregister a non-existent classifier
        self.registry.unregister("nonexistent")
        
        # Verify the registry is unchanged
        self.assertEqual(self.registry.get("classifier1"), self.classifier1)

    def test_get_nonexistent(self):
        """Test getting a non-existent classifier."""
        self.assertIsNone(self.registry.get("nonexistent"))

    def test_get_all(self):
        """Test getting all registered classifiers."""
        self.registry.register(self.classifier1)
        self.registry.register(self.classifier2)

        all_classifiers = self.registry.get_all()
        self.assertEqual(len(all_classifiers), 2)
        self.assertIn(self.classifier1, all_classifiers)
        self.assertIn(self.classifier2, all_classifiers)


class TestClassificationPipeline(unittest.TestCase):
    """Tests for the ClassificationPipeline class.
    
    These tests verify that the ClassificationPipeline correctly executes classifiers
    in sequence, handles context-aware classifiers appropriately, and manages edge cases
    like empty pipelines and non-existent classifiers. The pipeline is responsible for
    orchestrating the classification process across multiple classifiers.
    """

    def setUp(self):
        """Set up test fixtures.
        
        Creates a registry, pipeline, and test classifiers with predefined categories.
        """
        self.registry = ClassifierRegistry()
        self.pipeline = ClassificationPipeline(self.registry)
        
        # Create and register classifiers
        self.social_classifier = MockClassifier("social_classifier", Category.SOCIAL_MEDIA)
        self.work_classifier = MockClassifier("work_classifier", Category.PRODUCTIVITY)
        self.null_classifier = MockClassifier("null_classifier", None)
        self.context_classifier = MockContextAwareClassifier(
            "context_classifier", None, Category.ENTERTAINMENT
        )
        
        self.registry.register(self.social_classifier)
        self.registry.register(self.work_classifier)
        self.registry.register(self.null_classifier)
        self.registry.register(self.context_classifier)

    def test_add_classifier(self):
        """Test adding classifiers to the pipeline."""
        self.pipeline.add_classifier("social_classifier")
        self.pipeline.add_classifier("work_classifier")
        
        # Implementation detail: _pipeline is a list of classifier names
        self.assertEqual(len(self.pipeline._pipeline), 2)
        self.assertIn("social_classifier", self.pipeline._pipeline)
        self.assertIn("work_classifier", self.pipeline._pipeline)

    def test_add_nonexistent_classifier(self):
        """Test adding a non-existent classifier raises ValueError."""
        with self.assertRaises(ValueError):
            self.pipeline.add_classifier("nonexistent")

    def test_remove_classifier(self):
        """Test removing classifiers from the pipeline."""
        self.pipeline.add_classifier("social_classifier")
        self.pipeline.add_classifier("work_classifier")
        
        self.pipeline.remove_classifier("social_classifier")
        self.assertEqual(len(self.pipeline._pipeline), 1)
        self.assertNotIn("social_classifier", self.pipeline._pipeline)
        self.assertIn("work_classifier", self.pipeline._pipeline)

    def test_classify_empty_pipeline(self):
        """Test classify with an empty pipeline."""
        domain = Domain("example.com")
        result = self.pipeline.classify(domain)
        self.assertIsNone(result)

    def test_classify_first_match(self):
        """Test that classify returns the first non-None result.
        
        This test verifies that the classification pipeline returns the first
        non-None result from the classifiers in the pipeline.
        """
        self.pipeline.add_classifier("null_classifier")
        self.pipeline.add_classifier("social_classifier")
        self.pipeline.add_classifier("work_classifier")
        
        domain = Domain("example.com")
        result = self.pipeline.classify(domain)
        self.assertEqual(result, Category.SOCIAL_MEDIA)

    def test_classify_no_match(self):
        """Test classify when no classifier returns a non-None result."""
        self.pipeline.add_classifier("null_classifier")
        
        domain = Domain("example.com")
        result = self.pipeline.classify(domain)
        self.assertIsNone(result)

    def test_classify_with_context(self):
        """Test classify with context for context-aware classifiers.
        
        This test verifies that the classification pipeline correctly uses
        context when available for context-aware classifiers.
        """
        self.pipeline.add_classifier("null_classifier")
        self.pipeline.add_classifier("context_classifier")
        
        domain = Domain("example.com")
        context = {"path": "/videos"}
        
        # Without context, it should return None
        result = self.pipeline.classify(domain)
        self.assertIsNone(result)
        
        # With context, it should return the context category
        result = self.pipeline.classify(domain, context)
        self.assertEqual(result, Category.ENTERTAINMENT)
        
    def test_classify_with_nonexistent_classifier(self):
        """Test classify with a non-existent classifier in the pipeline.
        
        This test verifies that the classification pipeline gracefully handles
        the case where a classifier in the pipeline no longer exists in the registry.
        """
        # Add a valid classifier to the pipeline
        self.pipeline.add_classifier("social_classifier")
        
        # Manually add a non-existent classifier name to the pipeline
        # This simulates a classifier that was removed from the registry
        # after being added to the pipeline
        self.pipeline._pipeline.append("nonexistent_classifier")
        
        # Classify a domain
        domain = Domain("example.com")
        result = self.pipeline.classify(domain)
        
        # The pipeline should skip the non-existent classifier and return
        # the result from the valid classifier
        self.assertEqual(result, Category.SOCIAL_MEDIA)
        
    def test_pipeline_with_only_nonexistent_classifier(self):
        """Test classify with only non-existent classifiers in the pipeline.
        
        This test verifies that the classification pipeline gracefully handles
        the case where all classifiers in the pipeline no longer exist in the registry.
        """
        # Create an empty pipeline and add only a non-existent classifier
        self.pipeline._pipeline = ["nonexistent_classifier1", "nonexistent_classifier2"]
        
        # Classify a domain
        domain = Domain("example.com")
        result = self.pipeline.classify(domain)
        
        # The pipeline should skip all non-existent classifiers and return None
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
