"""
Debug script to trace the initialization of OpenAI and LLM classifiers
"""

import traceback
from core.logger.logger import get_logger
from core.utils.text_utils import sanitize_console_output

# Set up logging
logger = get_logger('tests.debug_classifier')

from core.domain_classifier.classifiers.youtube_classifier import (
    LLM_CLASSIFIER_AVAILABLE, 
    OPENAI_CLASSIFIER_AVAILABLE
)

# Logger is already set up above

# First check the availability flags
logger.info("=== Classifier Availability Flags ===")
logger.info(f"LLM Classifier Available: {LLM_CLASSIFIER_AVAILABLE}")
logger.info(f"OpenAI Classifier Available: {OPENAI_CLASSIFIER_AVAILABLE}")

# Try to import and initialize the classifiers directly
logger.info("=== Testing OpenAI Classifier ===")
try:
    from core.domain_classifier.classifiers.llm_classifier.openai_classifier import (
        OpenAIYouTubeClassifier, 
        OpenAIBaseClassifier,
        OPENAI_AVAILABLE
    )
    logger.info(f"OpenAI SDK Available: {OPENAI_AVAILABLE}")
    
    logger.info("Attempting to initialize OpenAIYouTubeClassifier...")
    try:
        classifier = OpenAIYouTubeClassifier()
        logger.info(sanitize_console_output("✓ OpenAI classifier initialized successfully!"))
        logger.info(f"Model: {classifier.model}")
    except Exception as e:
        logger.error(sanitize_console_output(f"✗ Failed to initialize OpenAI classifier: {e}"))
        logger.error(traceback.format_exc())
except ImportError as e:
    logger.error(sanitize_console_output(f"✗ Failed to import OpenAI classifier: {e}"))

logger.info("=== Testing LLM Classifier ===")
try:
    from core.domain_classifier.classifiers.llm_classifier.llm_youtube_classifier import (
        LLMYouTubeClassifier
    )
    from core.domain_classifier.classifiers.llm_classifier.llm_base_classifier import (
        LLM_AVAILABLE, TRANSFORMERS_AVAILABLE, TORCH_AVAILABLE, BNB_AVAILABLE
    )
    
    logger.info(f"LLM Available: {LLM_AVAILABLE}")
    logger.info(f"Transformers Available: {TRANSFORMERS_AVAILABLE}")
    logger.info(f"PyTorch Available: {TORCH_AVAILABLE}")
    logger.info(f"BitsAndBytes Available: {BNB_AVAILABLE}")
    
    logger.info("Attempting to initialize LLMYouTubeClassifier...")
    try:
        classifier = LLMYouTubeClassifier()
        logger.info(sanitize_console_output("✓ LLM classifier initialized successfully!"))
    except Exception as e:
        logger.error(sanitize_console_output(f"✗ Failed to initialize LLM classifier: {e}"))
        logger.error(traceback.format_exc())
except ImportError as e:
    logger.error(sanitize_console_output(f"✗ Failed to import LLM classifier: {e}"))
