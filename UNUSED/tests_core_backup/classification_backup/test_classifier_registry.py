"""
Tests for the classifier registry in core.

This module contains unit tests for the ClassifierRegistry class.
"""

import unittest
from unittest.mock import MagicMock

from focus_guard.core.classification.base import Classifier
from focus_guard.core.classification.classifiers.registry import ClassifierRegistry
from focus_guard.core.domain.models import Domain, Category


class MockClassifier(Classifier):
    """Mock classifier for testing."""
    
    def __init__(self, name, classification_map=None):
        """Initialize the mock classifier."""
        self._name = name
        self._classification_map = classification_map or {}
    
    @property
    def name(self) -> str:
        """Get the name of the classifier."""
        return self._name
    
    def classify(self, domain):
        """Classify a domain based on the classification map."""
        return self._classification_map.get(domain.value)
    
    def classify_with_context(self, domain, context):
        """Classify a domain with context based on the classification map."""
        return self.classify(domain)
    
    def reload(self):
        """Mock reload method."""
        pass


class TestClassifierRegistry(unittest.TestCase):
    """Tests for the ClassifierRegistry class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create the registry
        self.registry = ClassifierRegistry()
    
    def test_register_and_get(self):
        """Test registering and getting a classifier."""
        # Create a classifier
        classifier = MockClassifier("test_classifier")
        
        # Register the classifier
        self.registry.register(classifier)
        
        # Get the classifier
        retrieved_classifier = self.registry.get("test_classifier")
        
        # Verify that the classifier was retrieved
        self.assertEqual(retrieved_classifier, classifier)
    
    def test_register_with_priority(self):
        """Test registering a classifier with a priority."""
        # Create classifiers
        classifier1 = MockClassifier("classifier1")
        classifier2 = MockClassifier("classifier2")
        
        # Register the classifiers with priorities
        self.registry.register(classifier1, priority=10)
        self.registry.register(classifier2, priority=20)
        
        # Get all classifiers
        classifiers = self.registry.get_all()
        
        # Verify that the classifiers are returned in priority order (highest first)
        self.assertEqual(len(classifiers), 2)
        self.assertEqual(classifiers[0], classifier2)
        self.assertEqual(classifiers[1], classifier1)
    
    def test_register_duplicate_name(self):
        """Test registering a classifier with a duplicate name."""
        # Create classifiers with the same name
        classifier1 = MockClassifier("test_classifier")
        classifier2 = MockClassifier("test_classifier")
        
        # Register the first classifier
        self.registry.register(classifier1)
        
        # Register the second classifier
        self.registry.register(classifier2)
        
        # Get the classifier
        retrieved_classifier = self.registry.get("test_classifier")
        
        # Verify that the second classifier replaced the first
        self.assertEqual(retrieved_classifier, classifier2)
    
    def test_get_nonexistent_classifier(self):
        """Test getting a nonexistent classifier."""
        # Get a nonexistent classifier
        classifier = self.registry.get("nonexistent_classifier")
        
        # Verify that None is returned
        self.assertIsNone(classifier)
    
    def test_get_all_empty(self):
        """Test getting all classifiers when the registry is empty."""
        # Get all classifiers
        classifiers = self.registry.get_all()
        
        # Verify that an empty list is returned
        self.assertEqual(len(classifiers), 0)
    
    def test_get_all_sorted(self):
        """Test that get_all returns classifiers sorted by priority."""
        # Create classifiers
        classifier1 = MockClassifier("classifier1")
        classifier2 = MockClassifier("classifier2")
        classifier3 = MockClassifier("classifier3")
        
        # Register the classifiers with priorities
        self.registry.register(classifier1, priority=10)
        self.registry.register(classifier2, priority=30)
        self.registry.register(classifier3, priority=20)
        
        # Get all classifiers
        classifiers = self.registry.get_all()
        
        # Verify that the classifiers are returned in priority order (highest first)
        self.assertEqual(len(classifiers), 3)
        self.assertEqual(classifiers[0], classifier2)
        self.assertEqual(classifiers[1], classifier3)
        self.assertEqual(classifiers[2], classifier1)
    
    def test_set_priority(self):
        """Test setting the priority of a classifier."""
        # Create classifiers
        classifier1 = MockClassifier("classifier1")
        classifier2 = MockClassifier("classifier2")
        
        # Register the classifiers with priorities
        self.registry.register(classifier1, priority=10)
        self.registry.register(classifier2, priority=20)
        
        # Set the priority of the first classifier
        self.registry.set_priority("classifier1", 30)
        
        # Get all classifiers
        classifiers = self.registry.get_all()
        
        # Verify that the classifiers are returned in the new priority order
        self.assertEqual(len(classifiers), 2)
        self.assertEqual(classifiers[0], classifier1)
        self.assertEqual(classifiers[1], classifier2)
    
    def test_set_priority_nonexistent_classifier(self):
        """Test setting the priority of a nonexistent classifier."""
        # Set the priority of a nonexistent classifier
        result = self.registry.set_priority("nonexistent_classifier", 10)
        
        # Verify that False is returned
        self.assertFalse(result)
    
    def test_unregister(self):
        """Test unregistering a classifier."""
        # Create a classifier
        classifier = MockClassifier("test_classifier")
        
        # Register the classifier
        self.registry.register(classifier)
        
        # Unregister the classifier
        result = self.registry.unregister("test_classifier")
        
        # Verify that True is returned
        self.assertTrue(result)
        
        # Get the classifier
        retrieved_classifier = self.registry.get("test_classifier")
        
        # Verify that None is returned
        self.assertIsNone(retrieved_classifier)
    
    def test_unregister_nonexistent_classifier(self):
        """Test unregistering a nonexistent classifier."""
        # Unregister a nonexistent classifier
        result = self.registry.unregister("nonexistent_classifier")
        
        # Verify that False is returned
        self.assertFalse(result)
    
    def test_classify_with_multiple_classifiers(self):
        """Test classification with multiple classifiers."""
        # Create classifiers with different classification maps
        classifier1 = MockClassifier("classifier1", {
            "example.com": Category.PRODUCTIVITY,
            "github.com": Category.PRODUCTIVITY
        })
        classifier2 = MockClassifier("classifier2", {
            "facebook.com": Category.SOCIAL_MEDIA,
            "twitter.com": Category.SOCIAL_MEDIA
        })
        
        # Register the classifiers with priorities
        self.registry.register(classifier1, priority=10)
        self.registry.register(classifier2, priority=20)
        
        # Create domains
        domain1 = Domain("github.com")
        domain2 = Domain("facebook.com")
        domain3 = Domain("unknown.com")
        
        # Classify the domains using the registry's classify method
        category1 = self.registry.classify(domain1)
        category2 = self.registry.classify(domain2)
        category3 = self.registry.classify(domain3)
        
        # Verify the classifications
        self.assertEqual(category1, Category.PRODUCTIVITY)
        self.assertEqual(category2, Category.SOCIAL_MEDIA)
        self.assertIsNone(category3)


if __name__ == "__main__":
    unittest.main()
