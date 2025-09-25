"""
Domain classification component for the Focus Guard coordinator.

This module provides a wrapper for the domain classification system, making it
available to the coordinator and other components.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING
import os
import json
import shutil
from pathlib import Path

from focus_guard.core.classification.base import ClassificationPipeline, ClassifierRegistry
from focus_guard.core.domain.models import Classification as ClassificationResult
from focus_guard.core.domain.models import Category
from focus_guard.core.coordinator.events import EventTypes, EventData
from focus_guard.core.coordinator.interfaces import EventBus, Component
from focus_guard.core.config.interfaces import ConfigurationManager
from focus_guard.core.coordinator.components.base import BaseComponent


def create_classifier_component(event_bus: EventBus, config_manager: ConfigurationManager) -> Component:
    """
    Create and configure the domain classifier component.
    
    Args:
        event_bus: The event bus for component communication
        config_manager: The configuration manager
        
    Returns:
        Component: The configured domain classifier component
    """
    # Get the config directory path from environment or use default
    config_dir = os.getenv('FOCUS_GUARD_CONFIG_DIR', 
                         os.path.join(os.path.expanduser('~'), '.focusguard'))
    
    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    # Define template and target config paths
    template_path = Path(__file__).parent.parent.parent.parent.parent / 'config' / 'focus_guard_config_template.json'
    config_path = Path(config_dir) / 'config.json'
    
    # Copy template if config doesn't exist
    if not config_path.exists():
        if not template_path.exists():
            raise FileNotFoundError(f"Template config not found at {template_path}")
        shutil.copy2(template_path, config_path)
    
    # Load the config file
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    # Transform the config to match classifier's expected format
    classifier_config = transform_config_for_classifier(config_data)
    
    # Create the classifier registry and pipeline
    registry = ClassifierRegistry()
    pipeline = ClassificationPipeline(registry)
    
    # Configure the pipeline with classifiers
    # Note: You'll need to register actual classifiers here based on your new structure
    # This is a placeholder that will need to be updated with actual classifier registration
    
    # Create and return the component
    return ClassificationComponent(
        domain_classifier=pipeline,
        event_bus=event_bus,
        config_manager=config_manager
    )


def transform_config_for_classifier(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform the config structure to match what the classifier expects."""
    # If the config already has domain_categories at the root, use it as is
    if 'domain_categories' in config:
        return config
        
    # Otherwise, try to extract from distraction_detection.categories
    if 'distraction_detection' in config and 'categories' in config['distraction_detection']:
        return {
            'domain_categories': {
                'social_media': config['distraction_detection']['categories'].get('social_media', []),
                'games': config['distraction_detection']['categories'].get('games', []),
                'video_streaming': config['distraction_detection']['categories'].get('video_streaming', [])
            }
        }
    
    # Fall back to default categories if nothing else works
    return {
        'domain_categories': {
            'productivity': ['github.com', 'stackoverflow.com', 'docs.python.org'],
            'social': ['twitter.com', 'facebook.com', 'instagram.com'],
            'entertainment': ['youtube.com', 'netflix.com', 'twitch.tv']
        }
    }


class DomainClassifiedEventData(EventData):
    """Event data for domain classified events."""
    
    def __init__(self, source: str, domain: str, url: str, result: ClassificationResult):
        """
        Initialize the domain classified event data.
        
        Args:
            source (str): The source of the event.
            domain (str): The domain that was classified.
            url (str): The URL that was classified.
            result (ClassificationResult): The classification result.
        """
        super().__init__(source)
        self.domain = domain
        self.url = url
        self.result = result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event data to a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the event data.
        """
        data = super().to_dict()
        data["domain"] = self.domain
        data["url"] = self.url
        data["result"] = self.result.to_dict() if hasattr(self.result, "to_dict") else str(self.result)
        return data


class ClassificationComponent(BaseComponent):
    """
    Component wrapper for the domain classification system.
    
    This component provides access to the domain classification system and
    handles classification events.
    """
    
    def __init__(self, domain_classifier: ClassificationPipeline, event_bus: EventBus, config_manager: ConfigurationManager):
        """
        Initialize the classification component.
        
        Args:
            domain_classifier (DomainClassifier): The domain classifier to use.
            event_bus (EventBus): The event bus to use for communication.
            config_manager (ConfigurationManager): The configuration manager to use.
        """
        super().__init__("domain_classifier", event_bus, config_manager)
        self._domain_classifier = domain_classifier
        self._classification_cache = {}  # Cache of classification results by domain
        self._cache_ttl_seconds = 3600  # Default cache TTL in seconds
        self._cache_cleanup_task = None
        self._cache_cleanup_interval = 300  # Default cache cleanup interval in seconds
    
    async def _initialize_component(self) -> bool:
        """
        Initialize the classification component.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            # Configure from settings
            self._cache_ttl_seconds = self._config_manager.get_value(
                "classification.cache_ttl_seconds", 
                self._cache_ttl_seconds
            )
            self._cache_cleanup_interval = self._config_manager.get_value(
                "classification.cache_cleanup_interval_seconds", 
                self._cache_cleanup_interval
            )
            
            # Initialize the domain classifier
            self._logger.info("Initializing domain classifier")
            
            # Subscribe to browser tab events (if event bus is available)
            if self._event_bus is not None:
                self._event_bus.subscribe(EventTypes.TAB_OPENED, self)
                self._event_bus.subscribe(EventTypes.TAB_UPDATED, self)
            else:
                self._logger.warning("Event bus not available - skipping event subscriptions")
            
            return True
        except Exception as e:
            self._logger.exception(f"Error initializing domain classifier: {e}")
            return False
    
    async def _start_component(self) -> bool:
        """
        Start the classification component.
        
        Returns:
            bool: True if startup was successful, False otherwise.
        """
        try:
            # Start cache cleanup task
            self._cache_cleanup_task = asyncio.create_task(self._cleanup_cache())
            
            self._logger.info("Domain classifier started")
            return True
        except Exception as e:
            self._logger.exception(f"Error starting domain classifier: {e}")
            return False
    
    async def _stop_component(self) -> bool:
        """
        Stop the classification component.
        
        Returns:
            bool: True if stopping was successful, False otherwise.
        """
        try:
            # Stop cache cleanup task
            if self._cache_cleanup_task is not None:
                self._cache_cleanup_task.cancel()
                try:
                    await self._cache_cleanup_task
                except asyncio.CancelledError:
                    pass
                self._cache_cleanup_task = None
            
            self._logger.info("Domain classifier stopped")
            return True
        except Exception as e:
            self._logger.exception(f"Error stopping domain classifier: {e}")
            return False
    
    async def _shutdown_component(self) -> bool:
        """
        Shutdown the classification component.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        # Nothing additional to do here
        return True
    
    def _get_component_status(self) -> Dict[str, Any]:
        """
        Get the component-specific status.
        
        Returns:
            Dict[str, Any]: A dictionary containing the component's status information.
        """
        return {
            "cache_size": len(self._classification_cache),
            "cache_ttl_seconds": self._cache_ttl_seconds,
            "cache_cleanup_interval": self._cache_cleanup_interval
        }
    
    def _is_component_healthy(self) -> bool:
        """
        Check if the component implementation is healthy.
        
        Returns:
            bool: True if the component is healthy, False otherwise.
        """
        # Classification component is healthy if cache cleanup task is running
        return self._cache_cleanup_task is not None and not self._cache_cleanup_task.done()
    
    async def _cleanup_cache(self) -> None:
        """
        Clean up expired cache entries.
        
        This method runs in a loop, removing expired cache entries.
        """
        self._logger.debug("Starting classification cache cleanup")
        
        try:
            while True:
                try:
                    # Get current time
                    now = asyncio.get_event_loop().time()
                    
                    # Find expired entries
                    expired_domains = []
                    for domain, entry in self._classification_cache.items():
                        if now - entry["timestamp"] > self._cache_ttl_seconds:
                            expired_domains.append(domain)
                    
                    # Remove expired entries
                    for domain in expired_domains:
                        self._classification_cache.pop(domain, None)
                    
                    if expired_domains:
                        self._logger.debug(f"Removed {len(expired_domains)} expired classification cache entries")
                
                except Exception as e:
                    self._logger.exception(f"Error cleaning up classification cache: {e}")
                
                # Wait for next cleanup
                await asyncio.sleep(self._cache_cleanup_interval)
        
        except asyncio.CancelledError:
            self._logger.debug("Classification cache cleanup cancelled")
            raise
    
    async def on_event(self, event_type: str, event_data: Any) -> None:
        """
        Handle an event.
        
        Args:
            event_type (str): The type of event.
            event_data (Any): The event data.
        """
        await super().on_event(event_type, event_data)
        
        if event_type in [EventTypes.TAB_OPENED, EventTypes.TAB_UPDATED]:
            # Extract tab information
            tab = event_data.tab
            
            # Classify the domain
            if tab.url and tab.url.startswith("http"):
                asyncio.create_task(self._classify_and_publish(tab.url))
    
    async def _classify_and_publish(self, url: str) -> None:
        """
        Classify a URL and publish the result.
        
        Args:
            url (str): The URL to classify.
        """
        try:
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Check cache first
            cached_result = self._get_cached_classification(domain)
            if cached_result:
                # Use cached result
                await self._event_bus.publish(
                    EventTypes.DOMAIN_CLASSIFIED,
                    DomainClassifiedEventData("classification", domain, url, cached_result)
                )
                return
            
            # Classify the domain
            from focus_guard.core.domain.models import Domain
            domain_obj = Domain(domain)
            context = {"url": url} if url else {}
            result = await self._domain_classifier.classify(domain_obj, context)
            
            # Cache the result
            self._cache_classification(domain, result)
            
            # Publish the result
            await self._event_bus.publish(
                EventTypes.DOMAIN_CLASSIFIED,
                DomainClassifiedEventData("classification", domain, url, result)
            )
        
        except Exception as e:
            self._logger.exception(f"Error classifying URL {url}: {e}")
    
    def _get_cached_classification(self, domain: str) -> Optional[ClassificationResult]:
        """
        Get a cached classification result for a domain.
        
        Args:
            domain (str): The domain to get the classification for.
            
        Returns:
            Optional[ClassificationResult]: The cached classification result, or None if not found.
        """
        entry = self._classification_cache.get(domain)
        if entry:
            # Check if entry is still valid
            now = asyncio.get_event_loop().time()
            if now - entry["timestamp"] <= self._cache_ttl_seconds:
                return entry["result"]
        
        return None
    
    def _cache_classification(self, domain: str, result: ClassificationResult) -> None:
        """
        Cache a classification result for a domain.
        
        Args:
            domain (str): The domain to cache the classification for.
            result (ClassificationResult): The classification result to cache.
        """
        self._classification_cache[domain] = {
            "result": result,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def _handle_config_changed(self, event_data: Any) -> None:
        """
        Handle a configuration change event.
        
        Args:
            event_data (Any): The event data.
        """
        path = event_data.path
        new_value = event_data.new_value
        
        if path == "classification.cache_ttl_seconds":
            self._cache_ttl_seconds = new_value
            self._logger.info(f"Updated cache TTL to {new_value} seconds")
        
        elif path == "classification.cache_cleanup_interval_seconds":
            self._cache_cleanup_interval = new_value
            self._logger.info(f"Updated cache cleanup interval to {new_value} seconds")
    
    def get_domain_classifier(self) -> ClassificationPipeline:
        """
        Get the domain classifier pipeline.
        
        Returns:
            ClassificationPipeline: The classification pipeline.
        """
        return self._domain_classifier
    
    async def classify_domain(self, domain: str, url: str = None) -> ClassificationResult:
        """
        Classify a domain.
        
        Args:
            domain (str): The domain to classify.
            url (str, optional): The URL to classify. Defaults to None.
            
        Returns:
            ClassificationResult: The classification result.
        """
        # Check cache first
        cached_result = self._get_cached_classification(domain)
        if cached_result:
            return cached_result
        
        # Classify the domain
        from focus_guard.core.domain.models import Domain
        domain_obj = Domain(domain)
        context = {"url": url} if url else {}
        result = await self._domain_classifier.classify(domain_obj, context)
        
        # Cache the result
        self._cache_classification(domain, result)
        
        return result
    
    async def get_category_for_domain(self, domain: str, url: str = None) -> Category:
        """
        Get the category for a domain.
        
        Args:
            domain (str): The domain to get the category for.
            url (str, optional): The URL to classify. Defaults to None.
            
        Returns:
            Category: The category for the domain.
        """
        result = await self.classify_domain(domain, url)
        return result.category


# Alias for backward compatibility with coordinator
DomainClassifierComponent = ClassificationComponent
