"""
LLM-based content classifiers for FocusGuard

This package provides classifiers that use either:
1. Small, locally-run language models
2. API-based models like OpenAI's GPT

to determine if content is educational, entertainment, or neutral.
"""

# Local LLM classifiers
from .llm_base_classifier import LLMBaseClassifier
from .llm_youtube_classifier import LLMYouTubeClassifier
from .llm_domain_classifier import LLMDomainClassifier

# Set default availability
OPENAI_AVAILABLE = False

# Define minimal exports
__all__ = ['LLMBaseClassifier', 'LLMYouTubeClassifier', 'LLMDomainClassifier']

# Try to import OpenAI classifiers if available
try:
    import openai  # Try importing the library first
    from .openai_classifier import OpenAIBaseClassifier, OpenAIYouTubeClassifier
    from .openai_domain_classifier import OpenAIDomainClassifier
    OPENAI_AVAILABLE = True
    __all__ = ['LLMBaseClassifier', 'LLMYouTubeClassifier', 'LLMDomainClassifier',
               'OpenAIBaseClassifier', 'OpenAIYouTubeClassifier', 'OpenAIDomainClassifier']
except ImportError as e:
    # OpenAI SDK may not be installed
    print(f"[INFO] OpenAI integration disabled: {e}")
