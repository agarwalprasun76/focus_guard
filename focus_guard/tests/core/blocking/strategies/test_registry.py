"""
Tests for the blocking strategy registry in core.

This module contains unit tests for the BlockingStrategyRegistry class, which is responsible
for managing the registration, retrieval, and prioritization of blocking strategies.

The tests verify that the registry correctly:
- Registers and retrieves strategies
- Maintains priority ordering
- Handles duplicate registrations
- Supports priority updates
- Properly unregisters strategies
"""

import unittest
from unittest.mock import MagicMock

from focus_guard.core.blocking.base import BlockingStrategy
from focus_guard.core.blocking.strategies.registry import BlockingStrategyRegistry


class MockBlockingStrategy(BlockingStrategy):
    """Mock blocking strategy for testing.
    
    This class implements the BlockingStrategy interface for testing purposes,
    providing the minimum required implementation to satisfy the abstract base class.
    """
    
    def __init__(self, name, priority_value=10):
        """Initialize the mock strategy.
        
        Args:
            name: The name of the strategy
            priority_value: The priority value to return from the priority property
        """
        self._name = name
        self._priority_value = priority_value
    
    @property
    def name(self) -> str:
        """Get the name of the strategy."""
        return self._name
    
    @property
    def priority(self) -> int:
        """Get the priority of the strategy."""
        return self._priority_value
    
    def should_block(self, domain):
        """Mock implementation of should_block."""
        pass
    
    def should_block_with_context(self, domain, context):
        """Mock implementation of should_block_with_context."""
        pass
    
    def reload(self):
        """Mock implementation of reload."""
        pass


class TestBlockingStrategyRegistry(unittest.TestCase):
    """Tests for the BlockingStrategyRegistry class.
    
    These tests verify that the BlockingStrategyRegistry correctly manages
    the registration, retrieval, and prioritization of blocking strategies.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Create the registry
        self.registry = BlockingStrategyRegistry()
    
    def test_register_and_get(self):
        """Test registering and getting a strategy."""
        # Create a strategy
        strategy = MockBlockingStrategy("test_strategy")
        
        # Register the strategy
        self.registry.register(strategy)
        
        # Get the strategy
        retrieved_strategy = self.registry.get("test_strategy")
        
        # Verify that the strategy was retrieved
        self.assertEqual(retrieved_strategy, strategy)
    
    def test_register_with_priority(self):
        """Test registering a strategy with a priority."""
        # Create strategies
        strategy1 = MockBlockingStrategy("strategy1")
        strategy2 = MockBlockingStrategy("strategy2")
        
        # Register the strategies with priorities
        self.registry.register(strategy1, priority=10)
        self.registry.register(strategy2, priority=20)
        
        # Get all strategies
        strategies = self.registry.get_all()
        
        # Verify that the strategies are returned in priority order (highest first)
        self.assertEqual(len(strategies), 2)
        self.assertEqual(strategies[0], strategy2)
        self.assertEqual(strategies[1], strategy1)
    
    def test_register_duplicate_name(self):
        """Test registering a strategy with a duplicate name."""
        # Create strategies with the same name
        strategy1 = MockBlockingStrategy("test_strategy")
        strategy2 = MockBlockingStrategy("test_strategy")
        
        # Register the first strategy
        self.registry.register(strategy1)
        
        # Register the second strategy
        self.registry.register(strategy2)
        
        # Get the strategy
        retrieved_strategy = self.registry.get("test_strategy")
        
        # Verify that the second strategy replaced the first
        self.assertEqual(retrieved_strategy, strategy2)
    
    def test_get_nonexistent_strategy(self):
        """Test getting a nonexistent strategy."""
        # Get a nonexistent strategy
        strategy = self.registry.get("nonexistent_strategy")
        
        # Verify that None is returned
        self.assertIsNone(strategy)
    
    def test_get_all_empty(self):
        """Test getting all strategies when the registry is empty."""
        # Get all strategies
        strategies = self.registry.get_all()
        
        # Verify that an empty list is returned
        self.assertEqual(len(strategies), 0)
    
    def test_get_all_sorted(self):
        """Test that get_all returns strategies sorted by priority."""
        # Create strategies
        strategy1 = MockBlockingStrategy("strategy1")
        strategy2 = MockBlockingStrategy("strategy2")
        strategy3 = MockBlockingStrategy("strategy3")
        
        # Register the strategies with priorities
        self.registry.register(strategy1, priority=10)
        self.registry.register(strategy2, priority=30)
        self.registry.register(strategy3, priority=20)
        
        # Get all strategies
        strategies = self.registry.get_all()
        
        # Verify that the strategies are returned in priority order (highest first)
        self.assertEqual(len(strategies), 3)
        self.assertEqual(strategies[0], strategy2)
        self.assertEqual(strategies[1], strategy3)
        self.assertEqual(strategies[2], strategy1)
    
    def test_set_priority(self):
        """Test setting the priority of a strategy."""
        # Create strategies
        strategy1 = MockBlockingStrategy("strategy1")
        strategy2 = MockBlockingStrategy("strategy2")
        
        # Register the strategies with priorities
        self.registry.register(strategy1, priority=10)
        self.registry.register(strategy2, priority=20)
        
        # Set the priority of the first strategy
        self.registry.set_priority("strategy1", 30)
        
        # Get all strategies
        strategies = self.registry.get_all()
        
        # Verify that the strategies are returned in the new priority order
        self.assertEqual(len(strategies), 2)
        self.assertEqual(strategies[0], strategy1)
        self.assertEqual(strategies[1], strategy2)
    
    def test_set_priority_nonexistent_strategy(self):
        """Test setting the priority of a nonexistent strategy."""
        # Set the priority of a nonexistent strategy
        result = self.registry.set_priority("nonexistent_strategy", 10)
        
        # Verify that False is returned
        self.assertFalse(result)
    
    def test_unregister(self):
        """Test unregistering a strategy."""
        # Create a strategy
        strategy = MockBlockingStrategy("test_strategy")
        
        # Register the strategy
        self.registry.register(strategy)
        
        # Unregister the strategy
        result = self.registry.unregister("test_strategy")
        
        # Verify that True is returned
        self.assertTrue(result)
        
        # Get the strategy
        retrieved_strategy = self.registry.get("test_strategy")
        
        # Verify that None is returned
        self.assertIsNone(retrieved_strategy)
    
    def test_unregister_nonexistent_strategy(self):
        """Test unregistering a nonexistent strategy."""
        # Unregister a nonexistent strategy
        result = self.registry.unregister("nonexistent_strategy")
        
        # Verify that False is returned
        self.assertFalse(result)


    def test_get_priority(self):
        """Test getting the priority of a strategy.
        
        This test verifies that get_priority correctly returns the priority
        of a registered strategy.
        """
        # Create a strategy
        strategy = MockBlockingStrategy("test_strategy")
        
        # Register the strategy with a priority
        self.registry.register(strategy, priority=42)
        
        # Get the priority
        priority = self.registry.get_priority("test_strategy")
        
        # Verify that the correct priority is returned
        self.assertEqual(priority, 42)
    
    def test_get_priority_nonexistent_strategy(self):
        """Test getting the priority of a nonexistent strategy.
        
        This test verifies that get_priority returns None when asked for
        the priority of a strategy that isn't registered.
        """
        # Get the priority of a nonexistent strategy
        priority = self.registry.get_priority("nonexistent_strategy")
        
        # Verify that None is returned
        self.assertIsNone(priority)
    
    def test_clear(self):
        """Test clearing the registry.
        
        This test verifies that the clear method removes all registered strategies.
        """
        # Create and register some strategies
        strategy1 = MockBlockingStrategy("strategy1")
        strategy2 = MockBlockingStrategy("strategy2")
        self.registry.register(strategy1)
        self.registry.register(strategy2)
        
        # Verify that the strategies are registered
        self.assertEqual(len(self.registry.get_all()), 2)
        
        # Clear the registry
        self.registry.clear()
        
        # Verify that the registry is empty
        self.assertEqual(len(self.registry.get_all()), 0)
        self.assertIsNone(self.registry.get("strategy1"))
        self.assertIsNone(self.registry.get("strategy2"))


if __name__ == "__main__":
    unittest.main()
