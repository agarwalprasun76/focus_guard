"""
Integration tests for classification and blocking components.

This module contains tests that verify the integration between
classification and blocking components in the core_v2 module.
"""

import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch

from core_v2.domain.models import Domain, Category
from core_v2.classification.base import Classifier, ClassifierRegistry, ClassificationPipeline
from core_v2.blocking.base import BlockingStrategy, BlockingStrategyRegistry, BlockingPipeline, BlockingDecision, BlockingReason


class MockSocialMediaClassifier(Classifier):
    """Mock classifier that identifies social media domains."""
    
    @property
    def name(self) -> str:
        return "social_media_classifier"
    
    def classify(self, domain: Domain) -> Category:
        social_media_domains = ["facebook.com", "twitter.com", "instagram.com", "linkedin.com"]
        if domain.value in social_media_domains or any(domain.is_subdomain_of(Domain(d)) for d in social_media_domains):
            return Category.SOCIAL_MEDIA
        return None


class MockEntertainmentClassifier(Classifier):
    """Mock classifier that identifies entertainment domains."""
    
    @property
    def name(self) -> str:
        return "entertainment_classifier"
    
    def classify(self, domain: Domain) -> Category:
        entertainment_domains = ["youtube.com", "netflix.com", "hulu.com", "twitch.tv"]
        if domain.value in entertainment_domains or any(domain.is_subdomain_of(Domain(d)) for d in entertainment_domains):
            return Category.ENTERTAINMENT
        return None


class MockCategoryBlockingStrategy(BlockingStrategy):
    """Mock blocking strategy that blocks based on category."""
    
    def __init__(self, blocked_categories):
        self.blocked_categories = blocked_categories
    
    @property
    def name(self) -> str:
        return "category_blocker"
    
    @property
    def priority(self) -> int:
        return 100
    
    def should_block(self, domain: Domain) -> BlockingDecision:
        # This would normally use the domain to get its category,
        # but for testing we'll use a mock classifier
        category = None
        
        # Simple mock classification logic
        social_media_domains = ["facebook.com", "twitter.com", "instagram.com", "linkedin.com"]
        entertainment_domains = ["youtube.com", "netflix.com", "hulu.com", "twitch.tv"]
        
        if domain.value in social_media_domains or any(domain.is_subdomain_of(Domain(d)) for d in social_media_domains):
            category = Category.SOCIAL_MEDIA
        elif domain.value in entertainment_domains or any(domain.is_subdomain_of(Domain(d)) for d in entertainment_domains):
            category = Category.ENTERTAINMENT
        
        if category in self.blocked_categories:
            return BlockingDecision(
                should_block=True,
                reason=BlockingReason.CATEGORY,
                details=f"Blocked due to category: {category.name}"
            )
        
        return BlockingDecision(should_block=False)


class MockWhitelistStrategy(BlockingStrategy):
    """Mock blocking strategy that implements a whitelist."""
    
    def __init__(self, whitelist):
        self.whitelist = whitelist
    
    @property
    def name(self) -> str:
        return "whitelist"
    
    @property
    def priority(self) -> int:
        return 200  # Higher priority than category blocker
    
    def should_block(self, domain: Domain) -> BlockingDecision:
        # If domain is in whitelist, don't block
        if domain.value in self.whitelist or any(domain.is_subdomain_of(Domain(d)) for d in self.whitelist):
            return BlockingDecision(should_block=False)
        
        # Whitelist doesn't block, it just allows
        return BlockingDecision(should_block=False)


class TestClassificationBlockingIntegration(TestCase):
    """Integration tests for classification and blocking components."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create classifier registry and pipeline
        self.classifier_registry = ClassifierRegistry()
        self.classifier_registry.register(MockSocialMediaClassifier())
        self.classifier_registry.register(MockEntertainmentClassifier())
        self.classification_pipeline = ClassificationPipeline(self.classifier_registry)
        self.classification_pipeline.add_classifier("social_media_classifier")
        self.classification_pipeline.add_classifier("entertainment_classifier")
        
        # Create blocking registry and pipeline
        self.blocking_registry = BlockingStrategyRegistry()
        self.category_blocker = MockCategoryBlockingStrategy([Category.SOCIAL_MEDIA])
        self.whitelist_strategy = MockWhitelistStrategy(["github.com", "docs.github.com"])
        self.blocking_registry.register(self.category_blocker)
        self.blocking_registry.register(self.whitelist_strategy)
        self.blocking_pipeline = BlockingPipeline(self.blocking_registry)
    
    def test_social_media_classification_and_blocking(self):
        """Test that social media domains are classified and blocked correctly."""
        domains = [
            "facebook.com",
            "www.facebook.com",
            "twitter.com",
            "mobile.twitter.com",
        ]
        
        for domain_str in domains:
            domain = Domain(domain_str)
            
            # Test classification
            category = self.classification_pipeline.classify(domain)
            self.assertEqual(category, Category.SOCIAL_MEDIA)
            
            # Test blocking
            decision = self.blocking_pipeline.should_block(domain)
            self.assertTrue(decision.should_block)
            self.assertEqual(decision.reason, BlockingReason.CATEGORY)
    
    def test_entertainment_classification_and_blocking(self):
        """Test that entertainment domains are classified correctly but not blocked."""
        domains = [
            "youtube.com",
            "www.youtube.com",
            "netflix.com",
            "watch.hulu.com",
        ]
        
        for domain_str in domains:
            domain = Domain(domain_str)
            
            # Test classification
            category = self.classification_pipeline.classify(domain)
            self.assertEqual(category, Category.ENTERTAINMENT)
            
            # Test blocking (entertainment should not be blocked)
            decision = self.blocking_pipeline.should_block(domain)
            self.assertFalse(decision.should_block)
    
    def test_whitelist_overrides_blocking(self):
        """Test that whitelisted domains are not blocked even if they match a blocked category."""
        # Create a new blocking registry with a whitelist that includes a social media site
        blocking_registry = BlockingStrategyRegistry()
        category_blocker = MockCategoryBlockingStrategy([Category.SOCIAL_MEDIA])
        whitelist_strategy = MockWhitelistStrategy(["facebook.com", "github.com"])
        blocking_registry.register(category_blocker)
        blocking_registry.register(whitelist_strategy)
        blocking_pipeline = BlockingPipeline(blocking_registry)
        
        # Facebook is a social media site but it's whitelisted
        domain = Domain("facebook.com")
        
        # Test classification
        category = self.classification_pipeline.classify(domain)
        self.assertEqual(category, Category.SOCIAL_MEDIA)
        
        # Test blocking (should not be blocked due to whitelist)
        decision = blocking_pipeline.should_block(domain)
        self.assertFalse(decision.should_block)
    
    def test_unknown_domains_not_blocked(self):
        """Test that unknown domains are not blocked."""
        domains = [
            "example.com",
            "unknown-domain.com",
            "test.org",
        ]
        
        for domain_str in domains:
            domain = Domain(domain_str)
            
            # Test classification
            category = self.classification_pipeline.classify(domain)
            self.assertIsNone(category)
            
            # Test blocking
            decision = self.blocking_pipeline.should_block(domain)
            self.assertFalse(decision.should_block)


if __name__ == "__main__":
    unittest.main()
