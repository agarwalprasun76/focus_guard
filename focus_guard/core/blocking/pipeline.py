"""
Blocking Pipeline.

This module provides a pipeline for applying multiple blocking strategies
to determine if a domain should be blocked.
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple, Union

from focus_guard.core.blocking.base import BlockingStrategy, BlockingDecision
from focus_guard.core.domain.models import Domain, Category
from focus_guard.core.blocking.strategies.registry import BlockingStrategyRegistry


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
        self._logger = logging.getLogger("core.blocking.pipeline")
        self._logger.info("Blocking pipeline initialized")
    
    async def should_block(self, domain: Domain) -> BlockingDecision:
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
            return BlockingDecision(should_block=False, reason=None, details=None)
        
        # Apply each strategy in order of priority
        for strategy in strategies:
            try:
                decision = await strategy.should_block(domain)
                
                # Log the decision
                action = "block" if decision.should_block else "allow"
                self._logger.info(
                    f"Strategy '{strategy.name}' decided to {action} domain '{domain.value}': {decision.reason or 'No reason provided'}"
                )
                
                # If the strategy decides to block, return the decision
                if decision.should_block:
                    return decision
            except Exception as e:
                self._logger.error(
                    f"Error in strategy '{strategy.name}' while processing domain '{domain.value}': {str(e)}",
                    exc_info=True
                )
                # Continue to next strategy if one fails
                continue
        
# If no strategy decided to block, don't block
        return BlockingDecision(should_block=False, reason=None, details=None)
    
    async def should_block_with_context(self, domain: Domain, context: Dict[str, Any]) -> BlockingDecision:
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
            return BlockingDecision(should_block=False, reason=None, details=None)
        
        # Apply each strategy in order of priority
        for strategy in strategies:
            try:
                if hasattr(strategy, 'should_block_with_context'):
                    decision = await strategy.should_block_with_context(domain, context)
                else:
                    decision = await strategy.should_block(domain)
                
                # If the strategy decides to block, return the decision
                if decision.should_block:
                    self._logger.info(
                        f"Strategy '{strategy.name}' decided to block domain '{domain.value}' with context: {decision.reason}"
                    )
                    return decision
            except Exception as e:
                self._logger.error(
                    f"Error in strategy '{strategy.name}' while processing domain '{domain.value}' with context: {str(e)}",
                    exc_info=True
                )
                # Continue to next strategy if one fails
                continue
        
# If no strategy decided to block, don't block
        return BlockingDecision(should_block=False, reason=None, details=None)
    
    def reload_all_strategies(self) -> None:
        """
        Reload all registered blocking strategies.
        
        This method calls the reload() method on all registered blocking
        strategies, allowing them to refresh their configuration.
        """
        strategies = self._registry.get_all()
        
        for strategy in strategies:
            try:
                strategy.reload()
                self._logger.info(f"Reloaded strategy: {strategy.name}")
            except Exception as e:
                self._logger.error(
                    f"Failed to reload strategy '{strategy.name}': {str(e)}",
                    exc_info=True
                )
        
        self._logger.info(f"Reloaded {len(strategies)} blocking strategies")
