"""Classification service for the override flow.

This module provides a unified interface for classifying content when users
request overrides. It prioritizes LLM classification with rule-based fallback.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class ContentUsefulness(Enum):
    """How useful the content is for a student during study hours."""
    EDUCATIONAL = "educational"      # Directly supports learning
    ENRICHMENT = "enrichment"        # Broadens knowledge, healthy habits
    NEUTRAL = "neutral"              # Not helpful or harmful
    DISTRACTION = "distraction"      # Likely to derail focus
    UNKNOWN = "unknown"              # Could not determine


@dataclass
class ClassificationResult:
    """Result of classifying content for override decisions."""
    domain: str
    url: str
    category: str  # EDUCATION, ENTERTAINMENT, GAMING, etc.
    usefulness: ContentUsefulness
    confidence: float
    reason: str
    classifier_used: str  # 'llm', 'rules', 'fallback'
    is_distracting: bool
    content_type: str = "unknown"  # video, channel, article, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    classification_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "url": self.url,
            "category": self.category,
            "usefulness": self.usefulness.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "classifier_used": self.classifier_used,
            "is_distracting": self.is_distracting,
            "content_type": self.content_type,
            "metadata": self.metadata,
            "classification_time_ms": self.classification_time_ms,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ClassificationResult":
        """Reconstruct from to_dict() output (e.g. from persistent cache)."""
        usefulness_val = (d.get("usefulness") or "unknown").lower()
        usefulness = ContentUsefulness.UNKNOWN
        try:
            usefulness = ContentUsefulness(usefulness_val)
        except ValueError:
            for u in ContentUsefulness:
                if u.value == usefulness_val:
                    usefulness = u
                    break
        return cls(
            domain=d.get("domain", ""),
            url=d.get("url", ""),
            category=d.get("category", "UNKNOWN"),
            usefulness=usefulness,
            confidence=float(d.get("confidence", 0)),
            reason=d.get("reason", ""),
            classifier_used=d.get("classifier_used", "fallback"),
            is_distracting=bool(d.get("is_distracting", False)),
            content_type=d.get("content_type", "unknown"),
            metadata=d.get("metadata") or {},
            classification_time_ms=float(d.get("classification_time_ms", 0)),
        )

    @property
    def budget_key(self) -> str:
        """Key for looking up classification-specific budget."""
        return f"{self.category}:{self.usefulness.value.upper()}"


class ClassificationService:
    """Unified classification service for override flow.
    
    Prioritizes LLM classification for nuanced decisions, with rule-based
    fallback for speed and reliability.
    """
    
    # Cache for recent classifications
    _cache: Dict[str, ClassificationResult] = {}
    _cache_ttl_seconds: float = 300  # 5 minutes
    _cache_timestamps: Dict[str, float] = {}
    _max_cache_size: int = 100
    
    def __init__(self, prefer_llm: bool = True, llm_timeout: float = 5.0):
        """Initialize the classification service.
        
        Args:
            prefer_llm: If True, try LLM first, then fall back to rules.
            llm_timeout: Timeout for LLM classification in seconds.
        """
        self.prefer_llm = prefer_llm
        self.llm_timeout = llm_timeout
        self._youtube_classifier = None
        self._google_classifier = None
        self._reddit_classifier = None
        self._twitter_classifier = None
        self._domain_classifier = None
        self._search_logger = None
        
    def _get_youtube_classifier(self):
        """Lazy-load YouTube classifier."""
        if self._youtube_classifier is None:
            try:
                from focus_guard.core.classification.classifiers.domains.youtube_base import YouTubeClassifier
                self._youtube_classifier = YouTubeClassifier.create_default()
                logger.info("YouTube classifier loaded (LLM + rules)")
            except Exception as e:
                logger.warning("Could not load YouTube classifier: %s", e)
        return self._youtube_classifier
    
    def _get_google_classifier(self):
        """Lazy-load Google classifier."""
        if self._google_classifier is None:
            try:
                from focus_guard.core.classification.classifiers.domains.google import (
                    GoogleClassifier
                )
                self._google_classifier = GoogleClassifier.create_default(use_llm=self.prefer_llm)
                logger.info("Google classifier loaded (LLM=%s)", self.prefer_llm)
            except Exception as e:
                logger.warning("Could not load Google classifier: %s", e)
        return self._google_classifier
    
    def _get_reddit_classifier(self):
        """Lazy-load Reddit classifier."""
        if self._reddit_classifier is None:
            try:
                from focus_guard.core.classification.classifiers.domains.reddit import (
                    create_reddit_classifier
                )
                self._reddit_classifier = create_reddit_classifier()
                logger.info("Reddit classifier loaded")
            except Exception as e:
                logger.warning("Could not load Reddit classifier: %s", e)
        return self._reddit_classifier
    
    def _get_twitter_classifier(self):
        """Lazy-load Twitter/X classifier."""
        if self._twitter_classifier is None:
            try:
                from focus_guard.core.classification.classifiers.domains.twitter import (
                    create_twitter_classifier
                )
                self._twitter_classifier = create_twitter_classifier()
                logger.info("Twitter classifier loaded")
            except Exception as e:
                logger.warning("Could not load Twitter classifier: %s", e)
        return self._twitter_classifier
    
    def _get_search_logger(self):
        """Lazy-load search logger."""
        if self._search_logger is None:
            try:
                from focus_guard.core.browser_v2.tab_server.search_logger import get_search_logger
                self._search_logger = get_search_logger()
                logger.info("Search logger loaded")
            except Exception as e:
                logger.warning("Could not load search logger: %s", e)
        return self._search_logger
    
    def _get_domain_classifier(self):
        """Lazy-load generic URL classifier (config-based rules + LLM)."""
        if self._domain_classifier is None:
            try:
                from focus_guard.core.classification.classifiers.generic import (
                    create_generic_url_classifier
                )
                self._domain_classifier = create_generic_url_classifier(use_llm=self.prefer_llm)
                logger.info("Generic URL classifier loaded (LLM=%s)", self.prefer_llm)
            except Exception as e:
                logger.warning("Could not load generic URL classifier: %s", e)
        return self._domain_classifier
    
    def _get_cache_key(self, domain: str, url: str, context: Dict[str, Any]) -> str:
        """Generate cache key from domain, URL, and relevant context."""
        # For YouTube, include video_id if available
        if "youtube.com" in domain or "youtu.be" in domain:
            video_id = context.get("video_id", "")
            if video_id:
                return f"youtube:video:{video_id}"
            # Fall back to URL path
            return f"youtube:url:{url}"
        
        # For search engines, use the search query as key
        search_engines = {
            "google.com": ("google", "q"),
            "google.co": ("google", "q"),
            "bing.com": ("bing", "q"),
            "duckduckgo.com": ("duckduckgo", "q"),
            "search.yahoo.com": ("yahoo", "p"),
            "ecosia.org": ("ecosia", "q"),
        }
        for engine_domain, (engine_name, query_param) in search_engines.items():
            if engine_domain in domain:
                from urllib.parse import urlparse, parse_qs
                try:
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    query = params.get(query_param, [''])[0]
                    if query:
                        return f"{engine_name}:query:{query}"
                except Exception:
                    pass
                return f"{engine_name}:url:{url}"
        
        # For other domains, use domain + path
        return f"domain:{domain}:{url}"
    
    def _check_cache(self, cache_key: str) -> Optional[ClassificationResult]:
        """Check if we have a valid cached result."""
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self._cache_ttl_seconds:
                logger.debug("Cache hit for %s", cache_key)
                return self._cache[cache_key]
            else:
                # Expired
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
        return None
    
    def _store_cache(self, cache_key: str, result: ClassificationResult) -> None:
        """Store result in cache."""
        # Manage cache size
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest entry
            oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()
    
    async def classify_async(
        self,
        domain: str,
        url: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """Classify content asynchronously.
        
        Args:
            domain: The domain being accessed
            url: The full URL
            context: Additional context (title, description, channel, etc.)
            
        Returns:
            ClassificationResult with category, usefulness, and confidence
        """
        start_time = time.time()
        context = context or {}
        
        # Check memory cache first, then persistent cache (4.2)
        cache_key = self._get_cache_key(domain, url, context)
        cached = self._check_cache(cache_key)
        if cached:
            return cached
        try:
            from .classification_cache_persistent import get_persistent_classification_cache
            persistent = get_persistent_classification_cache()
            cached_dict = persistent.get(cache_key)
            if cached_dict:
                cached = ClassificationResult.from_dict(cached_dict)
                self._store_cache(cache_key, cached)  # repopulate memory
                return cached
        except Exception as e:
            logger.debug("Persistent cache read failed: %s", e)

        result = None
        
        # Try domain-specific classifiers first
        if "youtube.com" in domain or "youtu.be" in domain:
            result = await self._classify_youtube(domain, url, context)
        elif "google.com" in domain or "google.co" in domain:
            result = await self._classify_google(domain, url, context)
        elif "reddit.com" in domain:
            result = await self._classify_reddit(domain, url, context)
        elif "twitter.com" in domain or "x.com" in domain:
            result = await self._classify_twitter(domain, url, context)
        elif "bing.com" in domain:
            result = await self._classify_search_engine(domain, url, context, "bing")
        elif "duckduckgo.com" in domain:
            result = await self._classify_search_engine(domain, url, context, "duckduckgo")
        elif "search.yahoo.com" in domain or "yahoo.com/search" in url:
            result = await self._classify_search_engine(domain, url, context, "yahoo")
        elif "ecosia.org" in domain:
            result = await self._classify_search_engine(domain, url, context, "ecosia")
        
        # If no domain-specific result, try generic classifier
        if result is None:
            result = await self._classify_generic(domain, url, context)
        
        # Fallback if all else fails
        if result is None:
            result = self._create_fallback_result(domain, url, context)
        
        # Record classification time
        result.classification_time_ms = (time.time() - start_time) * 1000
        
        # Cache the result (memory + persistent 4.2)
        self._store_cache(cache_key, result)
        try:
            from .classification_cache_persistent import get_persistent_classification_cache
            get_persistent_classification_cache().set(cache_key, result.to_dict())
        except Exception as e:
            logger.debug("Persistent cache write failed: %s", e)

        logger.info(
            "Classified %s: category=%s, usefulness=%s, confidence=%.2f, classifier=%s, time=%.1fms",
            domain, result.category, result.usefulness.value, 
            result.confidence, result.classifier_used, result.classification_time_ms
        )
        
        return result
    
    def classify(
        self,
        domain: str,
        url: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """Classify content synchronously.
        
        This is a convenience wrapper around classify_async for sync contexts.
        """
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, need to handle differently
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, 
                    self.classify_async(domain, url, context)
                )
                return future.result(timeout=self.llm_timeout + 1)
        except RuntimeError:
            # No event loop running, we can use asyncio.run directly
            return asyncio.run(self.classify_async(domain, url, context))
    
    async def _classify_youtube(
        self,
        domain: str,
        url: str,
        context: Dict[str, Any],
    ) -> Optional[ClassificationResult]:
        """Classify YouTube content using the YouTube classifier pipeline."""
        classifier = self._get_youtube_classifier()
        if classifier is None:
            return None
        
        try:
            from focus_guard.core.domain.models import Domain
            domain_obj = Domain(domain)
            
            # Add URL to context if not present
            if "url" not in context:
                context["url"] = url
            
            # Call the classifier
            classification = await classifier.classify(domain_obj, context)
            
            if classification is None:
                return None
            
            # Extract usefulness from metadata if available (LLM classifier provides this)
            usefulness_str = classification.metadata.get("usefulness", "NEUTRAL")
            try:
                usefulness = ContentUsefulness(usefulness_str.lower())
            except ValueError:
                usefulness = ContentUsefulness.NEUTRAL
            
            # Determine if distracting
            is_distracting = classification.metadata.get(
                "is_distracting", 
                usefulness == ContentUsefulness.DISTRACTION
            )
            
            return ClassificationResult(
                domain=domain,
                url=url,
                category=classification.category.name,
                usefulness=usefulness,
                confidence=classification.confidence,
                reason=classification.metadata.get("reason", ""),
                classifier_used=classification.metadata.get("classifier", "youtube"),
                is_distracting=is_distracting,
                content_type=classification.metadata.get("content_type", "video"),
                metadata=classification.metadata,
            )
            
        except Exception as e:
            logger.warning("YouTube classification failed: %s", e)
            return None
    
    async def _classify_google(
        self,
        domain: str,
        url: str,
        context: Dict[str, Any],
    ) -> Optional[ClassificationResult]:
        """Classify Google Search content using the Google classifier pipeline."""
        classifier = self._get_google_classifier()
        if classifier is None:
            return None
        
        try:
            from focus_guard.core.domain.models import Domain
            domain_obj = Domain(domain)
            
            # Add URL to context if not present
            if "url" not in context:
                context["url"] = url
            
            # Call the classifier
            classification = await classifier.classify(domain_obj, context)
            
            if classification is None:
                return None
            
            # Extract usefulness from metadata if available
            usefulness_str = classification.metadata.get("usefulness", "NEUTRAL")
            try:
                usefulness = ContentUsefulness(usefulness_str.lower())
            except ValueError:
                usefulness = ContentUsefulness.NEUTRAL
            
            # Determine if distracting
            is_distracting = classification.metadata.get(
                "is_distracting", 
                usefulness == ContentUsefulness.DISTRACTION
            )
            
            result = ClassificationResult(
                domain=domain,
                url=url,
                category=classification.category.name,
                usefulness=usefulness,
                confidence=classification.confidence,
                reason=classification.metadata.get("reason", ""),
                classifier_used=classification.metadata.get("classifier", "google"),
                is_distracting=is_distracting,
                content_type=classification.metadata.get("content_type", "search"),
                metadata=classification.metadata,
            )
            
            # Log the search to database
            self._log_search(
                url=url,
                search_engine="google",
                result=result,
                browser=context.get("browser", ""),
                tab_id=context.get("tab_id", ""),
            )
            
            return result
            
        except Exception as e:
            logger.warning("Google classification failed: %s", e)
            return None
    
    async def _classify_reddit(
        self,
        domain: str,
        url: str,
        context: Dict[str, Any],
    ) -> Optional[ClassificationResult]:
        """Classify Reddit content using the Reddit classifier pipeline."""
        classifier = self._get_reddit_classifier()
        if classifier is None:
            return None
        
        try:
            from focus_guard.core.domain.models import Domain
            domain_obj = Domain(domain)
            
            if "url" not in context:
                context["url"] = url
            
            classification = await classifier.classify(domain_obj, context)
            
            if classification is None:
                return None
            
            # Get usefulness from metadata
            metadata = classification.metadata or {}
            usefulness_str = metadata.get("usefulness", "DISTRACTION")
            try:
                usefulness = ContentUsefulness(usefulness_str.lower())
            except ValueError:
                usefulness = ContentUsefulness.DISTRACTION
            
            is_distracting = usefulness == ContentUsefulness.DISTRACTION
            
            return ClassificationResult(
                domain=domain,
                url=url,
                category=classification.category.name,
                usefulness=usefulness,
                confidence=classification.confidence,
                reason=metadata.get("reason", "") or f"Reddit content: {classification.category.name}",
                classifier_used=metadata.get("classifier", "reddit"),
                is_distracting=is_distracting,
                content_type="social_media",
                metadata=metadata,
            )
            
        except Exception as e:
            logger.warning("Reddit classification failed: %s", e)
            return None
    
    async def _classify_twitter(
        self,
        domain: str,
        url: str,
        context: Dict[str, Any],
    ) -> Optional[ClassificationResult]:
        """Classify Twitter/X content using the Twitter classifier pipeline."""
        classifier = self._get_twitter_classifier()
        if classifier is None:
            return None
        
        try:
            from focus_guard.core.domain.models import Domain
            domain_obj = Domain(domain)
            
            if "url" not in context:
                context["url"] = url
            
            classification = await classifier.classify(domain_obj, context)
            
            if classification is None:
                return None
            
            # Get usefulness from metadata
            metadata = classification.metadata or {}
            usefulness_str = metadata.get("usefulness", "DISTRACTION")
            try:
                usefulness = ContentUsefulness(usefulness_str.lower())
            except ValueError:
                usefulness = ContentUsefulness.DISTRACTION
            
            is_distracting = usefulness == ContentUsefulness.DISTRACTION
            
            return ClassificationResult(
                domain=domain,
                url=url,
                category=classification.category.name,
                usefulness=usefulness,
                confidence=classification.confidence,
                reason=metadata.get("reason", "") or f"Twitter content: {classification.category.name}",
                classifier_used=metadata.get("classifier", "twitter"),
                is_distracting=is_distracting,
                content_type="social_media",
                metadata=metadata,
            )
            
        except Exception as e:
            logger.warning("Twitter classification failed: %s", e)
            return None
    
    async def _classify_search_engine(
        self,
        domain: str,
        url: str,
        context: Dict[str, Any],
        engine_name: str,
    ) -> Optional[ClassificationResult]:
        """Classify search content from any search engine.
        
        Reuses Google classifier logic since most search engines have similar patterns.
        Supports: bing, duckduckgo, yahoo, ecosia
        """
        classifier = self._get_google_classifier()
        if classifier is None:
            return None
        
        try:
            from focus_guard.core.domain.models import Domain
            # Create a google.com domain object to use Google classifier
            domain_obj = Domain("google.com")
            
            if "url" not in context:
                context["url"] = url
            
            classification = await classifier.classify(domain_obj, context)
            
            if classification is None:
                return None
            
            usefulness_str = classification.metadata.get("usefulness", "NEUTRAL")
            try:
                usefulness = ContentUsefulness(usefulness_str.lower())
            except ValueError:
                usefulness = ContentUsefulness.NEUTRAL
            
            is_distracting = classification.metadata.get(
                "is_distracting", 
                usefulness == ContentUsefulness.DISTRACTION
            )
            
            result = ClassificationResult(
                domain=domain,
                url=url,
                category=classification.category.name,
                usefulness=usefulness,
                confidence=classification.confidence,
                reason=classification.metadata.get("reason", ""),
                classifier_used=f"{engine_name}_via_google",
                is_distracting=is_distracting,
                content_type=classification.metadata.get("content_type", "search"),
                metadata=classification.metadata,
            )
            
            # Log the search to database
            self._log_search(
                url=url,
                search_engine=engine_name,
                result=result,
                browser=context.get("browser", ""),
                tab_id=context.get("tab_id", ""),
            )
            
            return result
            
        except Exception as e:
            logger.warning("%s classification failed: %s", engine_name.title(), e)
            return None
    
    async def _classify_generic(
        self,
        domain: str,
        url: str,
        context: Dict[str, Any],
    ) -> Optional[ClassificationResult]:
        """Classify using the generic domain classifier."""
        classifier = self._get_domain_classifier()
        if classifier is None:
            return None
        
        try:
            from focus_guard.core.domain.models import Domain
            domain_obj = Domain(domain)
            if "url" not in context:
                context["url"] = url
            
            classification = await classifier.classify(domain_obj, context)
            
            if classification is None:
                return None
            
            # Map category to usefulness heuristically
            category_name = classification.category.name
            usefulness = self._infer_usefulness_from_category(category_name)
            metadata = classification.metadata or {}
            classifier_used = metadata.get("classifier", "generic_url")
            reason = metadata.get("reason") or f"Domain classified as {category_name}"
            
            return ClassificationResult(
                domain=domain,
                url=url,
                category=category_name,
                usefulness=usefulness,
                confidence=classification.confidence,
                reason=reason,
                classifier_used=classifier_used,
                is_distracting=usefulness == ContentUsefulness.DISTRACTION,
                content_type="page",
                metadata=metadata,
            )
            
        except Exception as e:
            logger.warning("Generic classification failed: %s", e)
            return None
    
    def _log_search(
        self,
        url: str,
        search_engine: str,
        result: ClassificationResult,
        browser: str = "",
        tab_id: str = "",
    ) -> None:
        """Log a search to the database."""
        try:
            search_logger = self._get_search_logger()
            if search_logger:
                search_logger.log_search(
                    url=url,
                    search_engine=search_engine,
                    classification_category=result.category,
                    classification_usefulness=result.usefulness.value,
                    is_distracting=result.is_distracting,
                    browser=browser,
                    tab_id=tab_id,
                )
        except Exception as e:
            logger.warning("Failed to log search: %s", e)
    
    def _infer_usefulness_from_category(self, category: str) -> ContentUsefulness:
        """Infer usefulness from category when LLM doesn't provide it."""
        category_usefulness = {
            "EDUCATION": ContentUsefulness.EDUCATIONAL,
            "PRODUCTIVITY": ContentUsefulness.EDUCATIONAL,
            "TECHNOLOGY": ContentUsefulness.ENRICHMENT,
            "NEWS": ContentUsefulness.ENRICHMENT,
            "ENTERTAINMENT": ContentUsefulness.DISTRACTION,
            "GAMING": ContentUsefulness.DISTRACTION,
            "SOCIAL_MEDIA": ContentUsefulness.DISTRACTION,
            "SHOPPING": ContentUsefulness.NEUTRAL,
            "ADULT": ContentUsefulness.DISTRACTION,
            "MALICIOUS": ContentUsefulness.DISTRACTION,
            "UNKNOWN": ContentUsefulness.NEUTRAL,
        }
        return category_usefulness.get(category, ContentUsefulness.NEUTRAL)
    
    def _create_fallback_result(
        self,
        domain: str,
        url: str,
        context: Dict[str, Any],
    ) -> ClassificationResult:
        """Create a fallback result when classification fails."""
        return ClassificationResult(
            domain=domain,
            url=url,
            category="UNKNOWN",
            usefulness=ContentUsefulness.NEUTRAL,
            confidence=0.0,
            reason="Classification unavailable - using default",
            classifier_used="fallback",
            is_distracting=False,
            content_type="unknown",
            metadata={"fallback": True},
        )


# Singleton instance
_classification_service: Optional[ClassificationService] = None


def get_classification_service() -> ClassificationService:
    """Get or create the singleton ClassificationService instance."""
    global _classification_service
    if _classification_service is None:
        _classification_service = ClassificationService()
    return _classification_service


def reset_classification_service() -> None:
    """Reset the singleton (for testing)."""
    global _classification_service
    _classification_service = None
