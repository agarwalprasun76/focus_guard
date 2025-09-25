"""
Enhanced classification pipeline with multi-level caching and background processing.

This module provides an optimized classification pipeline that leverages
multi-level caching, background classification, and intelligent cache warming
to achieve sub-500ms response times for cached results.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from urllib.parse import urlparse
import hashlib

from focus_guard.core.classification.base import ClassificationPipeline, ClassifierRegistry
from focus_guard.core.cache.multi_level_cache import MultiLevelCache
from focus_guard.core.utils.background_tasks import BackgroundClassificationService
from focus_guard.core.domain.models import Domain, Classification, Category
from focus_guard.core.domain.constants import DOMAIN_CATEGORIES

logger = logging.getLogger(__name__)


class EnhancedClassificationPipeline:
    """
    Enhanced classification pipeline with aggressive caching and background processing.
    
    Features:
    - Multi-level caching (memory + disk)
    - Smart cache key generation for context-aware caching
    - Background classification for popular domains
    - Cache warming on startup
    - Performance monitoring and metrics
    - Fallback to original pipeline for cache misses
    """
    
    def __init__(
        self,
        registry: ClassifierRegistry,
        cache_dir: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize enhanced classification pipeline.
        
        Args:
            registry: Classifier registry
            cache_dir: Directory for cache storage
            config: Optional configuration
        """
        self.registry = registry
        self.config = config or {}
        
        # Original pipeline for fallback
        self.fallback_pipeline = ClassificationPipeline(registry)
        
        # Setup cache configuration
        cache_config = self.config.get('cache', {})
        self.cache = MultiLevelCache(
            cache_dir=cache_dir,
            memory_ttl=cache_config.get('memory_ttl', 3600),
            disk_ttl=cache_config.get('disk_ttl', 86400),
            max_memory_size=cache_config.get('max_memory_size', 1000),
            max_disk_size=cache_config.get('max_disk_size', 10000),
            background_refresh_interval=cache_config.get('refresh_interval', 300),
            enable_background_refresh=cache_config.get('enable_background_refresh', True)
        )
        
        # Background service
        self.background_service = BackgroundClassificationService(
            cache=self.cache,
            classifier_func=self._classify_for_background,
            config=self.config.get('background', {})
        )
        
        # Performance tracking
        self.performance_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_response_time': 0.0,
            'fast_responses': 0,  # < 500ms
            'slow_responses': 0,  # >= 500ms
        }
        
        # Cache key strategies
        self.cache_key_strategies = {
            'domain_only': self._generate_domain_key,
            'url_context': self._generate_url_context_key,
            'youtube_video': self._generate_youtube_video_key,
            'youtube_channel': self._generate_youtube_channel_key
        }
        
        self.started = False
    
    async def start(self) -> None:
        """Start the enhanced pipeline and background services."""
        if self.started:
            return
        
        # Start background service
        await self.background_service.start()
        
        self.started = True
        logger.info("Enhanced classification pipeline started")
    
    async def stop(self) -> None:
        """Stop the pipeline and background services."""
        if not self.started:
            return
        
        # Stop background service
        await self.background_service.stop()
        
        # Close cache
        await self.cache.close()
        
        self.started = False
        logger.info("Enhanced classification pipeline stopped")
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """
        Classify domain with enhanced caching and performance optimization.
        
        Args:
            domain: Domain to classify
            context: Optional context for classification
            
        Returns:
            Classification result or None
        """
        start_time = time.time()
        self.performance_stats['total_requests'] += 1
        
        try:
            # Generate cache key based on domain and context
            cache_key = self._generate_cache_key(domain, context)
            
            # Try to get from cache first
            cached_result = await self.cache.get(
                cache_key,
                classifier_func=lambda: self._classify_with_fallback(domain, context)
            )
            
            if cached_result is not None:
                self.performance_stats['cache_hits'] += 1
                response_time = time.time() - start_time
                self._update_performance_stats(response_time)
                
                logger.debug(f"Cache hit for {domain.value} ({response_time*1000:.1f}ms)")
                return cached_result
            
            # Cache miss - classify using fallback pipeline
            self.performance_stats['cache_misses'] += 1
            result = await self._classify_with_fallback(domain, context)
            
            # Cache the result
            if result is not None:
                await self.cache.set(cache_key, result, source='pipeline')
            
            response_time = time.time() - start_time
            self._update_performance_stats(response_time)
            
            logger.debug(f"Classification completed for {domain.value} ({response_time*1000:.1f}ms)")
            return result
        
        except Exception as e:
            logger.error(f"Enhanced classification failed for {domain.value}: {e}")
            # Fallback to original pipeline
            return await self._classify_with_fallback(domain, context)
    
    def add_classifier(self, name: str) -> None:
        """Add classifier to the pipeline."""
        self.fallback_pipeline.add_classifier(name)
    
    def remove_classifier(self, name: str) -> None:
        """Remove classifier from the pipeline."""
        self.fallback_pipeline.remove_classifier(name)
    
    async def warm_cache(self, domains: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Warm cache with specified domains or default popular domains.
        
        Args:
            domains: Optional list of domains to warm
            
        Returns:
            Warmup statistics
        """
        if domains is None:
            # Use domains from configuration
            domains = []
            for category_domains in DOMAIN_CATEGORIES.values():
                domains.extend(category_domains)
        
        start_time = time.time()
        warmed_count = await self.cache.warm_cache(domains, self._classify_for_warmup)
        elapsed = time.time() - start_time
        
        stats = {
            'domains_warmed': warmed_count,
            'total_domains': len(domains),
            'elapsed_time': elapsed,
            'success_rate': warmed_count / len(domains) if domains else 0
        }
        
        logger.info(f"Cache warming completed: {warmed_count}/{len(domains)} domains in {elapsed:.2f}s")
        return stats
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_requests = self.performance_stats['total_requests']
        
        stats = {
            **self.performance_stats,
            'cache_hit_rate': (
                self.performance_stats['cache_hits'] / max(1, total_requests)
            ),
            'fast_response_rate': (
                self.performance_stats['fast_responses'] / max(1, total_requests)
            )
        }
        
        # Add cache statistics
        cache_stats = self.cache.get_stats()
        stats['cache_stats'] = cache_stats
        
        # Add background service statistics
        if self.background_service:
            stats['background_stats'] = self.background_service.get_stats()
        
        return stats
    
    def _generate_cache_key(self, domain: Domain, context: Optional[Dict[str, Any]]) -> str:
        """
        Generate intelligent cache key based on domain and context.
        
        Args:
            domain: Domain to generate key for
            context: Optional context
            
        Returns:
            Cache key string
        """
        if context is None:
            return self._generate_domain_key(domain, context)
        
        # Determine best strategy based on domain and context
        domain_value = domain.value.lower()
        
        if 'youtube.com' in domain_value or 'youtu.be' in domain_value:
            if 'video_id' in context:
                return self._generate_youtube_video_key(domain, context)
            elif 'channel_id' in context or 'channel_title' in context:
                return self._generate_youtube_channel_key(domain, context)
        
        if 'url' in context:
            return self._generate_url_context_key(domain, context)
        
        return self._generate_domain_key(domain, context)
    
    def _generate_domain_key(self, domain: Domain, context: Optional[Dict[str, Any]]) -> str:
        """Generate simple domain-based cache key."""
        return f"domain:{domain.value}"
    
    def _generate_url_context_key(self, domain: Domain, context: Dict[str, Any]) -> str:
        """Generate cache key including URL context."""
        url = context.get('url', '')
        parsed = urlparse(url)
        
        # Create key from domain + path (ignore query params for better cache hits)
        key_parts = [domain.value]
        if parsed.path and parsed.path != '/':
            key_parts.append(parsed.path)
        
        key = ':'.join(key_parts)
        return f"url_context:{hashlib.md5(key.encode()).hexdigest()}"
    
    def _generate_youtube_video_key(self, domain: Domain, context: Dict[str, Any]) -> str:
        """Generate YouTube video-specific cache key."""
        video_id = context.get('video_id', '')
        if video_id:
            return f"youtube_video:{video_id}"
        
        # Fallback to URL-based key
        return self._generate_url_context_key(domain, context)
    
    def _generate_youtube_channel_key(self, domain: Domain, context: Dict[str, Any]) -> str:
        """Generate YouTube channel-specific cache key."""
        channel_id = context.get('channel_id', '')
        if channel_id:
            return f"youtube_channel:{channel_id}"
        
        channel_title = context.get('channel_title', '')
        if channel_title:
            return f"youtube_channel_title:{hashlib.md5(channel_title.encode()).hexdigest()}"
        
        # Fallback to domain key
        return self._generate_domain_key(domain, context)
    
    async def _classify_with_fallback(
        self, 
        domain: Domain, 
        context: Optional[Dict[str, Any]]
    ) -> Optional[Classification]:
        """Classify using the fallback pipeline."""
        try:
            # The fallback pipeline classify method is synchronous
            return self.fallback_pipeline.classify(domain, context)
        except Exception as e:
            logger.error(f"Fallback classification failed for {domain.value}: {e}")
            return None
    
    async def _classify_for_background(self, domain: Domain) -> Optional[Classification]:
        """Classify domain for background processing."""
        return await self._classify_with_fallback(domain, None)
    
    async def _classify_for_warmup(self, domain_str: str) -> Optional[Classification]:
        """Classify domain string for cache warming."""
        try:
            domain = Domain(domain_str)
            return await self._classify_with_fallback(domain, None)
        except Exception as e:
            logger.warning(f"Warmup classification failed for {domain_str}: {e}")
            return None
    
    def _update_performance_stats(self, response_time: float) -> None:
        """Update performance statistics."""
        # Update average response time
        total = self.performance_stats['total_requests']
        current_avg = self.performance_stats['avg_response_time']
        self.performance_stats['avg_response_time'] = (
            (current_avg * (total - 1) + response_time) / total
        )
        
        # Track fast vs slow responses
        if response_time < 0.5:  # 500ms threshold
            self.performance_stats['fast_responses'] += 1
        else:
            self.performance_stats['slow_responses'] += 1


class EnhancedClassificationFactory:
    """Factory for creating enhanced classification pipelines."""
    
    @staticmethod
    def create_pipeline(
        registry: ClassifierRegistry,
        cache_dir: str,
        config: Optional[Dict[str, Any]] = None
    ) -> EnhancedClassificationPipeline:
        """
        Create an enhanced classification pipeline.
        
        Args:
            registry: Classifier registry
            cache_dir: Cache directory
            config: Optional configuration
            
        Returns:
            Configured enhanced pipeline
        """
        # Default configuration
        default_config = {
            'cache': {
                'memory_ttl': 3600,  # 1 hour
                'disk_ttl': 86400,   # 24 hours
                'max_memory_size': 1000,
                'max_disk_size': 10000,
                'refresh_interval': 300,  # 5 minutes
                'enable_background_refresh': True
            },
            'background': {
                'refresh_interval': 300,
                'warmup_batch_size': 10,
                'warmup_delay': 0.5
            }
        }
        
        # Merge with provided config
        if config:
            default_config.update(config)
        
        return EnhancedClassificationPipeline(registry, cache_dir, default_config)
    
    @staticmethod
    def create_with_classifiers(
        classifiers: List[str],
        cache_dir: str,
        config: Optional[Dict[str, Any]] = None
    ) -> EnhancedClassificationPipeline:
        """
        Create pipeline with specified classifiers.
        
        Args:
            classifiers: List of classifier names to add
            cache_dir: Cache directory
            config: Optional configuration
            
        Returns:
            Configured pipeline with classifiers
        """
        registry = ClassifierRegistry()
        
        # Register classifiers (this would need to be implemented based on available classifiers)
        # For now, we'll create an empty registry and let the caller add classifiers
        
        pipeline = EnhancedClassificationFactory.create_pipeline(registry, cache_dir, config)
        
        # Add classifiers to pipeline
        for classifier_name in classifiers:
            pipeline.add_classifier(classifier_name)
        
        return pipeline
