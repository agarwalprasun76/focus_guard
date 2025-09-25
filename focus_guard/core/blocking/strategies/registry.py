"""
Blocking Strategy Registry.

This module provides a registry for managing and prioritizing blocking strategies.
"""

import logging
from typing import Dict, List, Optional, Type

from focus_guard.core.blocking.base import BlockingStrategy


class BlockingStrategyRegistry:
    """
    Registry for blocking strategies.
    
    This class manages the registration, retrieval, and prioritization of
    blocking strategies.
    """
    
    def __init__(self):
        """Initialize the blocking strategy registry."""
        self._strategies: Dict[str, BlockingStrategy] = {}
        self._priorities: Dict[str, int] = {}
        self._logger = logging.getLogger("core.blocking.strategies.registry")
        self._logger.info("Blocking strategy registry initialized")
    
    def register(self, strategy: BlockingStrategy, priority: int = 0) -> None:
        """
        Register a blocking strategy with the registry.
        
        Args:
            strategy: The blocking strategy to register.
            priority: The priority of the strategy (higher = checked first).
        """
        strategy_name = strategy.name
        self._strategies[strategy_name] = strategy
        self._priorities[strategy_name] = priority
        self._logger.info(f"Registered blocking strategy '{strategy_name}' with priority {priority}")
    
    def unregister(self, strategy_name: str) -> bool:
        """
        Unregister a blocking strategy from the registry.
        
        Args:
            strategy_name: The name of the strategy to unregister.
            
        Returns:
            True if the strategy was unregistered, False if it wasn't registered.
        """
        if strategy_name in self._strategies:
            del self._strategies[strategy_name]
            del self._priorities[strategy_name]
            self._logger.info(f"Unregistered blocking strategy '{strategy_name}'")
            return True
        return False
    
    def get(self, strategy_name: str) -> Optional[BlockingStrategy]:
        """
        Get a blocking strategy by name.
        
        Args:
            strategy_name: The name of the strategy to get.
            
        Returns:
            The blocking strategy, or None if not found.
        """
        return self._strategies.get(strategy_name)
    
    def get_all(self) -> List[BlockingStrategy]:
        """
        Get all registered blocking strategies, sorted by priority.
        
        Returns:
            A list of blocking strategies, sorted by priority (highest first).
        """
        return [
            self._strategies[name]
            for name, _ in sorted(
                self._priorities.items(),
                key=lambda item: item[1],
                reverse=True
            )
        ]
    
    def set_priority(self, strategy_name: str, priority: int) -> bool:
        """
        Set the priority of a blocking strategy.
        
        Args:
            strategy_name: The name of the strategy.
            priority: The new priority.
            
        Returns:
            True if the priority was set, False if the strategy wasn't found.
        """
        if strategy_name in self._priorities:
            self._priorities[strategy_name] = priority
            self._logger.info(f"Set priority of blocking strategy '{strategy_name}' to {priority}")
            return True
        return False
    
    def get_priority(self, strategy_name: str) -> Optional[int]:
        """
        Get the priority of a blocking strategy.
        
        Args:
            strategy_name: The name of the strategy.
            
        Returns:
            The priority, or None if the strategy wasn't found.
        """
        return self._priorities.get(strategy_name)
    
    def clear(self) -> None:
        """Clear all registered blocking strategies."""
        self._strategies.clear()
        self._priorities.clear()
        self._logger.info("Cleared all blocking strategies")
