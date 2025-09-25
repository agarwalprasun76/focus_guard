"""
Base classes and common functionality for YouTube classification."""

import re
import logging
import os
from typing import Dict, Any, Optional, List, Set, Pattern, Type, TypeVar, Generic

from focus_guard.core.domain.models import Domain, Category, Classification
from .base import BaseDomainClassifier, DomainClassifier

logger = logging.getLogger(__name__)

# YouTube domain patterns
YOUTUBE_DOMAINS = {
    'youtube.com',
    'youtu.be',
    'youtube-nocookie.com',
    'youtubeeducation.com',
    'youtubekids.com',
    'youtubegaming.com',
    'youtubemusic.com'
}

# YouTube content type detection patterns
CONTENT_TYPE_PATTERNS = {
    'video': re.compile(r'watch\?v=([^&/]+)'),
    'playlist': re.compile(r'playlist\?list=([^&/]+)'),
    'channel': re.compile(r'channel/([^/]+)'),
    'user': re.compile(r'user/([^/]+)'),
    'shorts': re.compile(r'shorts/([^/?#&]+)'),
    'live': re.compile(r'live/([^/?#&]+)')
}

class YouTubeClassifier(BaseDomainClassifier):
    """Composite classifier for YouTube content."""
    
    def __init__(self, classifiers: List[DomainClassifier], name: str = "youtube"):
        """Initialize with a list of classifiers to try in order."""
        super().__init__(name)
        self.classifiers = classifiers
    
    @classmethod
    def create_default(cls) -> 'YouTubeClassifier':
        """Create a default YouTube classifier with available classifiers."""
        from .youtube_rules import RuleBasedYouTubeClassifier
        from .youtube_llm import LLMBasedYouTubeClassifier
        
        classifiers: List[DomainClassifier] = [RuleBasedYouTubeClassifier()]
        
        # Try to add LLM-based classifiers if available
        try:
            from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
            if 'OPENAI_API_KEY' in os.environ:
                logger.info("OpenAI API key found, creating LLM classifier")
                llm_client = OpenAIClient()
                llm_classifier = LLMBasedYouTubeClassifier(llm_client=llm_client)
                classifiers.insert(0, llm_classifier)
                logger.info("LLM YouTube classifier added successfully")
            else:
                logger.info("No OpenAI API key found, using rule-based only")
        except ImportError as e:
            logger.debug(f"OpenAI client not available: {e}, using rule-based only")
        except Exception as e:
            logger.warning(f"Failed to create LLM classifier: {e}, using rule-based only")
        
        return cls(classifiers)
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify YouTube content using available classifiers."""
        if context is None:
            context = {}
        
        # Create cache key to prevent duplicate calls
        cache_key = None
        if 'video_id' in context:
            cache_key = f"composite_youtube:{context['video_id']}"
        elif 'url' in context:
            cache_key = f"composite_youtube:{context['url']}"
        
        # Check if we have a cached result for this content
        if hasattr(self, '_classification_cache') and cache_key and cache_key in self._classification_cache:
            logger.debug(f"Composite classifier cache hit for {cache_key}")
            return self._classification_cache[cache_key]
        
        # Initialize cache if not exists
        if not hasattr(self, '_classification_cache'):
            self._classification_cache = {}
        
        # Try each classifier in order until one succeeds
        for classifier in self.classifiers:
            try:
                logger.info(f"Trying classifier '{classifier.name}' for YouTube content")
                result = await classifier.classify(domain, context)
                if result is not None:
                    if result.metadata is None:
                        result.metadata = {}
                    # Preserve the specific classifier name (e.g., youtube_rule_based, youtube_llm)
                    result.metadata['classifier'] = classifier.name
                    result.metadata['composite_classifier'] = self.name
                    
                    # Cache the result to prevent duplicate calls
                    if cache_key:
                        # Manage cache size (simple FIFO)
                        if len(self._classification_cache) >= 50:
                            oldest_key = next(iter(self._classification_cache))
                            del self._classification_cache[oldest_key]
                        self._classification_cache[cache_key] = result
                        logger.debug(f"Cached composite result for {cache_key}")
                    
                    logger.info(f"Composite classifier returning result from '{classifier.name}': {result.category.name} (confidence: {result.confidence})")
                    return result
            except Exception as e:
                logger.warning(f"Classifier {classifier.name} failed: {e}")
                continue
        
        return None
    
    def classify_with_context(
        self,
        domain: Domain,
        context: Dict[str, Any]
    ) -> Optional[Classification]:
        """Synchronous wrapper for classify method to support context-aware classification."""
        import asyncio
        
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, we need to handle this differently
            # For now, we'll create a new event loop in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.classify(domain, context))
                return future.result()
        except RuntimeError:
            # No event loop running, we can use asyncio.run directly
            return asyncio.run(self.classify(domain, context))
