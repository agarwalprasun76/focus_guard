"""
Category Blocker Strategy.

This module provides a blocking strategy that blocks domains based on their
category and user-configured blocking rules.
"""

import logging
from typing import Dict, Any, Set, Optional

from focus_guard.core.blocking.base import BlockingStrategy, BlockingDecision
from focus_guard.core.domain.models import Domain, Category
from focus_guard.core.config.loader import ConfigurationLoader
from focus_guard.core.domain.constants import CATEGORY_TO_ENUM_MAPPING


class CategoryBlockerStrategy(BlockingStrategy):
    """
    Blocking strategy that blocks domains based on their category.
    
    This strategy uses the domain category and user-configured blocking rules
    to determine if a domain should be blocked.
    """
    
    def __init__(self, config_loader: ConfigurationLoader):
        """
        Initialize the category blocker strategy.
        
        Args:
            config_loader: The configuration loader to access blocking rules.
        """
        self._config_loader = config_loader
        self._logger = logging.getLogger("core.blocking.strategies.category_blocker")
        self._logger.info("Category blocker strategy initialized")
    
    @property
    def name(self) -> str:
        """
        Get the name of the blocking strategy.
        
        Returns:
            The strategy name.
        """
        return "category_blocker"
    
    @property
    def priority(self) -> int:
        """
        Get the priority of the blocking strategy.
        
        Category blocker has medium priority (50) to ensure it runs after
        domain excluder but before other more specific strategies.
        
        Returns:
            The strategy priority.
        """
        return 50
    
    def should_block(self, domain: Domain) -> BlockingDecision:
        """
        Determine if a domain should be blocked based on its category.
        
        This method requires the domain to have a category assigned.
        If no category is assigned, it will return a decision not to block.
        
        Args:
            domain: The domain to check.
            
        Returns:
            A BlockingDecision indicating whether the domain should be blocked.
        """
        # Get the current blocking configuration
        blocking_config = self._config_loader.get_blocking_config()
        
        # If no blocking config is available, don't block
        if not blocking_config:
            return BlockingDecision(should_block=False, reason=None)
        
        # Check if domain is in the whitelist
        if domain.value in blocking_config.whitelist:
            return BlockingDecision(
                should_block=False,
                reason=f"Domain {domain.value} is in the whitelist"
            )
        
        # Check if the domain has a category
        if not domain.category:
            self._logger.debug(f"Domain {domain.value} has no category assigned")
            return BlockingDecision(should_block=False, reason=None)
        
        # Check if the category is blocked
        # First check if blocked_categories contains Category enums
        if domain.category in blocking_config.blocked_categories:
            return BlockingDecision(
                should_block=True,
                reason=f"Category {domain.category.name} is blocked"
            )
            
        # If not found, try string comparison as fallback
        category_str = None
        for config_cat, enum_cat in CATEGORY_TO_ENUM_MAPPING.items():
            if domain.category == Category[enum_cat]:
                category_str = config_cat
                break
                
        if category_str and category_str in blocking_config.blocked_categories:
            return BlockingDecision(
                should_block=True,
                reason=f"Category {domain.category.name} is blocked"
            )
        
        return BlockingDecision(should_block=False, reason=None)
    
    def should_block_with_context(self, domain: Domain, context: Dict[str, Any]) -> BlockingDecision:
        """
        Determine if a domain should be blocked using additional context.
        
        This method considers the current focus mode, time-based rules,
        and other contextual information when making a blocking decision.
        
        Args:
            domain: The domain to check.
            context: Additional context for making the blocking decision.
            
        Returns:
            A BlockingDecision indicating whether the domain should be blocked.
        """
        # Get the current blocking configuration
        blocking_config = self._config_loader.get_blocking_config()
        
        # If no blocking config is available, don't block
        if not blocking_config:
            return BlockingDecision(should_block=False, reason=None)
        
        # Check if domain is in the whitelist
        if domain.value in blocking_config.whitelist:
            return BlockingDecision(
                should_block=False,
                reason=f"Domain {domain.value} is in the whitelist"
            )
        
        # Check if the domain has a category
        if not domain.category:
            self._logger.debug(f"Domain {domain.value} has no category assigned")
            return BlockingDecision(should_block=False, reason=None)
        
        # Check focus mode from context
        focus_mode = context.get("focus_mode")
        if focus_mode and hasattr(blocking_config, 'focus_mode_categories'):
            # Get categories blocked in the current focus mode
            blocked_categories = blocking_config.focus_mode_categories.get(focus_mode, set())
            
            # Check if blocked_categories contains Category enums
            if domain.category in blocked_categories:
                return BlockingDecision(
                    should_block=True,
                    reason=f"Category {domain.category.name} is blocked in focus mode {focus_mode}"
                )
                
            # Fall back to string comparison if needed
            category_str = None
            for config_cat, enum_cat in CATEGORY_TO_ENUM_MAPPING.items():
                if domain.category == Category[enum_cat]:
                    category_str = config_cat
                    break
                    
            if category_str and category_str in blocked_categories:
                return BlockingDecision(
                    should_block=True,
                    reason=f"Category {domain.category.name} is blocked in focus mode {focus_mode}"
                )
        
        # Check time-based rules
        current_time = context.get("current_time")
        if current_time and hasattr(blocking_config, 'time_based_rules') and blocking_config.time_based_rules:
            for rule in blocking_config.time_based_rules:
                # First check if blocked_categories contains Category enums
                if (rule.start_time <= current_time <= rule.end_time and 
                    domain.category in rule.blocked_categories):
                    return BlockingDecision(
                        should_block=True,
                        reason=f"Category {domain.category.name} is blocked during scheduled time"
                    )
                
                # Fall back to string comparison if needed
                category_str = None
                for config_cat, enum_cat in CATEGORY_TO_ENUM_MAPPING.items():
                    if domain.category == Category[enum_cat]:
                        category_str = config_cat
                        break
                        
                if (rule.start_time <= current_time <= rule.end_time and 
                    category_str and category_str in rule.blocked_categories):
                    return BlockingDecision(
                        should_block=True,
                        reason=f"Category {domain.category.name} is blocked during scheduled time"
                    )
        
        # Fall back to standard category blocking
        return self.should_block(domain)
    
    def reload(self) -> None:
        """Reload the blocking configuration."""
        self._logger.info("Reloading category blocker configuration")
        # Configuration is loaded dynamically from the config_loader, no need to do anything here
