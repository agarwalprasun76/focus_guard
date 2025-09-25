"""
Tests for the CategoryBlockerStrategy class.

This module contains tests for the CategoryBlockerStrategy, which is responsible for
blocking domains based on their assigned categories. The strategy considers:

1. Globally blocked categories (e.g., social media, entertainment)
2. Focus mode-specific blocked categories (e.g., social media during work focus mode)
3. Time-based rules (e.g., block entertainment during work hours)
4. Whitelisted domains that should never be blocked

The tests verify that the strategy correctly applies these rules and provides
appropriate blocking decisions with clear reason messages.

Note: The CategoryBlockerStrategy expects domains to have a 'category' attribute,
which is not present in the actual Domain class. In these tests, we patch the
Domain class to add this attribute during test setup.
"""

import unittest
from unittest.mock import MagicMock, patch

from core_v2.domain.models import Domain, Category
from core_v2.blocking.strategies.category_blocker import CategoryBlockerStrategy
from core_v2.classification.base import Classifier


class MockClassifier(Classifier):
    """Mock classifier for testing purposes.
    
    This class simulates a domain classifier that maps domain values to categories.
    It implements the same interface as the real classifiers but uses a predefined
    mapping instead of actual classification logic.
    """
    
    def __init__(self, classification_map=None):
        """Initialize the mock classifier with a predefined classification map.
        
        Args:
            classification_map: A dictionary mapping domain values to Category enum values.
                               Defaults to an empty dictionary if not provided.
        """
        self._classification_map = classification_map or {}
        self._name = "mock_classifier"
    
    @property
    def name(self) -> str:
        """Get the name of the classifier.
        
        Returns:
            The name of this classifier instance.
        """
        return self._name
    
    def classify(self, domain):
        """Classify a domain based on the predefined classification map.
        
        Args:
            domain: A Domain object to classify.
            
        Returns:
            The Category enum value for the domain, or None if not found.
        """
        return self._classification_map.get(domain.value)
    
    def classify_with_context(self, domain, context):
        """Classify a domain with context based on the classification map.
        
        This implementation ignores the context and delegates to the regular classify method.
        
        Args:
            domain: A Domain object to classify.
            context: Additional context information (ignored in this mock).
            
        Returns:
            The Category enum value for the domain, or None if not found.
        """
        return self.classify(domain)
    
    def reload(self):
        """Mock reload method.
        
        This method is required by the classifier interface but does nothing in the mock.
        """
        pass


class TestCategoryBlockerStrategy(unittest.TestCase):
    """Tests for the CategoryBlockerStrategy class."""
    
    def setUp(self):
        """Set up test fixtures before each test.
        
        This method:
        1. Creates a mock config loader with predefined blocking rules
        2. Sets up a domain-to-category mapping for test domains
        3. Patches the Domain.__init__ method to add a category attribute
        4. Instantiates the CategoryBlockerStrategy with the mock config loader
        """
        # Create a mock config loader
        self.mock_config_loader = MagicMock()
        
        # Create a mock blocking config
        mock_blocking_config = MagicMock()
        mock_blocking_config.blocked_categories = [Category.SOCIAL_MEDIA, Category.ENTERTAINMENT, Category.SHOPPING]
        mock_blocking_config.whitelist = ["github.com", "gitlab.com"]
        mock_blocking_config.focus_mode_categories = {
            "work": [Category.SOCIAL_MEDIA, Category.ENTERTAINMENT, Category.SHOPPING],
            "study": [Category.SOCIAL_MEDIA, Category.ENTERTAINMENT, Category.SHOPPING, Category.NEWS]
        }
        mock_blocking_config.time_based_rules = []
        
        # Configure the mock config loader to return our mock blocking config
        self.mock_config_loader.get_blocking_config.return_value = mock_blocking_config
        
        # Create a domain-to-category mapping for our tests
        self.domain_to_category = {
            "facebook.com": Category.SOCIAL_MEDIA,
            "twitter.com": Category.SOCIAL_MEDIA,
            "youtube.com": Category.ENTERTAINMENT,
            "netflix.com": Category.ENTERTAINMENT,
            "amazon.com": Category.SHOPPING,
            "ebay.com": Category.SHOPPING,
            "github.com": Category.PRODUCTIVITY,
            "gitlab.com": Category.PRODUCTIVITY,
            "nytimes.com": Category.NEWS,
            "cnn.com": Category.NEWS
        }
        
        # Save the original Domain.__init__ method
        self.original_domain_init = Domain.__init__
        
        # Patch the Domain.__init__ method to add a category property
        def patched_init(self_domain, value):
            self.original_domain_init(self_domain, value)
            # Add a category property that returns the category from our mapping
            self_domain.category = self.domain_to_category.get(value)
        
        # Apply the patch
        Domain.__init__ = patched_init
        
        # Create the strategy
        self.strategy = CategoryBlockerStrategy(self.mock_config_loader)
    
    def test_name_property(self):
        """Test the name property."""
        self.assertEqual(self.strategy.name, "category_blocker")
    
    def test_priority_property(self):
        """Test the priority property.

        The priority property determines the order in which blocking strategies are applied.
        A lower priority value means the strategy will be applied earlier.
        In this case, we expect the priority to be 50, which is a medium priority.
        """
        # Verify the priority value is as expected (medium priority)
        self.assertEqual(self.strategy.priority, 50)
    
    def test_should_block_blocked_category(self):
        """Test blocking a domain in a blocked category.
        
        This test verifies that domains in globally blocked categories (social media,
        entertainment, shopping) are correctly identified as blocked, with appropriate
        reason messages indicating which category triggered the block.
        """
        # Create domains in blocked categories
        social_domain = Domain("facebook.com")
        entertainment_domain = Domain("youtube.com")
        shopping_domain = Domain("amazon.com")
        
        # Check if the domains should be blocked
        social_decision = self.strategy.should_block(social_domain)
        entertainment_decision = self.strategy.should_block(entertainment_domain)
        shopping_decision = self.strategy.should_block(shopping_domain)
        
        # Verify that the domains are blocked
        self.assertTrue(social_decision.should_block)
        self.assertEqual(social_decision.reason, "Category SOCIAL_MEDIA is blocked")
        
        self.assertTrue(entertainment_decision.should_block)
        self.assertEqual(entertainment_decision.reason, "Category ENTERTAINMENT is blocked")
        
        self.assertTrue(shopping_decision.should_block)
        self.assertEqual(shopping_decision.reason, "Category SHOPPING is blocked")
    
    def test_should_block_non_blocked_category(self):
        """Test not blocking a domain in a non-blocked category.
        
        This test verifies that domains in categories that are not globally blocked
        (e.g., NEWS) are correctly identified as not blocked. The test creates a custom
        blocking configuration with an empty whitelist to ensure the test is focused
        solely on the category-based blocking logic.
        """
        # Create a domain in a non-blocked category that is not whitelisted
        # First, create a new mock blocking config with different blocked categories
        mock_blocking_config = MagicMock()
        mock_blocking_config.blocked_categories = [Category.SOCIAL_MEDIA, Category.ENTERTAINMENT, Category.SHOPPING]
        mock_blocking_config.whitelist = []  # Empty whitelist
        mock_blocking_config.focus_mode_categories = {}
        mock_blocking_config.time_based_rules = []
        
        # Update the mock config loader to return our mock blocking config
        self.mock_config_loader.get_blocking_config.return_value = mock_blocking_config
        
        # Create domains in non-blocked categories
        news_domain = Domain("nytimes.com")  # NEWS category, not in blocked_categories
        
        # Check if the domain should be blocked
        news_decision = self.strategy.should_block(news_domain)
        
        # Verify that the domain is not blocked
        self.assertFalse(news_decision.should_block)
        self.assertIsNone(news_decision.reason)
        
    def test_should_block_domain_with_no_category(self):
        """Test behavior for a domain with no category.
        
        This test verifies the strategy's behavior when encountering a domain that
        doesn't have a category assigned. This is an important edge case as not all
        domains may be categorized in the system. In this case, the strategy should
        gracefully handle the situation by not blocking the domain and returning a
        decision with no reason.
        
        The test uses a domain that is not in our domain-to-category mapping, which
        means it will have a None category when accessed through the patched Domain class.
        """
        # Create a domain with no category
        domain = Domain("unknown-domain.com")
        
        # Check if the domain should be blocked
        decision = self.strategy.should_block(domain)
        
        # Verify that the domain is not blocked
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
        
    def test_should_block_with_context_no_category(self):
        """Test handling a domain with no category in context-based blocking."""
        # Create a domain with no category
        unknown_domain = Domain("jira.com")  # This domain has None category in our setup
        
        # Create a context with focus mode
        context = {"focus_mode": "work"}
        
        # Check if the domain should be blocked with context
        decision = self.strategy.should_block_with_context(unknown_domain, context)
        
        # Verify that the domain is not blocked
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
    
    def test_should_block_whitelisted_domain(self):
        """Test not blocking a whitelisted domain.
        
        This test verifies that domains in the whitelist are never blocked, even if they
        belong to a category that would normally be blocked. The whitelist takes precedence
        over category-based blocking rules. The test checks that the blocking decision
        correctly indicates the domain is whitelisted in the reason message.
        """
        # Create whitelisted domains
        github_domain = Domain("github.com")
        gitlab_domain = Domain("gitlab.com")
        
        # Check if the domains should be blocked
        github_decision = self.strategy.should_block(github_domain)
        gitlab_decision = self.strategy.should_block(gitlab_domain)
        
        # Verify that the domains are not blocked
        self.assertFalse(github_decision.should_block)
        self.assertEqual(github_decision.reason, "Domain github.com is in the whitelist")
        
        self.assertFalse(gitlab_decision.should_block)
        self.assertEqual(gitlab_decision.reason, "Domain gitlab.com is in the whitelist")
        
    def test_should_block_with_context_whitelisted_domain(self):
        """Test not blocking a whitelisted domain with context."""
        # Create a whitelisted domain
        github_domain = Domain("github.com")
        
        # Create a context with focus mode that would normally block this category
        context = {"focus_mode": "work"}
        
        # Check if the domain should be blocked with context
        decision = self.strategy.should_block_with_context(github_domain, context)
        
        # Verify that the domain is not blocked due to being whitelisted
        self.assertFalse(decision.should_block)
        self.assertEqual(decision.reason, "Domain github.com is in the whitelist")
    
    def test_should_block_with_context_no_focus_mode(self):
        """Test blocking with context but no focus mode.
        
        This test verifies that when a context is provided but it doesn't contain
        a focus mode key, the strategy falls back to the regular blocking rules.
        In this case, a social media domain should be blocked because it's in the
        globally blocked categories list, and the reason should reflect that it's
        blocked due to its category, not due to any focus mode.
        """
        # Create a domain in a blocked category
        domain = Domain("facebook.com")
        
        # Create a context without focus mode
        context = {"some_key": "some_value"}
        
        # Check if the domain should be blocked with context
        decision = self.strategy.should_block_with_context(domain, context)
        
        # Verify that the domain is blocked
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "Category SOCIAL_MEDIA is blocked")
        
    def test_should_block_no_blocking_config(self):
        """Test behavior when no blocking config is available.
        
        This test verifies the strategy's behavior when the config loader returns None
        for the blocking configuration. This is an important edge case that could occur
        if the configuration is missing or corrupted. In this case, the strategy should
        gracefully handle the situation by not blocking any domains and returning a
        decision with no reason.
        """
        # Create a domain
        domain = Domain("facebook.com")
        
        # Configure the mock config loader to return None for blocking config
        self.mock_config_loader.get_blocking_config.return_value = None
        
        # Check if the domain should be blocked
        decision = self.strategy.should_block(domain)
        
        # Verify that the domain is not blocked
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
        
    def test_should_block_with_context_no_blocking_config(self):
        """Test context-based blocking when no blocking config is available.
        
        This test verifies the strategy's behavior when the config loader returns None
        for the blocking configuration, but a context with focus mode is provided.
        Even with a valid focus mode in the context, if there's no blocking configuration
        available, the strategy should gracefully handle this edge case by not blocking
        any domains and returning a decision with no reason.
        """
        # Create a domain
        domain = Domain("facebook.com")
        
        # Create a context with focus mode
        context = {"focus_mode": "work"}
        
        # Configure the mock config loader to return None for blocking config
        self.mock_config_loader.get_blocking_config.return_value = None
        
        # Check if the domain should be blocked with context
        decision = self.strategy.should_block_with_context(domain, context)
        
        # Verify that the domain is not blocked
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
    
    def test_should_block_with_context_work_focus_mode(self):
        """Test blocking with context in work focus mode.
        
        This test verifies that the strategy correctly applies the 'work' focus mode
        blocking rules. In work focus mode, social media, entertainment, and shopping
        categories should be blocked, while news should remain accessible. The test
        checks both the blocking decision and the specific reason message that
        indicates the focus mode.
        """
        # Create domains in different categories
        social_domain = Domain("facebook.com")
        entertainment_domain = Domain("youtube.com")
        shopping_domain = Domain("amazon.com")
        news_domain = Domain("nytimes.com")
        
        # Create a context with work focus mode
        context = {"focus_mode": "work"}
        
        # Check if the domains should be blocked with context
        social_decision = self.strategy.should_block_with_context(social_domain, context)
        entertainment_decision = self.strategy.should_block_with_context(entertainment_domain, context)
        shopping_decision = self.strategy.should_block_with_context(shopping_domain, context)
        news_decision = self.strategy.should_block_with_context(news_domain, context)
        
        # Verify that the domains are blocked according to work focus mode
        self.assertTrue(social_decision.should_block)
        self.assertEqual(social_decision.reason, "Category SOCIAL_MEDIA is blocked in focus mode work")
        
        self.assertTrue(entertainment_decision.should_block)
        self.assertEqual(entertainment_decision.reason, "Category ENTERTAINMENT is blocked in focus mode work")
        
        self.assertTrue(shopping_decision.should_block)
        self.assertEqual(shopping_decision.reason, "Category SHOPPING is blocked in focus mode work")
        
        # News is not blocked in work focus mode
        self.assertFalse(news_decision.should_block)
        self.assertIsNone(news_decision.reason)
    
    def test_should_block_with_context_study_focus_mode(self):
        """Test blocking with context in study focus mode."""
        # Create domains in different categories
        social_domain = Domain("facebook.com")
        entertainment_domain = Domain("youtube.com")
        shopping_domain = Domain("amazon.com")
        news_domain = Domain("nytimes.com")
        
        # Create a context with study focus mode
        context = {"focus_mode": "study"}
        
        # Check if the domains should be blocked with context
        social_decision = self.strategy.should_block_with_context(social_domain, context)
        entertainment_decision = self.strategy.should_block_with_context(entertainment_domain, context)
        shopping_decision = self.strategy.should_block_with_context(shopping_domain, context)
        news_decision = self.strategy.should_block_with_context(news_domain, context)
        
        # Verify that the domains are blocked according to study focus mode
        self.assertTrue(social_decision.should_block)
        self.assertEqual(social_decision.reason, "Category SOCIAL_MEDIA is blocked in focus mode study")
        
        self.assertTrue(entertainment_decision.should_block)
        self.assertEqual(entertainment_decision.reason, "Category ENTERTAINMENT is blocked in focus mode study")
        
        self.assertTrue(shopping_decision.should_block)
        self.assertEqual(shopping_decision.reason, "Category SHOPPING is blocked in focus mode study")
        
        # News is also blocked in study focus mode
        self.assertTrue(news_decision.should_block)
        self.assertEqual(news_decision.reason, "Category NEWS is blocked in focus mode study")
        
    def test_should_block_with_context_time_based_rules(self):
        """Test blocking with time-based rules.
        
        This test verifies that the strategy correctly applies time-based blocking rules.
        It creates a mock time-based rule that blocks social media between 9:00 AM and 5:00 PM,
        then tests that a social media domain is blocked when the current time (12:00 PM)
        falls within this range. The test checks both the blocking decision and the specific
        reason message that indicates the time-based block.
        
        This test is particularly important as it covers the time-based blocking functionality
        which allows for scheduling when certain categories should be blocked, regardless of
        the global blocking settings or focus mode.
        """
        # Create a domain in a category
        social_domain = Domain("facebook.com")
        
        # Create a mock time-based rule
        from datetime import time
        mock_rule = MagicMock()
        mock_rule.start_time = time(9, 0)  # 9:00 AM
        mock_rule.end_time = time(17, 0)  # 5:00 PM
        mock_rule.blocked_categories = [Category.SOCIAL_MEDIA]
        
        # Create a new mock blocking config with time-based rules
        mock_blocking_config = MagicMock()
        mock_blocking_config.blocked_categories = []  # No globally blocked categories
        mock_blocking_config.whitelist = []
        mock_blocking_config.focus_mode_categories = {}
        mock_blocking_config.time_based_rules = [mock_rule]
        
        # Update the mock config loader to return our mock blocking config
        self.mock_config_loader.get_blocking_config.return_value = mock_blocking_config
        
        # Create a context with current time within the rule's time range
        context = {"current_time": time(12, 0)}  # 12:00 PM
        
        # Check if the domain should be blocked with context
        decision = self.strategy.should_block_with_context(social_domain, context)
        
        # Verify that the domain is blocked due to time-based rule
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "Category SOCIAL_MEDIA is blocked during scheduled time")
    
    def tearDown(self):
        """Restore the original Domain.__init__ method after each test.
        
        This method is called after each test method completes, ensuring that the
        Domain class is restored to its original state. This is crucial to prevent
        side effects between tests and to avoid affecting other test modules that
        might use the Domain class.
        
        The tearDown method is part of the unittest framework's test lifecycle and
        helps maintain test isolation and cleanliness.
        """
        Domain.__init__ = self.original_domain_init

    def test_reload(self):
        """Test reloading the strategy."""
        # Create a new mock blocking config with different blocked categories
        new_mock_blocking_config = MagicMock()
        new_mock_blocking_config.blocked_categories = [
            Category.SOCIAL_MEDIA, Category.NEWS  # Removed entertainment and shopping, added news
        ]
        new_mock_blocking_config.whitelist = ["github.com", "gitlab.com"]
        new_mock_blocking_config.focus_mode_categories = {
            "work": [Category.SOCIAL_MEDIA, Category.NEWS],
            "study": [Category.SOCIAL_MEDIA, Category.NEWS]
        }
        new_mock_blocking_config.time_based_rules = []
        
        # Update the mock config loader to return the new blocking config
        self.mock_config_loader.get_blocking_config.return_value = new_mock_blocking_config
        
        # Reload the strategy
        self.strategy.reload()
        
        # Create domains in different categories
        social_domain = Domain("facebook.com")
        entertainment_domain = Domain("youtube.com")
        shopping_domain = Domain("amazon.com")
        news_domain = Domain("nytimes.com")
        
        # Check if the domains should be blocked
        social_decision = self.strategy.should_block(social_domain)
        entertainment_decision = self.strategy.should_block(entertainment_domain)
        shopping_decision = self.strategy.should_block(shopping_domain)
        news_decision = self.strategy.should_block(news_domain)
        
        # Verify that the domains are blocked according to the new configuration
        self.assertTrue(social_decision.should_block)
        self.assertEqual(social_decision.reason, "Category SOCIAL_MEDIA is blocked")
        
        # Entertainment is no longer blocked
        self.assertFalse(entertainment_decision.should_block)
        self.assertIsNone(entertainment_decision.reason)
        
        # Shopping is no longer blocked
        self.assertFalse(shopping_decision.should_block)
        self.assertIsNone(shopping_decision.reason)
        
        # News is now blocked
        self.assertTrue(news_decision.should_block)
        self.assertEqual(news_decision.reason, "Category NEWS is blocked")


if __name__ == "__main__":
    unittest.main()
