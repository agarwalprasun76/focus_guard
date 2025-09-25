"""
Core V2 API for domain classification and blocking.

This module provides the main entry point for the domain classification
and blocking system, integrating all components into a cohesive API.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple

from core_v2.domain.models import Domain, Category, URL
from core_v2.classification.base import ClassifierRegistry
from core_v2.classification.domain_classifier import StandardDomainClassifier
from core_v2.classification.classifiers.youtube import YouTubeClassifierAdapter
from core_v2.classification.classifiers.registry import ClassifierRegistry
from core_v2.blocking.base import BlockingDecision
from core_v2.blocking.pipeline import BlockingPipeline
from core_v2.blocking.strategies.registry import BlockingStrategyRegistry
from core_v2.blocking.strategies.domain_excluder import DomainExcluderStrategy
from core_v2.blocking.strategies.category_blocker import CategoryBlockerStrategy
from core_v2.config.loader import ConfigurationLoader
from core_v2.cache.memory_cache import MemoryCache
from core_v2.utils.domain_utils import extract_domain_from_url


class ClassifierBlockerAPI:
    """
    Main API for domain classification and blocking.
    
    This class serves as the primary interface for the domain classification
    and blocking system, integrating classifiers, blocking strategies, and
    configuration into a unified API.
    """
    
    def __init__(self):
        """Initialize the ClassifierBlockerAPI."""
        # Set up logging
        self._logger = logging.getLogger("core_v2.api")
        
        # Initialize configuration loader
        self._config_loader = ConfigurationLoader()
        
        # Initialize caches
        self._domain_cache = MemoryCache[Category](3600)  # 1 hour TTL
        self._blocking_cache = MemoryCache[Tuple[bool, str]](300)  # 5 minutes TTL
        
        # Initialize classifier registry and register classifiers
        self._classifier_registry = ClassifierRegistry()
        self._setup_classifiers()
        
        # Initialize blocking strategy registry and register strategies
        self._blocking_registry = BlockingStrategyRegistry()
        self._setup_blocking_strategies()
        
        # Initialize blocking pipeline
        self._blocking_pipeline = BlockingPipeline(self._blocking_registry)
        
        self._logger.info("ClassifierBlockerAPI initialized")
    
    def _setup_classifiers(self) -> None:
        """Set up and register classifiers."""
        # Create and register the standard domain classifier (highest priority)
        standard_classifier = StandardDomainClassifier(self._config_loader)
        self._classifier_registry.register(standard_classifier, priority=100)
        
        # Create and register the YouTube classifier adapter
        youtube_classifier = YouTubeClassifierAdapter()
        self._classifier_registry.register(youtube_classifier, priority=90)
        
        self._logger.info(f"Registered {len(self._classifier_registry.get_all())} classifiers")
    
    def _setup_blocking_strategies(self) -> None:
        """Set up and register blocking strategies."""
        # Create and register the domain excluder strategy (highest priority)
        domain_excluder = DomainExcluderStrategy()
        self._blocking_registry.register(domain_excluder, priority=100)
        
        # Create and register the category blocker strategy
        category_blocker = CategoryBlockerStrategy(self._config_loader)
        self._blocking_registry.register(category_blocker, priority=90)
        
        self._logger.info(f"Registered {len(self._blocking_registry.get_all())} blocking strategies")
    
    def classify_domain(self, domain_str: str) -> Optional[Category]:
        """
        Classify a domain into a category.
        
        Args:
            domain_str: The domain string to classify.
            
        Returns:
            The category of the domain, or None if it couldn't be classified.
        """
        try:
            # Check cache first
            cached_category = self._domain_cache.get(domain_str)
            if cached_category is not None:
                self._logger.debug(f"Cache hit for domain {domain_str}: {cached_category}")
                return cached_category
            
            # Create domain object
            domain = Domain(domain_str)
            
            # Get all classifiers in priority order
            classifiers = self._classifier_registry.get_all()
            
            # Try each classifier until one returns a category
            for classifier in classifiers:
                category = classifier.classify(domain)
                if category is not None:
                    self._logger.info(
                        f"Classifier '{classifier.name}' classified domain '{domain_str}' as {category.name}"
                    )
                    # Cache the result
                    self._domain_cache.set(domain_str, category)
                    return category
            
            self._logger.info(f"Domain '{domain_str}' could not be classified")
            # Cache the None result to avoid repeated classification attempts
            self._domain_cache.set(domain_str, None)
            return None
            
        except Exception as e:
            self._logger.error(f"Error classifying domain '{domain_str}': {e}")
            return None
    
    def classify_domain_with_context(self, domain_str: str, context: Dict[str, Any]) -> Optional[Category]:
        """
        Classify a domain using additional context.
        
        Args:
            domain_str: The domain string to classify.
            context: Additional context to aid classification.
            
        Returns:
            The category of the domain, or None if it couldn't be classified.
        """
        try:
            # Create domain object
            domain = Domain(domain_str)
            
            # Get all classifiers in priority order
            classifiers = self._classifier_registry.get_all()
            
            # Try each classifier until one returns a category
            for classifier in classifiers:
                if hasattr(classifier, 'classify_with_context'):
                    category = classifier.classify_with_context(domain, context)
                    if category is not None:
                        self._logger.info(
                            f"Classifier '{classifier.name}' classified domain '{domain_str}' as {category.name} with context"
                        )
                        return category
            
            # Fall back to standard classification if context-aware classification failed
            return self.classify_domain(domain_str)
            
        except Exception as e:
            self._logger.error(f"Error classifying domain '{domain_str}' with context: {e}")
            return None
    
    def should_block_tab(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if a tab with the given URL should be blocked.
        
        Args:
            url: The URL to check.
            metadata: Optional metadata about the tab.
            
        Returns:
            True if the tab should be blocked, False otherwise.
        """
        try:
            # Check cache first
            cache_key = f"{url}:{hash(str(metadata))}"
            cached_result = self._blocking_cache.get(cache_key)
            if cached_result is not None:
                should_block, _ = cached_result
                return should_block
            
            # Extract domain from URL
            domain_str = extract_domain_from_url(url)
            if not domain_str:
                self._logger.warning(f"Could not extract domain from URL: {url}")
                return False
            
            # Create domain object
            domain = Domain(domain_str)
            
            # Classify the domain
            context = {"url": url, "metadata": metadata or {}}
            category = self.classify_domain_with_context(domain_str, context)
            if category:
                domain.category = category
            
            # Check if the domain should be blocked
            decision = self._blocking_pipeline.should_block_with_context(domain, context)
            
            # Cache the result
            self._blocking_cache.set(cache_key, (decision.should_block, decision.reason or ""))
            
            return decision.should_block
            
        except Exception as e:
            self._logger.error(f"Error checking if tab should be blocked for URL '{url}': {e}")
            return False
    
    def get_blocking_reason(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Get the reason why a URL is blocked.
        
        Args:
            url: The URL to check.
            metadata: Optional metadata about the tab, important for context-aware classification.
            
        Returns:
            The reason for blocking, or None if the URL is not blocked.
        """
        try:
            # Check cache first
            cache_key = f"{url}:{hash(str(metadata))}"
            cached_result = self._blocking_cache.get(cache_key)
            if cached_result is not None:
                should_block, reason = cached_result
                return reason if should_block else None
            
            # Extract domain from URL
            domain_str = extract_domain_from_url(url)
            if not domain_str:
                self._logger.warning(f"Could not extract domain from URL: {url}")
                return None
            
            # Create domain object
            domain = Domain(domain_str)
            
            # Classify the domain with context if metadata is provided
            context = {"url": url, "metadata": metadata or {}}
            if metadata:
                category = self.classify_domain_with_context(domain_str, context)
            else:
                category = self.classify_domain(domain_str)
                
            if category:
                domain.category = category
            
            # Check if the domain should be blocked, using context if available
            if metadata:
                decision = self._blocking_pipeline.should_block_with_context(domain, context)
            else:
                decision = self._blocking_pipeline.should_block(domain)
            
            # Cache the result
            self._blocking_cache.set(cache_key, (decision.should_block, decision.reason or ""))
            
            return decision.reason if decision.should_block else None
            
        except Exception as e:
            self._logger.error(f"Error getting blocking reason for URL '{url}': {e}")
            return None
    
    def reload_configuration(self) -> None:
        """
        Reload the configuration from disk.
        
        This method is used to refresh the configuration when it changes,
        without requiring a restart of the application.
        """
        try:
            # Reload configuration
            self._logger.debug("Starting configuration reload")
            self._config_loader.reload()
            self._logger.debug("Configuration loader reloaded")
            
            # Clear caches
            self._logger.debug("Clearing caches")
            self._domain_cache.clear()
            self._blocking_cache.clear()
            
            # Re-initialize classifier registry with fresh classifiers
            # This ensures domain classifiers pick up the new configuration
            self._logger.debug("Re-initializing classifier registry")
            self._classifier_registry = ClassifierRegistry()
            self._setup_classifiers()
            
            # Reload blocking strategies
            self._logger.debug("Reloading blocking strategies")
            self._blocking_pipeline.reload_all_strategies()
            
            # Verify domain classification after reload
            domain = "facebook.com"
            category = self.classify_domain(domain)
            self._logger.debug(f"After reload, domain {domain} is classified as {category}")
            
            self._logger.info("Configuration reloaded")
            
        except Exception as e:
            self._logger.error(f"Error reloading configuration: {e}")
            import traceback
            self._logger.error(traceback.format_exc())


# Create a singleton instance for easy access
api = ClassifierBlockerAPI()
