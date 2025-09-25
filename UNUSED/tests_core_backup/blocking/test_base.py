"""
Unit tests for the blocking base classes.

This module tests the core interfaces and classes for domain blocking, including:
- BlockingReason enum: Defines reasons why a domain might be blocked
- BlockingDecision class: Represents a decision to block or allow a domain
- BlockingStrategy interface: Base interface for domain blocking strategies
- ContextAwareBlockingStrategy interface: Interface for strategies that use additional context
- BlockingStrategyRegistry: Registry for managing blocking strategies
- BlockingPipeline: Pipeline for executing multiple blocking strategies in sequence

The tests verify the correct behavior of these components, including their
interactions and the enforcement of abstract method implementations.
"""

import unittest
from unittest.mock import Mock, patch

from core_v2.blocking.base import (
    BlockingReason,
    BlockingDecision,
    BlockingStrategy,
    ContextAwareBlockingStrategy,
    BlockingStrategyRegistry,
    BlockingPipeline,
)
from core_v2.domain.models import Domain


class TestBlockingReason(unittest.TestCase):
    """Tests for the BlockingReason enum.
    
    These tests verify that all expected blocking reasons are defined in the enum.
    The BlockingReason enum is used to categorize why a domain was blocked.
    """

    def test_blocking_reason_values(self):
        """Test that all expected blocking reasons are defined."""
        self.assertTrue(hasattr(BlockingReason, "CATEGORY"))
        self.assertTrue(hasattr(BlockingReason, "DOMAIN_EXCLUDED"))
        self.assertTrue(hasattr(BlockingReason, "USER_BLOCKED"))
        self.assertTrue(hasattr(BlockingReason, "CONTENT_POLICY"))
        self.assertTrue(hasattr(BlockingReason, "YOUTUBE_CONTENT"))
        self.assertTrue(hasattr(BlockingReason, "OTHER"))


class TestBlockingDecision(unittest.TestCase):
    """Tests for the BlockingDecision class.
    
    These tests verify that the BlockingDecision class correctly handles initialization
    with various combinations of parameters. The BlockingDecision class represents
    the outcome of a blocking strategy's decision process.
    """

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        decision = BlockingDecision(should_block=True)
        self.assertTrue(decision.should_block)
        self.assertIsNone(decision.reason)
        self.assertIsNone(decision.details)

    def test_init_with_reason(self):
        """Test initialization with a reason."""
        decision = BlockingDecision(
            should_block=True,
            reason=BlockingReason.CATEGORY,
        )
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, BlockingReason.CATEGORY)
        self.assertIsNone(decision.details)

    def test_init_with_details(self):
        """Test initialization with details."""
        decision = BlockingDecision(
            should_block=True,
            reason=BlockingReason.CATEGORY,
            details="Blocked due to social media category",
        )
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, BlockingReason.CATEGORY)
        self.assertEqual(decision.details, "Blocked due to social media category")


class MockBlockingStrategy(BlockingStrategy):
    """Mock implementation of BlockingStrategy for testing."""

    def __init__(self, name, priority, should_block_result=False):
        self._name = name
        self._priority = priority
        self._should_block_result = should_block_result

    def should_block(self, domain):
        return BlockingDecision(
            should_block=self._should_block_result,
            reason=BlockingReason.CATEGORY if self._should_block_result else None,
            details=f"Decision from {self._name}" if self._should_block_result else None,
        )

    @property
    def name(self):
        return self._name

    @property
    def priority(self):
        return self._priority


class MockContextAwareBlockingStrategy(ContextAwareBlockingStrategy):
    """Mock implementation of ContextAwareBlockingStrategy for testing."""

    def __init__(self, name, priority, should_block_result=False, context_aware_result=False):
        self._name = name
        self._priority = priority
        self._should_block_result = should_block_result
        self._context_aware_result = context_aware_result

    def should_block(self, domain):
        return BlockingDecision(
            should_block=self._should_block_result,
            reason=BlockingReason.CATEGORY if self._should_block_result else None,
            details=f"Decision from {self._name}" if self._should_block_result else None,
        )

    def should_block_with_context(self, domain, context):
        return BlockingDecision(
            should_block=self._context_aware_result,
            reason=BlockingReason.CONTENT_POLICY if self._context_aware_result else None,
            details=f"Context-aware decision from {self._name}" if self._context_aware_result else None,
        )

    @property
    def name(self):
        return self._name

    @property
    def priority(self):
        return self._priority


class TestBlockingStrategyRegistry(unittest.TestCase):
    """Tests for the BlockingStrategyRegistry class.
    
    These tests verify that the BlockingStrategyRegistry correctly manages the
    registration, unregistration, and retrieval of blocking strategies. The registry
    is a central component that maintains a collection of available strategies.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.registry = BlockingStrategyRegistry()
        self.strategy1 = MockBlockingStrategy("strategy1", 10)
        self.strategy2 = MockBlockingStrategy("strategy2", 20)

    def test_register(self):
        """Test registering strategies."""
        self.registry.register(self.strategy1)
        self.assertEqual(self.registry.get("strategy1"), self.strategy1)

        self.registry.register(self.strategy2)
        self.assertEqual(self.registry.get("strategy2"), self.strategy2)

    def test_unregister(self):
        """Test unregistering strategies."""
        self.registry.register(self.strategy1)
        self.registry.register(self.strategy2)

        self.registry.unregister("strategy1")
        self.assertIsNone(self.registry.get("strategy1"))
        self.assertEqual(self.registry.get("strategy2"), self.strategy2)

    def test_get_nonexistent(self):
        """Test getting a non-existent strategy."""
        self.assertIsNone(self.registry.get("nonexistent"))

    def test_get_all(self):
        """Test getting all registered strategies."""
        self.registry.register(self.strategy1)
        self.registry.register(self.strategy2)

        all_strategies = self.registry.get_all()
        self.assertEqual(len(all_strategies), 2)
        self.assertIn(self.strategy1, all_strategies)
        self.assertIn(self.strategy2, all_strategies)


class TestBlockingPipeline(unittest.TestCase):
    """Tests for the BlockingPipeline class.
    
    These tests verify that the BlockingPipeline correctly executes blocking strategies
    in priority order and returns the appropriate blocking decision. The pipeline
    is responsible for coordinating the execution of multiple strategies.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.registry = BlockingStrategyRegistry()
        self.pipeline = BlockingPipeline(self.registry)

    def test_should_block_empty_pipeline(self):
        """Test should_block with an empty pipeline."""
        domain = Domain("example.com")
        decision = self.pipeline.should_block(domain)
        self.assertFalse(decision.should_block)

    def test_should_block_no_blocking_strategies(self):
        """Test should_block with strategies that don't block."""
        self.registry.register(MockBlockingStrategy("strategy1", 10, False))
        self.registry.register(MockBlockingStrategy("strategy2", 20, False))

        domain = Domain("example.com")
        decision = self.pipeline.should_block(domain)
        self.assertFalse(decision.should_block)

    def test_should_block_with_blocking_strategy(self):
        """Test should_block with a strategy that blocks."""
        self.registry.register(MockBlockingStrategy("strategy1", 10, False))
        self.registry.register(MockBlockingStrategy("strategy2", 20, True))

        domain = Domain("example.com")
        decision = self.pipeline.should_block(domain)
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, BlockingReason.CATEGORY)
        self.assertEqual(decision.details, "Decision from strategy2")

    def test_should_block_priority_order(self):
        """Test that strategies are executed in priority order."""
        # Even though strategy1 would block, strategy2 has higher priority and runs first
        self.registry.register(MockBlockingStrategy("strategy1", 10, True))
        self.registry.register(MockBlockingStrategy("strategy2", 20, True))

        domain = Domain("example.com")
        decision = self.pipeline.should_block(domain)
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.details, "Decision from strategy2")

    def test_should_block_with_context(self):
        """Test should_block with context for context-aware strategies."""
        # Regular strategy that doesn't block
        self.registry.register(MockBlockingStrategy("strategy1", 10, False))
        # Context-aware strategy that blocks only with context
        self.registry.register(
            MockContextAwareBlockingStrategy("context_strategy", 20, False, True)
        )

        domain = Domain("example.com")
        context = {"path": "/sensitive-content"}

        # Without context, it shouldn't block
        decision = self.pipeline.should_block(domain)
        self.assertFalse(decision.should_block)

        # With context, it should block
        decision = self.pipeline.should_block(domain, context)
        self.assertTrue(decision.should_block)
        self.assertEqual(decision.reason, BlockingReason.CONTENT_POLICY)
        self.assertEqual(decision.details, "Context-aware decision from context_strategy")


class TestAbstractClasses(unittest.TestCase):
    """Tests for abstract base classes and their method enforcement.
    
    These tests verify that the abstract base classes correctly enforce the
    implementation of their abstract methods. This ensures that concrete
    subclasses must provide implementations for all required functionality.
    """
    
    def test_blocking_strategy_cannot_be_instantiated(self):
        """Test that BlockingStrategy cannot be instantiated directly.
        
        This test verifies that attempting to instantiate the abstract BlockingStrategy
        class without implementing its abstract methods raises a TypeError.
        """
        with self.assertRaises(TypeError):
            BlockingStrategy()
    
    def test_blocking_strategy_abstract_methods(self):
        """Test that BlockingStrategy enforces implementation of abstract methods.
        
        This test verifies that a subclass of BlockingStrategy must implement all
        abstract methods to be instantiable.
        """
        # Create a partial implementation missing some methods
        class PartialBlockingStrategy(BlockingStrategy):
            @property
            def name(self):
                return "partial"
                
            @property
            def priority(self):
                return 10
        
        # Should still raise TypeError because should_block is not implemented
        with self.assertRaises(TypeError):
            PartialBlockingStrategy()
    
    def test_context_aware_blocking_strategy_cannot_be_instantiated(self):
        """Test that ContextAwareBlockingStrategy cannot be instantiated directly.
        
        This test verifies that attempting to instantiate the abstract
        ContextAwareBlockingStrategy class without implementing its abstract methods
        raises a TypeError.
        """
        with self.assertRaises(TypeError):
            ContextAwareBlockingStrategy()
    
    def test_context_aware_blocking_strategy_abstract_methods(self):
        """Test that ContextAwareBlockingStrategy enforces implementation of abstract methods.
        
        This test verifies that a subclass of ContextAwareBlockingStrategy must implement
        all abstract methods to be instantiable.
        """
        # Create a partial implementation missing some methods
        class PartialContextAwareStrategy(ContextAwareBlockingStrategy):
            @property
            def name(self):
                return "partial_context"
                
            @property
            def priority(self):
                return 10
                
            def should_block(self, domain):
                return BlockingDecision(should_block=False)
        
        # Should still raise TypeError because should_block_with_context is not implemented
        with self.assertRaises(TypeError):
            PartialContextAwareStrategy()


if __name__ == "__main__":
    unittest.main()
