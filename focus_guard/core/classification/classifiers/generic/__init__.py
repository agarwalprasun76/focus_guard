"""
Generic classifiers for any URL/domain.

These classifiers work as fallbacks when no domain-specific classifier
(like YouTube or Google) is available.
"""

from .url_classifier import (
    RuleBasedURLClassifier,
    URLPatternRule,
    create_url_rules_classifier,
)

from .url_llm_classifier import (
    LLMBasedURLClassifier,
    create_url_llm_classifier,
)

from .url_composite_classifier import (
    GenericURLClassifier,
    get_generic_url_classifier,
    create_generic_url_classifier,
)

__all__ = [
    'RuleBasedURLClassifier',
    'URLPatternRule',
    'create_url_rules_classifier',
    'LLMBasedURLClassifier',
    'create_url_llm_classifier',
    'GenericURLClassifier',
    'get_generic_url_classifier',
    'create_generic_url_classifier',
]
