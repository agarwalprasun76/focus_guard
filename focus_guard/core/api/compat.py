"""
Compatibility layer for transitioning from core to core.

This module provides compatibility functions and classes to ease the transition
from the old core module to the new core module. It allows for gradual
migration by providing interfaces that match the old API but use the new
implementation under the hood.
"""

import logging
from typing import Optional, Dict, Any, Union
from enum import Enum, auto

# Define the legacy DomainCategory enum locally to avoid import issues
class DomainCategory(Enum):
    """Legacy domain category enum."""
    WORK = auto()
    SOCIAL = auto()
    ENTERTAINMENT = auto()
    SHOPPING = auto()
    NEWS = auto()
    EDUCATION = auto()
    FINANCE = auto()
    HEALTH = auto()
    TRAVEL = auto()
    TECHNOLOGY = auto()
    GAMING = auto()
    ADULT = auto()
    OTHER = auto()

from focus_guard.core.api import api
from focus_guard.core.domain.models import Category, Domain

# Set up logging
logger = logging.getLogger(__name__)


def map_category_to_legacy(category: Optional[Category]) -> Optional[DomainCategory]:
    """
    Map a core Category to a legacy DomainCategory.
    
    Args:
        category: The core Category to map.
        
    Returns:
        The equivalent legacy DomainCategory, or None if no mapping exists.
    """
    if category is None:
        return None
        
    # Map from new Category enum to old DomainCategory enum
    mapping = {
        Category.PRODUCTIVITY: DomainCategory.WORK,
        Category.SOCIAL_MEDIA: DomainCategory.SOCIAL,
        Category.ENTERTAINMENT: DomainCategory.ENTERTAINMENT,
        Category.SHOPPING: DomainCategory.SHOPPING,
        Category.NEWS: DomainCategory.NEWS,
        Category.EDUCATION: DomainCategory.EDUCATION,
        Category.FINANCE: DomainCategory.FINANCE,
        Category.TECHNOLOGY: DomainCategory.TECHNOLOGY,
        Category.GAMING: DomainCategory.GAMING,
        Category.ADULT: DomainCategory.ADULT,
        Category.UNKNOWN: DomainCategory.OTHER
    }
    
    return mapping.get(category)


def classify_domain(domain: str) -> Optional[DomainCategory]:
    """
    Classify a domain using the new core API but return a legacy DomainCategory.
    
    This function is a drop-in replacement for the legacy classify_domain function.
    
    Args:
        domain: The domain to classify.
        
    Returns:
        The domain category as a legacy DomainCategory enum value, or None if not classified.
    """
    logger.debug(f"compat.classify_domain called for domain: {domain}")
    
    # Use the new API to classify the domain
    category = api.classify_domain(domain)
    
    # Map the new Category to the legacy DomainCategory
    legacy_category = map_category_to_legacy(category)
    
    logger.debug(f"Domain {domain} classified as {category} (legacy: {legacy_category})")
    return legacy_category


def should_block_tab(url: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Determine if a tab should be blocked using the new core API.
    
    This function is a drop-in replacement for the legacy should_block_tab function.
    
    Args:
        url: The URL of the tab.
        metadata: Optional metadata about the tab.
        
    Returns:
        True if the tab should be blocked, False otherwise.
    """
    logger.debug(f"compat.should_block_tab called for URL: {url}")
    
    # Use the new API to determine if the tab should be blocked
    should_block = api.should_block_tab(url, metadata)
    
    logger.debug(f"Tab with URL {url} should be blocked: {should_block}")
    return should_block


def get_blocking_reason(url: str) -> Optional[str]:
    """
    Get the reason why a tab is blocked using the new core API.
    
    This function is a drop-in replacement for the legacy get_blocking_reason function.
    
    Args:
        url: The URL of the tab.
        
    Returns:
        The reason why the tab is blocked, or None if it is not blocked.
    """
    logger.debug(f"compat.get_blocking_reason called for URL: {url}")
    
    # Use the new API to get the blocking reason
    reason = api.get_blocking_reason(url)
    
    logger.debug(f"Blocking reason for URL {url}: {reason}")
    return reason


def reload_configuration() -> None:
    """
    Reload the configuration using the new core API.
    
    This function is a drop-in replacement for the legacy reload_configuration function.
    
    Returns:
        None
    """
    logger.debug("compat.reload_configuration called")
    
    # Use the new API to reload the configuration
    api.reload_configuration()
    
    logger.debug("Configuration reloaded")


# Create a compatibility class that mimics the legacy DomainClassifier
class DomainClassifierCompat:
    """
    Compatibility class that mimics the legacy DomainClassifier but uses the new core API.
    """
    
    def __init__(self):
        """Initialize the compatibility domain classifier."""
        logger.debug("DomainClassifierCompat initialized")
    
    def classify_domain(self, domain: str) -> Optional[DomainCategory]:
        """
        Classify a domain using the new core API but return a legacy DomainCategory.
        
        Args:
            domain: The domain to classify.
            
        Returns:
            The domain category as a legacy DomainCategory enum value, or None if not classified.
        """
        return classify_domain(domain)
    
    def reload_config(self) -> None:
        """
        Reload the configuration using the new core API.
        
        Returns:
            None
        """
        reload_configuration()


# Create a compatibility class that mimics the legacy BlockingManager
class BlockingManagerCompat:
    """
    Compatibility class that mimics the legacy BlockingManager but uses the new core API.
    """
    
    def __init__(self):
        """Initialize the compatibility blocking manager."""
        logger.debug("BlockingManagerCompat initialized")
    
    def should_block_tab(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if a tab should be blocked using the new core API.
        
        Args:
            url: The URL of the tab.
            metadata: Optional metadata about the tab.
            
        Returns:
            True if the tab should be blocked, False otherwise.
        """
        return should_block_tab(url, metadata)
    
    def get_blocking_reason(self, url: str) -> Optional[str]:
        """
        Get the reason why a tab is blocked using the new core API.
        
        Args:
            url: The URL of the tab.
            
        Returns:
            The reason why the tab is blocked, or None if it is not blocked.
        """
        return get_blocking_reason(url)
    
    def reload_config(self) -> None:
        """
        Reload the configuration using the new core API.
        
        Returns:
            None
        """
        reload_configuration()


# Create singleton instances for compatibility
domain_classifier_compat = DomainClassifierCompat()
blocking_manager_compat = BlockingManagerCompat()
