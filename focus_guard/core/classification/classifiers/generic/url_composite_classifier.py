"""
Composite generic URL classifier.

Combines rule-based and LLM-based classification for any URL,
following the same pattern as YouTube and Google classifiers.

Priority:
1. Rule-based classifier (fast, from config)
2. LLM classifier (for uncertain cases)
"""

import logging
from typing import Dict, Any, Optional, List

from focus_guard.core.domain.models import Domain, Classification

from focus_guard.core.classification.classifiers.domains.base import BaseDomainClassifier
from .url_classifier import RuleBasedURLClassifier, create_url_rules_classifier
from .url_llm_classifier import LLMBasedURLClassifier, create_url_llm_classifier

logger = logging.getLogger(__name__)


def _context_float(context: Optional[Dict[str, Any]], key: str, default: float) -> float:
    """Safely read float values from context."""
    if not context or key not in context:
        return default
    try:
        return float(context[key])
    except (TypeError, ValueError):
        return default


class GenericURLClassifier(BaseDomainClassifier):
    """Composite classifier for any URL.
    
    Tries rules first (fast), then LLM for uncertain cases.
    """
    
    # Confidence threshold below which we try LLM
    LLM_THRESHOLD = 0.7
    
    def __init__(
        self,
        use_llm: bool = True,
        llm_for_uncertain_only: bool = True,
    ):
        """Initialize the generic URL classifier.
        
        Args:
            use_llm: Whether to include LLM classifier.
            llm_for_uncertain_only: If True, only use LLM when rules are uncertain.
        """
        super().__init__(name="generic_url_composite")
        
        self.use_llm = use_llm
        self.llm_for_uncertain_only = llm_for_uncertain_only
        
        # Always have rule-based classifier
        self._rules_classifier = create_url_rules_classifier()
        
        # Lazy-load LLM classifier
        self._llm_classifier: Optional[LLMBasedURLClassifier] = None
    
    def _get_llm_classifier(self) -> Optional[LLMBasedURLClassifier]:
        """Lazy-load LLM classifier."""
        if not self.use_llm:
            return None
        
        if self._llm_classifier is None:
            self._llm_classifier = create_url_llm_classifier()
            if self._llm_classifier:
                logger.info("Generic URL LLM classifier loaded")
            else:
                logger.warning("Could not load generic URL LLM classifier")
        
        return self._llm_classifier
    
    def reload_config(self) -> None:
        """Reload configuration for rule-based classifier."""
        self._rules_classifier.reload_config()
        logger.info("Generic URL classifier config reloaded")
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify a URL using available classifiers.
        
        Strategy:
        1. Try rule-based classifier first (fast)
        2. If rules return high confidence, use that result
        3. If rules are uncertain or return None, try LLM
        """
        force_llm = bool((context or {}).get("force_llm", False))
        rule_confidence_threshold = _context_float(context, "rule_confidence_threshold", self.LLM_THRESHOLD)

        if force_llm:
            llm_classifier = self._get_llm_classifier()
            if llm_classifier:
                try:
                    llm_result = await llm_classifier.classify(domain, context)
                    if llm_result is not None:
                        logger.debug(
                            "URL force-classified by LLM: %s (%s, %.2f)",
                            domain.value, llm_result.category, llm_result.confidence
                        )
                        return llm_result
                except Exception as e:
                    logger.warning("Forced LLM classification failed: %s", e)

        # Try rules first
        rules_result = await self._rules_classifier.classify(domain, context)
        
        if rules_result is not None:
            # If high confidence, use rules result
            if rules_result.confidence >= rule_confidence_threshold:
                logger.debug(
                    "URL classified by rules: %s (%s, %.2f)",
                    domain.value, rules_result.category, rules_result.confidence
                )
                return rules_result
            
            # If llm_for_uncertain_only is False, still use rules
            if not self.llm_for_uncertain_only:
                return rules_result
        
        # Try LLM for uncertain cases
        llm_classifier = self._get_llm_classifier()
        if llm_classifier:
            try:
                llm_result = await llm_classifier.classify(domain, context)
                if llm_result is not None:
                    logger.debug(
                        "URL classified by LLM: %s (%s, %.2f)",
                        domain.value, llm_result.category, llm_result.confidence
                    )
                    return llm_result
            except Exception as e:
                logger.warning("LLM classification failed: %s", e)
        
        # Fall back to rules result if we have one
        if rules_result is not None:
            return rules_result
        
        # No classification available
        return None
    
    @classmethod
    def create_default(cls, use_llm: bool = True) -> 'GenericURLClassifier':
        """Create a default generic URL classifier."""
        return cls(use_llm=use_llm)
    
    @classmethod
    def create_rules_only(cls) -> 'GenericURLClassifier':
        """Create a classifier with only rule-based classification."""
        return cls(use_llm=False)


# Singleton instance
_default_classifier: Optional[GenericURLClassifier] = None


def get_generic_url_classifier() -> GenericURLClassifier:
    """Get the default generic URL classifier instance."""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = GenericURLClassifier.create_default()
    return _default_classifier


def create_generic_url_classifier(use_llm: bool = True) -> GenericURLClassifier:
    """Factory function to create a generic URL classifier."""
    return GenericURLClassifier(use_llm=use_llm)
