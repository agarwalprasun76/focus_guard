"""
Core V2 API for domain classification and blocking.

This module provides the main entry point for the domain classification
and blocking system, integrating all components into a cohesive API.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple, NamedTuple

from focus_guard.core.domain.models import Domain, Category
from focus_guard.core.classification.base import ClassifierRegistry
from focus_guard.core.blocking.base import BlockingDecision
from focus_guard.core.blocking.pipeline import BlockingPipeline
from focus_guard.core.blocking.strategies.registry import BlockingStrategyRegistry
from focus_guard.core.blocking.strategies.domain_excluder import DomainExcluderStrategy
from focus_guard.core.blocking.strategies.category_blocker import CategoryBlockerStrategy
from focus_guard.core.config.loader import ConfigurationLoader
from focus_guard.core.cache.memory_cache import MemoryCache
from focus_guard.core.domain.domain_utils_new import extract_domain_from_url


class ClassificationResult(NamedTuple):
    """Result of domain classification including which classifier was used."""
    category: Optional[Category]
    classifier_name: Optional[str]
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class BlockingResult(NamedTuple):
    """Result of blocking decision including reason and classification details."""
    should_block: bool
    reason: Optional[str]
    category: Optional[Category] = None
    classifier_name: Optional[str] = None


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
        self._logger = logging.getLogger("core.api")
        
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
        # Create and register the YouTube classifier FIRST (highest priority for youtube.com)
        from focus_guard.core.classification.classifiers.domains.youtube_base import YouTubeClassifier
        
        # Use the create_default method which automatically detects and uses LLM if API key is available
        try:
            youtube_classifier = YouTubeClassifier.create_default()
            self._logger.info("YouTube classifier created with auto-detection of LLM capabilities")
            
            # Log which classifiers are actually loaded
            if hasattr(youtube_classifier, 'classifiers'):
                classifier_names = [getattr(c, 'name', c.__class__.__name__) for c in youtube_classifier.classifiers]
                self._logger.info(f"YouTube classifier loaded with: {classifier_names}")
        except Exception as e:
            self._logger.warning(f"Failed to create YouTube classifier: {e}")
            # Fallback to rule-based only
            from focus_guard.core.classification.classifiers.domains.youtube_rules import RuleBasedYouTubeClassifier
            youtube_classifier = RuleBasedYouTubeClassifier()
            self._logger.info("YouTube classifier created with rule-based classification only")
        
        self._classifier_registry.register(youtube_classifier)
        
        # Create and register the domain category classifier (lower priority)
        from focus_guard.core.classification.classifiers.domain_category_classifier import create_domain_category_classifier
        domain_classifier = create_domain_category_classifier()
        self._classifier_registry.register(domain_classifier)
        
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
    
    async def classify_domain_detailed(self, domain_str: str, url: Optional[str] = None) -> ClassificationResult:
        """
        Classify a domain into a category with detailed information about which classifier was used.
        
        Args:
            domain_str: The domain string to classify
            url: Optional full URL for context-aware classification
            
        Returns:
            ClassificationResult: Detailed classification result including classifier name
        """
        try:
            # Create domain object
            try:
                domain = Domain(domain_str)
                
                # Create context for classification
                context = {}
                if url:
                    context['url'] = url
                    
                    # For YouTube URLs, extract metadata and additional context
                    if 'youtube.com' in domain_str or 'youtu.be' in domain_str:
                        from focus_guard.core.utils.youtube_utils import is_youtube_url, extract_youtube_id
                        from focus_guard.core.utils.metadata_fetcher import metadata_fetcher
                        
                        if is_youtube_url(url):
                            video_id = extract_youtube_id(url)
                            if video_id:
                                context['video_id'] = video_id
                                
                                # Determine content type from URL structure
                                if '/shorts/' in url:
                                    context['content_type'] = 'shorts'
                                elif '/watch' in url:
                                    context['content_type'] = 'video'
                                elif '/playlist' in url:
                                    context['content_type'] = 'playlist'
                                
                                # Fetch YouTube metadata
                                try:
                                    youtube_metadata = metadata_fetcher.fetch_metadata_for_youtube(video_id)
                                    if youtube_metadata and 'error' not in youtube_metadata:
                                        # Merge YouTube metadata into context
                                        context.update(youtube_metadata)
                                        self._logger.info(f"Fetched YouTube metadata for {video_id}: {youtube_metadata.get('title', 'Unknown')}")
                                    else:
                                        self._logger.warning(f"Failed to fetch YouTube metadata for {video_id}: {youtube_metadata.get('error', 'Unknown error')}")
                                except Exception as e:
                                    self._logger.warning(f"Exception fetching YouTube metadata for {video_id}: {e}")
                
                # Get all classifiers in priority order
                classifiers = self._classifier_registry.get_all()
                
                # Try each classifier until one returns a category
                for classifier in classifiers:
                    if hasattr(classifier, 'classify'):
                        try:
                            classification = await classifier.classify(domain, context)
                            if classification is not None:
                                # Use the specific classifier name from metadata if available (e.g., youtube_rule_based, youtube_llm)
                                specific_classifier_name = classification.metadata.get('classifier', classifier.name) if classification.metadata else classifier.name
                                self._logger.info(f"Classifier '{specific_classifier_name}' classified domain '{domain_str}' as {classification.category.name} (confidence: {classification.confidence})")
                                return ClassificationResult(
                                    category=classification.category,
                                    classifier_name=specific_classifier_name,
                                    confidence=classification.confidence,
                                    metadata=classification.metadata
                                )
                        except Exception as e:
                            self._logger.warning(f"Classifier '{classifier.name}' failed to classify domain '{domain_str}': {e}")
                            continue
                
                self._logger.info(f"No classifier could classify domain '{domain_str}'")
                return ClassificationResult(category=None, classifier_name=None)
                
            except Exception as e:
                self._logger.warning(f"Could not classify domain '{domain_str}': {e}")
                return ClassificationResult(category=None, classifier_name=None)
                
        except Exception as e:
            self._logger.error(f"Error classifying domain '{domain_str}': {e}")
            return ClassificationResult(category=None, classifier_name=None)

    async def classify_domain(self, domain_str: str, url: Optional[str] = None) -> Optional[Category]:
        """
        Classify a domain into a category.
        
        Args:
            domain_str: The domain string to classify
            url: Optional full URL for context-aware classification
            
        Returns:
            Optional[Category]: The classified category, or None if classification fails
        """
        # Use the detailed method and return just the category for backward compatibility
        result = await self.classify_domain_detailed(domain_str, url)
        return result.category
    
    async def classify_domain_with_context(self, domain_str: str, context: Dict[str, Any]) -> Optional[Category]:
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
                try:
                    if hasattr(classifier, 'classify_with_context'):
                        self._logger.info(f"Trying classifier '{classifier.name}' for domain '{domain_str}' with context: {context}")
                        classification = classifier.classify_with_context(domain, context)
                        if classification is not None:
                            self._logger.info(f"Classifier '{classifier.name}' classified domain '{domain_str}' as {classification} with context")
                            self._logger.info(f"Classification details - Category: {classification.category}, Confidence: {classification.confidence}, Metadata: {classification.metadata}")
                            return classification.category
                        else:
                            self._logger.info(f"Classifier '{classifier.name}' returned None for domain '{domain_str}'")
                    else:
                        # Try regular classify method for non-context-aware classifiers
                        self._logger.info(f"Trying regular classifier '{classifier.name}' for domain '{domain_str}'")
                        classification = await classifier.classify(domain, context)
                        if classification is not None:
                            if hasattr(classification, 'category'):
                                self._logger.info(f"Classifier '{classifier.name}' classified domain '{domain_str}' as {classification.category}")
                                return classification.category
                            else:
                                # Handle case where classify returns Category directly
                                self._logger.info(f"Classifier '{classifier.name}' classified domain '{domain_str}' as {classification}")
                                return classification
                except Exception as e:
                    self._logger.warning(f"Classifier '{classifier.name}' failed to classify domain '{domain_str}': {e}")
                    continue
            
            # No classifier could handle this domain
            self._logger.info(f"No classifier could classify domain '{domain_str}' with context")
            return None
            
        except Exception as e:
            self._logger.error(f"Error classifying domain '{domain_str}' with context: {e}")
            return None
    
    async def should_block_tab(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
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
            category = await self.classify_domain_with_context(domain_str, context)
            
            # Set the category on the domain object
            if category:
                domain.category = category
            else:
                domain.category = Category.UNKNOWN
            
            # Check if the domain should be blocked
            decision = await self._blocking_pipeline.should_block_with_context(domain, context)
            
            # Cache the result
            self._blocking_cache.set(cache_key, (decision.should_block, decision.reason or ""))
            
            return decision.should_block
            
        except Exception as e:
            self._logger.error(f"Error checking if tab should be blocked for URL '{url}': {e}")
            return False
    
    async def get_blocking_reason(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
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
            
            # If not cached, call should_block_tab which will do the classification and cache the result
            should_block = await self.should_block_tab(url, metadata)
            
            # Now check cache again - should_block_tab should have populated it
            cached_result = self._blocking_cache.get(cache_key)
            if cached_result is not None:
                should_block, reason = cached_result
                return reason if should_block else None
            
            # Fallback - this shouldn't happen but just in case
            return decision.reason if decision.should_block else None
            
        except Exception as e:
            self._logger.error(f"Error getting blocking reason for URL '{url}': {e}")
            return None
    
    async def check_blocking_with_details(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> BlockingResult:
        """
        Check if a URL should be blocked and return comprehensive details.
        
        Args:
            url: The URL to check.
            metadata: Optional metadata about the tab.
            
        Returns:
            BlockingResult: Complete blocking decision with reason and classification details.
        """
        try:
            # Check cache first
            cache_key = f"{url}:{hash(str(metadata))}"
            cached_result = self._blocking_cache.get(cache_key)
            if cached_result is not None:
                should_block, reason = cached_result
                return BlockingResult(should_block=should_block, reason=reason)
            
            # Extract domain from URL
            domain_str = extract_domain_from_url(url)
            if not domain_str:
                self._logger.warning(f"Could not extract domain from URL: {url}")
                return BlockingResult(should_block=False, reason="Could not extract domain")
            
            # Create domain object
            domain = Domain(domain_str)
            
            # Classify the domain with detailed results using context
            context = {"url": url, "metadata": metadata or {}}
            
            # For YouTube URLs, we need to use classify_domain_detailed with proper context
            if 'youtube.com' in domain_str or 'youtu.be' in domain_str:
                classification_result = await self.classify_domain_detailed(domain_str, url)
            else:
                classification_result = await self.classify_domain_detailed(domain_str, url)
            
            # Set the category on the domain object
            if classification_result.category:
                domain.category = classification_result.category
            else:
                domain.category = Category.UNKNOWN
            
            # Check if the domain should be blocked
            decision = await self._blocking_pipeline.should_block_with_context(domain, context)
            
            # Log the blocking decision
            if decision.should_block:
                self._logger.info(f"Domain '{domain_str}' blocked with context: {decision.reason}")
            else:
                self._logger.info(f"No strategy blocked domain '{domain_str}'")
            
            # Cache the result
            self._blocking_cache.set(cache_key, (decision.should_block, decision.reason or ""))
            
            return BlockingResult(
                should_block=decision.should_block,
                reason=decision.reason,
                category=classification_result.category,
                classifier_name=classification_result.classifier_name
            )
            
        except Exception as e:
            self._logger.error(f"Error checking blocking for URL '{url}': {e}")
            return BlockingResult(should_block=False, reason=f"Error: {e}")
    
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
