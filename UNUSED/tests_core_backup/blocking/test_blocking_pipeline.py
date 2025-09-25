"""
Tests for the blocking pipeline in core_v2.

This module contains unit tests for the BlockingPipeline class, which is responsible for
applying multiple blocking strategies to determine if a domain should be blocked.

The tests verify that the pipeline correctly:
- Handles empty strategy registries
- Applies strategies in priority order
- Returns the first blocking decision
- Supports context-aware blocking strategies
- Provides reload functionality for strategies
"""

import unittest
from unittest.mock import MagicMock, patch

from core_v2.domain.models import Domain, Category
from core_v2.blocking.base import BlockingStrategy, BlockingDecision
from core_v2.blocking.pipeline import BlockingPipeline
from core_v2.blocking.strategies.registry import BlockingStrategyRegistry


class MockBlockingStrategy(BlockingStrategy):
    """Mock blocking strategy for testing.
    
    This class implements the BlockingStrategy interface for testing purposes,
    allowing tests to configure the blocking behavior and priority.
    """
    
    def __init__(self, name, priority=10, should_block_result=False, reason=None):
        """Initialize the mock strategy.
        
        Args:
            name: The name of the strategy
            priority: The priority of the strategy (higher = runs earlier)
            should_block_result: Whether the strategy should decide to block
            reason: The reason for blocking, if applicable
        """
        self._name = name
        self._priority = priority
        self._should_block_result = should_block_result
        self._reason = reason
        self.reload_called = False
    
    @property
    def name(self) -> str:
        """Get the name of the strategy."""
        return self._name
    
    @property
    def priority(self) -> int:
        """Get the priority of the strategy."""
        return self._priority
    
    def should_block(self, domain):
        """Return the configured blocking decision."""
        return BlockingDecision(
            should_block=self._should_block_result,
            reason=self._reason
        )
    
    def should_block_with_context(self, domain, context):
        """Return the configured blocking decision with context."""
        return BlockingDecision(
            should_block=self._should_block_result,
            reason=self._reason
        )
    
    def reload(self):
        """Mock reload method that tracks calls."""
        self.reload_called = True


class TestBlockingPipeline(unittest.TestCase):
    """Tests for the BlockingPipeline class.
    
    These tests verify that the BlockingPipeline correctly applies blocking strategies
    in priority order and returns the appropriate blocking decision.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a registry with mock strategies
        self.registry = BlockingStrategyRegistry()
        
        # Create the pipeline with the registry
        self.pipeline = BlockingPipeline(self.registry)
    
    def test_empty_registry(self):
        """Test that no blocking occurs with an empty registry."""
        domain = Domain("example.com")
        decision = self.pipeline.should_block(domain)
        
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
    
    def test_single_strategy_no_block(self):
        """Test with a single strategy that doesn't block.
        
        This test verifies that when a single strategy decides not to block,
        the pipeline returns a non-blocking decision.
        """
        # Register a strategy that doesn't block
        strategy = MockBlockingStrategy(
            "test_strategy", 
            priority=10,
            should_block_result=False
        )
        self.registry.register(strategy)
        
        domain = Domain("example.com")
        decision = self.pipeline.should_block(domain)
        
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
    
    def test_single_strategy_block(self):
        """Test with a single strategy that blocks.
        
        This test verifies that when a single strategy decides to block,
        the pipeline returns the correct blocking decision.
        """
        # Register a strategy that blocks
        strategy = MockBlockingStrategy(
            "test_strategy",
            priority=10,
            should_block_result=True,
            reason="Test blocking reason"
        )
        self.registry.register(strategy)
        
        domain = Domain("example.com")
        decision = self.pipeline.should_block(domain)
        
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "Test blocking reason")
    
    def test_multiple_strategies_priority_order(self):
        """Test that strategies are applied in priority order.
        
        This test verifies that when multiple strategies are registered,
        they are executed in order of priority (highest first).
        """
        # Register strategies with different priorities
        strategy1 = MockBlockingStrategy(
            "low_priority",
            priority=10,
            should_block_result=True,
            reason="Low priority reason"
        )
        strategy2 = MockBlockingStrategy(
            "high_priority",
            priority=20,
            should_block_result=True,
            reason="High priority reason"
        )
        
        # Register the strategies with explicit priorities
        # Note: The registry uses these priorities, not the ones in the strategy objects
        self.registry.register(strategy1, priority=10)
        self.registry.register(strategy2, priority=20)
        
        domain = Domain("example.com")
        decision = self.pipeline.should_block(domain)
        
        # The high priority strategy should be applied first
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "High priority reason")
    
    def test_multiple_strategies_first_block_wins(self):
        """Test that the first strategy to block determines the result.
        
        This test verifies that when multiple strategies are registered,
        the first one to return a blocking decision determines the final result.
        """
        # Register strategies with different decisions
        strategy1 = MockBlockingStrategy(
            "first_strategy",
            priority=30,
            should_block_result=False
        )
        strategy2 = MockBlockingStrategy(
            "second_strategy",
            priority=20,
            should_block_result=True,
            reason="Second strategy reason"
        )
        strategy3 = MockBlockingStrategy(
            "third_strategy",
            priority=10,
            should_block_result=True,
            reason="Third strategy reason"
        )
        
        # Register the strategies
        self.registry.register(strategy1)
        self.registry.register(strategy2)
        self.registry.register(strategy3)
        
        domain = Domain("example.com")
        decision = self.pipeline.should_block(domain)
        
        # The second strategy should be the first to block
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "Second strategy reason")
    
    def test_should_block_with_context(self):
        """Test blocking with context.
        
        This test verifies that the pipeline correctly passes context information
        to strategies when using should_block_with_context.
        """
        # Register a strategy that blocks with context
        strategy = MockBlockingStrategy(
            "context_strategy",
            priority=10,
            should_block_result=True,
            reason="Context blocking reason"
        )
        self.registry.register(strategy)
        
        domain = Domain("example.com")
        context = {"focus_mode": "work"}
        decision = self.pipeline.should_block_with_context(domain, context)
        
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "Context blocking reason")
    
    def test_reload_all_strategies(self):
        """Test reloading all strategies.
        
        This test verifies that the reload_all_strategies method correctly calls
        the reload method on each registered strategy.
        """
        # Create real mock strategies with reload methods
        strategy1 = MockBlockingStrategy("strategy1", priority=10)
        strategy2 = MockBlockingStrategy("strategy2", priority=20)
        
        # Register the strategies
        self.registry.register(strategy1)
        self.registry.register(strategy2)
        
        # Reload all strategies
        self.pipeline.reload_all_strategies()
        
        # Verify that reload was called on each strategy
        self.assertTrue(strategy1.reload_called)
        self.assertTrue(strategy2.reload_called)


    def test_should_block_with_context_no_strategies(self):
        """Test should_block_with_context with no strategies.
        
        This test verifies that when no strategies are registered,
        should_block_with_context returns a non-blocking decision.
        """
        domain = Domain("example.com")
        context = {"focus_mode": "work"}
        decision = self.pipeline.should_block_with_context(domain, context)
        
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
    
    def test_reload_all_strategies_with_error(self):
        """Test reloading strategies with one that raises an error.
        
        This test verifies that the reload_all_strategies method handles errors
        gracefully when a strategy's reload method raises an exception.
        """
        # Create a strategy that will raise an exception on reload
        class ErrorStrategy(MockBlockingStrategy):
            def reload(self):
                raise ValueError("Test error")
        
        # Create strategies
        strategy1 = MockBlockingStrategy("normal_strategy", priority=10)
        strategy2 = ErrorStrategy("error_strategy", priority=20)
        
        # Register the strategies
        self.registry.register(strategy1)
        self.registry.register(strategy2)
        
        # Reload all strategies - should not raise an exception
        self.pipeline.reload_all_strategies()
        
        # Verify that reload was called on the normal strategy
        self.assertTrue(strategy1.reload_called)


if __name__ == "__main__":
    unittest.main()
