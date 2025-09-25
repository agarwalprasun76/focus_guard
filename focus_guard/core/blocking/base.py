"""
Base interfaces for domain blocking.

This module defines the core interfaces for blocking strategies and related components.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Set

from focus_guard.core.domain.models import Domain, URL, Category


class BlockingReason(Enum):
    """
    Reasons why a domain might be blocked.
    """
    
    CATEGORY = auto()  # Blocked due to its category
    DOMAIN_EXCLUDED = auto()  # Blocked by domain excluder (e.g., StevenBlack hosts)
    USER_BLOCKED = auto()  # Explicitly blocked by user
    CONTENT_POLICY = auto()  # Blocked due to content policy
    YOUTUBE_CONTENT = auto()  # Blocked due to YouTube content classification
    OTHER = auto()  # Other reason


class BlockingDecision:
    """
    Represents a decision to block or allow a domain.
    """
    
    def __init__(
        self,
        should_block: bool,
        reason: Optional[BlockingReason] = None,
        details: Optional[str] = None
    ):
        """
        Initialize a blocking decision.
        
        Args:
            should_block: Whether the domain should be blocked.
            reason: The reason for blocking, if applicable.
            details: Additional details about the blocking decision.
        """
        self.should_block = should_block
        self.reason = reason
        self.details = details


class BlockingStrategy(ABC):
    """
    Base interface for domain blocking strategies.
    
    A blocking strategy is responsible for determining if a domain should be blocked
    based on specific criteria.
    """
    
    @abstractmethod
    def should_block(self, domain: Domain) -> BlockingDecision:
        """
        Determine if a domain should be blocked.
        
        Args:
            domain: The domain to check.
            
        Returns:
            A BlockingDecision indicating whether the domain should be blocked.
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of the blocking strategy.
        
        Returns:
            The strategy name.
        """
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """
        Get the priority of the blocking strategy.
        
        Higher priority strategies are executed first in the pipeline.
        
        Returns:
            The strategy priority.
        """
        pass


class ContextAwareBlockingStrategy(BlockingStrategy):
    """
    Interface for blocking strategies that use context beyond just the domain.
    
    Some blocking strategies may need additional context, such as URL path,
    query parameters, or metadata about the content, to make accurate blocking decisions.
    """
    
    @abstractmethod
    def should_block_with_context(
        self, domain: Domain, context: Dict[str, Any]
    ) -> BlockingDecision:
        """
        Determine if a domain should be blocked using additional context.
        
        Args:
            domain: The domain to check.
            context: Additional context to aid the decision.
            
        Returns:
            A BlockingDecision indicating whether the domain should be blocked.
        """
        pass


class BlockingStrategyRegistry:
    """
    Registry for blocking strategies.
    
    This class manages a collection of blocking strategies and provides methods to
    register, unregister, and retrieve them.
    """
    
    def __init__(self):
        """Initialize an empty blocking strategy registry."""
        self._strategies: Dict[str, BlockingStrategy] = {}
    
    def register(self, strategy: BlockingStrategy) -> None:
        """
        Register a blocking strategy.
        
        Args:
            strategy: The strategy to register.
        """
        self._strategies[strategy.name] = strategy
    
    def unregister(self, name: str) -> None:
        """
        Unregister a blocking strategy.
        
        Args:
            name: The name of the strategy to unregister.
        """
        if name in self._strategies:
            del self._strategies[name]
    
    def get(self, name: str) -> Optional[BlockingStrategy]:
        """
        Get a blocking strategy by name.
        
        Args:
            name: The name of the strategy to retrieve.
            
        Returns:
            The strategy, or None if not found.
        """
        return self._strategies.get(name)
    
    def get_all(self) -> List[BlockingStrategy]:
        """
        Get all registered blocking strategies.
        
        Returns:
            A list of all registered blocking strategies.
        """
        return list(self._strategies.values())


class BlockingPipeline:
    """
    Pipeline for executing multiple blocking strategies in sequence.
    
    This class manages the execution of multiple blocking strategies and combines
    their results according to a defined strategy.
    """
    
    def __init__(self, registry: BlockingStrategyRegistry):
        """
        Initialize a blocking pipeline.
        
        Args:
            registry: The blocking strategy registry to use.
        """
        self._registry = registry
    
    def should_block(
        self, domain: Domain, context: Optional[Dict[str, Any]] = None
    ) -> BlockingDecision:
        """
        Determine if a domain should be blocked using the pipeline.
        
        This method executes each strategy in order of priority,
        returning the first decision to block.
        
        Args:
            domain: The domain to check.
            context: Optional context for context-aware strategies.
            
        Returns:
            A BlockingDecision indicating whether the domain should be blocked.
        """
        # Get all strategies sorted by priority (highest first)
        strategies = sorted(
            self._registry.get_all(),
            key=lambda s: s.priority,
            reverse=True
        )
        
        for strategy in strategies:
            if context is not None and isinstance(strategy, ContextAwareBlockingStrategy):
                decision = strategy.should_block_with_context(domain, context)
            else:
                decision = strategy.should_block(domain)
            
            if decision.should_block:
                return decision
        
        # If no strategy decided to block, allow by default
        return BlockingDecision(should_block=False)
