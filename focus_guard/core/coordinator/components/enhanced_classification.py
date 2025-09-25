"""
Enhanced domain classification component with multi-level caching and background processing.

This module provides an optimized classification component that leverages the
enhanced classification pipeline for improved performance and caching.
"""

import asyncio
import logging
import os
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from focus_guard.core.classification.enhanced_pipeline import EnhancedClassificationPipeline, EnhancedClassificationFactory
from focus_guard.core.classification.base import ClassifierRegistry
from focus_guard.core.domain.models import Classification as ClassificationResult
from focus_guard.core.domain.models import Category, Domain
from focus_guard.core.coordinator.events import EventTypes, EventData
from focus_guard.core.coordinator.interfaces import EventBus, Component
from focus_guard.core.config.interfaces import ConfigurationManager
from focus_guard.core.coordinator.components.base import BaseComponent

logger = logging.getLogger(__name__)


def create_enhanced_classifier_component(
    event_bus: EventBus, 
    config_manager: ConfigurationManager,
    cache_dir: Optional[str] = None
) -> Component:
    """
    Create and configure the enhanced domain classifier component.
    
    Args:
        event_bus: The event bus for component communication
        config_manager: The configuration manager
        cache_dir: Optional cache directory (defaults to system cache dir)
        
    Returns:
        Component: The configured enhanced domain classifier component
    """
    # Get cache directory
    if cache_dir is None:
        cache_dir = os.path.join(
            os.getenv('FOCUS_GUARD_CACHE_DIR', 
                     os.path.join(os.path.expanduser('~'), '.focusguard', 'cache')),
            'classification'
        )
    
    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)
    
    # Get configuration for enhanced pipeline
    config = {
        'cache': {
            'memory_ttl': config_manager.get_value('classification.cache.memory_ttl', 3600),
            'disk_ttl': config_manager.get_value('classification.cache.disk_ttl', 86400),
            'max_memory_size': config_manager.get_value('classification.cache.max_memory_size', 1000),
            'max_disk_size': config_manager.get_value('classification.cache.max_disk_size', 10000),
            'refresh_interval': config_manager.get_value('classification.cache.refresh_interval', 300),
            'enable_background_refresh': config_manager.get_value('classification.cache.enable_background_refresh', True)
        },
        'background': {
            'refresh_interval': config_manager.get_value('classification.background.refresh_interval', 300),
            'warmup_batch_size': config_manager.get_value('classification.background.warmup_batch_size', 10),
            'warmup_delay': config_manager.get_value('classification.background.warmup_delay', 0.5)
        }
    }
    
    # Create classifier registry
    registry = ClassifierRegistry()
    
    # TODO: Register actual classifiers here based on configuration
    # This would need to be implemented based on available classifiers
    
    # Create enhanced pipeline
    pipeline = EnhancedClassificationFactory.create_pipeline(registry, cache_dir, config)
    
    # Create and return the component
    return EnhancedClassificationComponent(
        pipeline=pipeline,
        event_bus=event_bus,
        config_manager=config_manager
    )


class DomainClassifiedEventData(EventData):
    """Event data for domain classified events."""
    
    def __init__(self, source: str, domain: str, url: str, result: ClassificationResult):
        """
        Initialize the domain classified event data.
        
        Args:
            source: The source of the event
            domain: The domain that was classified
            url: The URL that was classified
            result: The classification result
        """
        super().__init__(source)
        self.domain = domain
        self.url = url
        self.result = result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event data to a dictionary."""
        data = super().to_dict()
        data["domain"] = self.domain
        data["url"] = self.url
        data["result"] = self.result.to_dict() if hasattr(self.result, "to_dict") else str(self.result)
        return data


class EnhancedClassificationComponent(BaseComponent):
    """
    Enhanced classification component with multi-level caching and background processing.
    
    This component provides:
    - Multi-level caching (memory + disk)
    - Background classification for popular domains
    - Cache warming on startup
    - Performance monitoring
    - Smart cache key generation
    """
    
    def __init__(
        self, 
        pipeline: EnhancedClassificationPipeline, 
        event_bus: EventBus, 
        config_manager: ConfigurationManager
    ):
        """
        Initialize the enhanced classification component.
        
        Args:
            pipeline: The enhanced classification pipeline
            event_bus: The event bus for communication
            config_manager: The configuration manager
        """
        super().__init__("enhanced_domain_classifier", event_bus, config_manager)
        self._pipeline = pipeline
        self._warmup_on_start = True
        self._performance_monitoring_task = None
        self._performance_log_interval = 1800  # 30 minutes
    
    async def _initialize_component(self) -> bool:
        """Initialize the enhanced classification component."""
        try:
            # Configure from settings
            self._warmup_on_start = self._config_manager.get_value(
                "classification.warmup_on_start", 
                True
            )
            self._performance_log_interval = self._config_manager.get_value(
                "classification.performance_log_interval", 
                1800
            )
            
            self._logger.info("Initializing enhanced domain classifier")
            
            # Subscribe to browser tab events
            if self._event_bus is not None:
                await self._event_bus.subscribe(EventTypes.TAB_OPENED, self)
                await self._event_bus.subscribe(EventTypes.TAB_UPDATED, self)
            else:
                self._logger.warning("Event bus not available - skipping event subscriptions")
            
            return True
        except Exception as e:
            self._logger.exception(f"Error initializing enhanced domain classifier: {e}")
            return False
    
    async def _start_component(self) -> bool:
        """Start the enhanced classification component."""
        try:
            # Start the enhanced pipeline
            await self._pipeline.start()
            
            # Start performance monitoring
            self._performance_monitoring_task = asyncio.create_task(
                self._performance_monitoring_loop()
            )
            
            # Warm cache if enabled
            if self._warmup_on_start:
                asyncio.create_task(self._warmup_cache_async())
            
            self._logger.info("Enhanced domain classifier started")
            return True
        except Exception as e:
            self._logger.exception(f"Error starting enhanced domain classifier: {e}")
            return False
    
    async def _stop_component(self) -> bool:
        """Stop the enhanced classification component."""
        try:
            # Stop performance monitoring
            if self._performance_monitoring_task:
                self._performance_monitoring_task.cancel()
                try:
                    await self._performance_monitoring_task
                except asyncio.CancelledError:
                    pass
                self._performance_monitoring_task = None
            
            # Stop the enhanced pipeline
            await self._pipeline.stop()
            
            self._logger.info("Enhanced domain classifier stopped")
            return True
        except Exception as e:
            self._logger.exception(f"Error stopping enhanced domain classifier: {e}")
            return False
    
    async def _shutdown_component(self) -> bool:
        """Shutdown the enhanced classification component."""
        # Pipeline handles its own cleanup
        return True
    
    def _get_component_status(self) -> Dict[str, Any]:
        """Get the component-specific status."""
        status = {
            "pipeline_started": self._pipeline.started,
            "warmup_on_start": self._warmup_on_start,
            "performance_monitoring": self._performance_monitoring_task is not None
        }
        
        # Add performance statistics
        try:
            perf_stats = self._pipeline.get_performance_stats()
            status.update(perf_stats)
        except Exception as e:
            self._logger.warning(f"Could not get performance stats: {e}")
        
        return status
    
    def _is_component_healthy(self) -> bool:
        """Check if the component is healthy."""
        return (
            self._pipeline.started and
            (self._performance_monitoring_task is None or 
             not self._performance_monitoring_task.done())
        )
    
    async def on_event(self, event_type: str, event_data: Any) -> None:
        """Handle an event."""
        await super().on_event(event_type, event_data)
        
        if event_type in [EventTypes.TAB_OPENED, EventTypes.TAB_UPDATED]:
            # Extract tab information
            tab = event_data.tab
            
            # Classify the domain asynchronously
            if tab.url and tab.url.startswith("http"):
                asyncio.create_task(self._classify_and_publish(tab.url, tab))
    
    async def _classify_and_publish(self, url: str, tab: Any = None) -> None:
        """
        Classify a URL and publish the result.
        
        Args:
            url: The URL to classify
            tab: Optional tab object with additional context
        """
        try:
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Build context from tab and URL
            context = {"url": url}
            if tab:
                # Add tab-specific context
                if hasattr(tab, 'title') and tab.title:
                    context['title'] = tab.title
                if hasattr(tab, 'id') and tab.id:
                    context['tab_id'] = tab.id
                
                # YouTube-specific context extraction
                if 'youtube.com' in domain or 'youtu.be' in domain:
                    context.update(self._extract_youtube_context(url, tab))
            
            # Classify using enhanced pipeline
            domain_obj = Domain(domain)
            result = await self._pipeline.classify(domain_obj, context)
            
            if result:
                # Publish the result
                await self._event_bus.publish(
                    EventTypes.DOMAIN_CLASSIFIED,
                    DomainClassifiedEventData("enhanced_classification", domain, url, result)
                )
            
        except Exception as e:
            self._logger.exception(f"Error classifying URL {url}: {e}")
    
    def _extract_youtube_context(self, url: str, tab: Any) -> Dict[str, Any]:
        """Extract YouTube-specific context from URL and tab."""
        context = {}
        
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            
            # Extract video ID
            if 'watch' in parsed.path:
                query_params = parse_qs(parsed.query)
                if 'v' in query_params:
                    context['video_id'] = query_params['v'][0]
            elif 'youtu.be' in parsed.netloc:
                # Short URL format
                video_id = parsed.path.lstrip('/')
                if video_id:
                    context['video_id'] = video_id
            
            # Extract playlist ID
            if parsed.query:
                query_params = parse_qs(parsed.query)
                if 'list' in query_params:
                    context['playlist_id'] = query_params['list'][0]
            
            # Add tab title as video title for YouTube
            if hasattr(tab, 'title') and tab.title:
                # YouTube titles often end with " - YouTube"
                title = tab.title
                if title.endswith(' - YouTube'):
                    title = title[:-10]  # Remove " - YouTube"
                context['title'] = title
        
        except Exception as e:
            self._logger.debug(f"Error extracting YouTube context: {e}")
        
        return context
    
    async def _warmup_cache_async(self) -> None:
        """Warm up cache asynchronously."""
        try:
            self._logger.info("Starting cache warmup")
            stats = await self._pipeline.warm_cache()
            self._logger.info(
                f"Cache warmup completed: {stats['domains_warmed']}/{stats['total_domains']} "
                f"domains in {stats['elapsed_time']:.2f}s "
                f"(success rate: {stats['success_rate']:.1%})"
            )
        except Exception as e:
            self._logger.error(f"Cache warmup failed: {e}")
    
    async def _performance_monitoring_loop(self) -> None:
        """Performance monitoring loop."""
        try:
            while True:
                await asyncio.sleep(self._performance_log_interval)
                
                try:
                    stats = self._pipeline.get_performance_stats()
                    self._logger.info(
                        f"Classification performance - "
                        f"Requests: {stats['total_requests']}, "
                        f"Cache hit rate: {stats['cache_hit_rate']:.1%}, "
                        f"Avg response time: {stats['avg_response_time']*1000:.1f}ms, "
                        f"Fast responses: {stats['fast_response_rate']:.1%}"
                    )
                except Exception as e:
                    self._logger.warning(f"Error logging performance stats: {e}")
        
        except asyncio.CancelledError:
            self._logger.debug("Performance monitoring loop cancelled")
    
    async def _handle_config_changed(self, event_data: Any) -> None:
        """Handle configuration change events."""
        path = event_data.path
        new_value = event_data.new_value
        
        if path.startswith("classification."):
            self._logger.info(f"Configuration changed: {path} = {new_value}")
            # Note: Some configuration changes may require pipeline restart
            # This could be implemented based on specific needs
    
    # Public API methods
    
    async def classify_domain(self, domain: str, url: str = None, context: Dict[str, Any] = None) -> ClassificationResult:
        """
        Classify a domain using the enhanced pipeline.
        
        Args:
            domain: The domain to classify
            url: Optional URL for context
            context: Optional additional context
            
        Returns:
            Classification result
        """
        domain_obj = Domain(domain)
        
        # Build context
        full_context = context or {}
        if url:
            full_context["url"] = url
        
        result = await self._pipeline.classify(domain_obj, full_context)
        return result
    
    async def get_category_for_domain(self, domain: str, url: str = None, context: Dict[str, Any] = None) -> Category:
        """
        Get the category for a domain.
        
        Args:
            domain: The domain to classify
            url: Optional URL for context
            context: Optional additional context
            
        Returns:
            Category for the domain
        """
        result = await self.classify_domain(domain, url, context)
        return result.category if result else Category.UNKNOWN
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self._pipeline.get_performance_stats()
    
    async def force_cache_warmup(self) -> Dict[str, Any]:
        """Force immediate cache warmup."""
        return await self._pipeline.warm_cache()
    
    def get_pipeline(self) -> EnhancedClassificationPipeline:
        """Get the enhanced classification pipeline."""
        return self._pipeline


# Alias for backward compatibility
EnhancedDomainClassifierComponent = EnhancedClassificationComponent
