"""
Composite Google Search classifier.

Combines rule-based and LLM-based classification for Google Search,
following the same pattern as the YouTube classifier.

Priority:
1. LLM classifier (for nuanced understanding of search intent)
2. Rule-based classifier (fast fallback)
"""

import logging
from typing import Dict, Any, Optional, List

from focus_guard.core.domain.models import Domain, Classification

from .base import BaseDomainClassifier
from .google_rules import RuleBasedGoogleClassifier, create_google_rules_classifier
from .google_llm import LLMBasedGoogleClassifier, create_google_llm_classifier

logger = logging.getLogger(__name__)


class GoogleClassifier(BaseDomainClassifier):
    """Composite classifier for Google Search and related services.
    
    Tries LLM first for nuanced classification, falls back to rules.
    """
    
    GOOGLE_DOMAINS = [
        'google.com', 'www.google.com',
        'google.co.uk', 'google.ca', 'google.com.au',
        'google.co.in', 'google.de', 'google.fr',
    ]
    
    def __init__(
        self,
        classifiers: Optional[List[BaseDomainClassifier]] = None,
        use_llm: bool = True,
    ):
        """Initialize the Google classifier.
        
        Args:
            classifiers: Optional list of classifiers to use.
            use_llm: Whether to include LLM classifier (default True).
        """
        super().__init__(name="google_composite")
        
        if classifiers is not None:
            self._classifiers = classifiers
        else:
            self._classifiers = []
            
            # Try to add LLM classifier first
            if use_llm:
                llm_classifier = create_google_llm_classifier()
                if llm_classifier:
                    self._classifiers.append(llm_classifier)
                    logger.info("Google LLM classifier enabled")
                else:
                    logger.warning("Google LLM classifier not available")
            
            # Always add rule-based classifier as fallback
            self._classifiers.append(create_google_rules_classifier())
    
    def _is_google_domain(self, domain: str) -> bool:
        """Check if domain is a Google domain."""
        domain_lower = domain.lower()
        return any(
            domain_lower == g or domain_lower.endswith('.' + g)
            for g in self.GOOGLE_DOMAINS
        )
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify a Google domain using available classifiers.
        
        Tries each classifier in order until one returns a result.
        """
        # Only handle Google domains
        if not self._is_google_domain(domain.value):
            return None
        
        for classifier in self._classifiers:
            try:
                result = await classifier.classify(domain, context)
                if result is not None:
                    logger.debug(
                        f"Google classified by {classifier.name}: "
                        f"{result.category} ({result.confidence:.2f})"
                    )
                    return result
            except Exception as e:
                logger.warning(
                    f"Google classifier {classifier.name} failed: {e}"
                )
                continue
        
        return None
    
    @classmethod
    def create_default(cls, use_llm: bool = True) -> 'GoogleClassifier':
        """Create a default Google classifier with standard configuration."""
        return cls(use_llm=use_llm)
    
    @classmethod
    def create_rules_only(cls) -> 'GoogleClassifier':
        """Create a Google classifier with only rule-based classification."""
        return cls(use_llm=False)


# Singleton instance for easy import
_default_classifier: Optional[GoogleClassifier] = None


def get_google_classifier() -> GoogleClassifier:
    """Get the default Google classifier instance."""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = GoogleClassifier.create_default()
    return _default_classifier


def create_google_classifier(use_llm: bool = True) -> GoogleClassifier:
    """Factory function to create a Google classifier."""
    return GoogleClassifier(use_llm=use_llm)
