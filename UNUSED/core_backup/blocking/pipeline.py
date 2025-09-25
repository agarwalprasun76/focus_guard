"""
Blocking Pipeline.

This module provides a pipeline for applying multiple blocking strategies
to determine if a domain should be blocked.
"""

import logging
from typing import Dict, Any, List, Optional

from core_v2.blocking.base import BlockingStrategy, BlockingDecision
from core_v2.domain.models import Domain
from core_v2.blocking.strategies.registry import BlockingStrategyRegistry


class BlockingPipeline:
    """
    Pipeline for applying multiple blocking strategies.
    
    This class manages the application of multiple blocking strategies to
    determine if a domain should be blocked.
    """
    
    def __init__(self, registry: BlockingStrategyRegistry):
        """
        Initialize the blocking pipeline.
        
        Args:
            registry: The registry of blocking strategies.
        """
        self._registry = registry
        self._logger = logging.getLogger("core_v2.blocking.pipeline")
        self._logger.info("Blocking pipeline initialized")
    
    def should_block(self, domain: Domain) -> BlockingDecision:
        """
        Determine if a domain should be blocked.
        
        This method applies all registered blocking strategies in order of
        priority until a decision to block is made.
        
        Args:
            domain: The domain to check.
            
        Returns:
            A BlockingDecision indicating whether the domain should be blocked.
        """
        strategies = self._registry.get_all()
        
        # If no strategies are registered, don't block
        if not strategies:
            self._logger.warning("No blocking strategies registered")
            return BlockingDecision(should_block=False, reason=None)
        
        # Apply each strategy in order of priority
        for strategy in strategies:
            decision = strategy.should_block(domain)
            
            # If the strategy decides to block, return the decision
            if decision.should_block:
                self._logger.info(
                    f"Strategy '{strategy.name}' decided to block domain '{domain.value}': {decision.reason}"
                )
                return decision
        
        # If no strategy decided to block, don't block
        return BlockingDecision(should_block=False, reason=None)
    
    def should_block_with_context(self, domain: Domain, context: Dict[str, Any]) -> BlockingDecision:
        """
        Determine if a domain should be blocked using additional context.
        
        This method applies all registered blocking strategies in order of
        priority until a decision to block is made, providing additional
        context to each strategy.
        
        Args:
            domain: The domain to check.
            context: Additional context for making the blocking decision.
            
        Returns:
            A BlockingDecision indicating whether the domain should be blocked.
        """
        strategies = self._registry.get_all()
        
        # If no strategies are registered, don't block
        if not strategies:
            self._logger.warning("No blocking strategies registered")
            return BlockingDecision(should_block=False, reason=None)
        
        # Apply each strategy in order of priority
        for strategy in strategies:
            decision = strategy.should_block_with_context(domain, context)
            
            # If the strategy decides to block, return the decision
            if decision.should_block:
                self._logger.info(
                    f"Strategy '{strategy.name}' decided to block domain '{domain.value}' with context: {decision.reason}"
                )
                return decision
        
        # If no strategy decided to block, don't block
        return BlockingDecision(should_block=False, reason=None)
    
    def reload_all_strategies(self) -> None:
        """Reload all registered blocking strategies."""
        strategies = self._registry.get_all()
        for strategy in strategies:
            try:
                strategy.reload()
            except Exception as e:
                self._logger.error(f"Error reloading strategy '{strategy.name}': {e}")
        
        self._logger.info(f"Reloaded {len(strategies)} blocking strategies")
