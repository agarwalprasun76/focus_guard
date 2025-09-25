"""
Tests for the blocking pipeline in core.

This module contains unit tests for the BlockingPipeline class, which is responsible for
applying multiple blocking strategies to determine if a domain should be blocked.

The tests verify that the pipeline correctly:
- Handles empty strategy registries
- Applies strategies in priority order
- Returns the first blocking decision
- Supports context-aware blocking strategies
- Provides reload functionality for strategies
"""

import asyncio
import unittest
from typing import Dict, Any
from unittest.mock import MagicMock, patch

from focus_guard.core.domain.models import Domain, Category
from focus_guard.core.blocking.base import BlockingStrategy, BlockingDecision
from focus_guard.core.blocking.pipeline import BlockingPipeline
from focus_guard.core.blocking.strategies.registry import BlockingStrategyRegistry


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
    
    async def should_block(self, domain: Domain) -> BlockingDecision:
        """Determine if access to the given domain should be blocked."""
        return BlockingDecision(
            should_block=self._should_block_result,
            reason=self._reason,
            details=f"Strategy: {self._name}" if self._reason else None
        )
    
    async def should_block_with_context(self, domain: Domain, context: Dict[str, Any]) -> BlockingDecision:
        """Determine if access should be blocked with additional context."""
        return await self.should_block(domain)
    
    def reload(self) -> None:
        """Reload the strategy's configuration."""
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
        decision = asyncio.run(self.pipeline.should_block(domain))
        self.assertIsInstance(decision, BlockingDecision)
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
        self.assertIsNone(decision.details)
    
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
        decision = asyncio.run(self.pipeline.should_block(domain))
    
        self.assertIsInstance(decision, BlockingDecision)
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
        self.assertIsNone(decision.details)
    
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
        decision = asyncio.run(self.pipeline.should_block(domain))
    
        self.assertIsInstance(decision, BlockingDecision)
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "Test blocking reason")
        self.assertEqual(decision.details, "Strategy: test_strategy")
    
    def test_multiple_strategies_priority_order(self):
        """Test that strategies are applied in priority order.
        
        This test verifies that when multiple strategies are registered,
        they are executed in order of priority (highest first) and the first
        strategy to return a blocking decision determines the result.
        """
        # Track call order
        call_order = []
        
        # Create a custom strategy that tracks call order
        class TrackingMockStrategy(MockBlockingStrategy):
            async def should_block(self, domain):
                call_order.append(self._name)
                # Only the first strategy should block
                block = len(call_order) == 1
                return BlockingDecision(
                    should_block=block,
                    reason=f"{'Blocked' if block else 'Allowed'} by {self._name}",
                    details=f"Strategy: {self._name}" if block else None
                )
        
        # Register strategies with different priorities
        strategy1 = TrackingMockStrategy("low_priority", priority=10)
        strategy2 = TrackingMockStrategy("high_priority", priority=20)
    
        # Register the strategies with explicit priorities
        self.registry.register(strategy1, priority=10)
        self.registry.register(strategy2, priority=20)
    
        domain = Domain("example.com")
        decision = asyncio.run(self.pipeline.should_block(domain))
    
        # Only the high priority strategy should be called since it returns a blocking decision
        self.assertIsInstance(decision, BlockingDecision)
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "Blocked by high_priority")
        self.assertEqual(call_order, ["high_priority"])
    
    def test_multiple_strategies_first_block_wins(self):
        """Test that the first strategy to block determines the result.
        
        This test verifies that when multiple strategies are registered,
        the first one to return a blocking decision determines the final result.
        """
        # Track which strategies were called
        called = []
        
        # Create a custom strategy that tracks calls
        class TrackingMockStrategy(MockBlockingStrategy):
            async def should_block(self, domain):
                called.append(self._name)
                return await super().should_block(domain)
        
        # Register strategies with different decisions
        strategy1 = TrackingMockStrategy(
            "first_strategy",
            priority=30,
            should_block_result=False
        )
        strategy2 = TrackingMockStrategy(
            "second_strategy",
            priority=20,
            should_block_result=True,
            reason="Second strategy reason"
        )
        strategy3 = TrackingMockStrategy(
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
        decision = asyncio.run(self.pipeline.should_block(domain))
    
        # The second strategy should be the first to block
        self.assertIsInstance(decision, BlockingDecision)
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "Second strategy reason")
        # Verify third strategy wasn't called (short-circuit evaluation)
        self.assertIn("first_strategy", called)
        self.assertIn("second_strategy", called)
        self.assertNotIn("third_strategy", called)
    
    def test_should_block_with_context(self):
        """Test blocking with context.
        
        This test verifies that the pipeline correctly passes context information
        to strategies when using should_block_with_context.
        """
        # Track the context that was passed
        received_context = {}
        
        # Create a custom strategy that captures the context
        class ContextAwareMockStrategy(MockBlockingStrategy):
            async def should_block_with_context(self, domain, context):
                nonlocal received_context
                received_context = context
                return await super().should_block(domain)
        
        # Register the strategy
        strategy = ContextAwareMockStrategy(
            "context_strategy",
            priority=10,
            should_block_result=True,
            reason="Test blocking reason"
        )
        self.registry.register(strategy)
    
        domain = Domain("example.com")
        context = {"focus_mode": "work"}
        decision = asyncio.run(self.pipeline.should_block_with_context(domain, context))
    
        self.assertIsInstance(decision, BlockingDecision)
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, "Test blocking reason")
        self.assertEqual(decision.details, "Strategy: context_strategy")
        self.assertEqual(received_context, context)
    
    def test_reload_all_strategies(self):
        """Test reloading all strategies.
        
        This test verifies that the reload_all_strategies method correctly calls
        the reload method on each registered strategy.
        """
        # Create strategies
        strategy1 = MockBlockingStrategy("strategy1")
        strategy2 = MockBlockingStrategy("strategy2")
        
        # Register strategies
        self.registry.register(strategy1)
        self.registry.register(strategy2)
        
        # Verify reload hasn't been called yet
        self.assertFalse(strategy1.reload_called)
        self.assertFalse(strategy2.reload_called)
        
        # Call reload
        self.pipeline.reload_all_strategies()
        
        # Verify reload was called on both strategies
        self.assertTrue(strategy1.reload_called)
        self.assertTrue(strategy2.reload_called)


    def test_should_block_with_context_no_strategies(self):
        """Test should_block_with_context with no strategies.
        
        This test verifies that when no strategies are registered,
        should_block_with_context returns a non-blocking decision.
        """
        domain = Domain("example.com")
        context = {"focus_mode": "work"}
        decision = asyncio.run(self.pipeline.should_block_with_context(domain, context))
    
        self.assertIsInstance(decision, BlockingDecision)
        self.assertFalse(decision.should_block)
        self.assertIsNone(decision.reason)
        self.assertIsNone(decision.details)


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
