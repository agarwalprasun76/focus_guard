from core.domain_classifier.classifiers.youtube_classifier import YouTubeClassifier, ClassificationMethod
from core.domain_classifier.classifier_registry import ClassifierRegistry
from core.domain_classifier.metadata import metadata_fetcher
from urllib.parse import urlparse

# Completely disable all other loggers and set up our own clean logging
import logging

# Silence all other loggers including the root logger
logging.getLogger().setLevel(logging.ERROR)  # Set root logger to ERROR level
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.ERROR)

# Create our clean logger
logger = logging.getLogger("youtube_test")
logger.setLevel(logging.INFO)
logger.propagate = False

# Add a handler with our desired format
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(message)s'))  # Simple, no-prefix format
logger.addHandler(handler)

# Helper function for cleaner output of classification results
def format_result(result, prefix=""):
    """Format a classification result for cleaner output"""
    # Handle ClassificationResult objects (new format)
    if hasattr(result, 'decision') and hasattr(result, 'score'):
        # This is the ClassificationResult object from utils.py
        classification = result.decision
        confidence = result.score
        reason = getattr(result, 'reason', 'No reason provided')
    # Handle objects with classification/confidence properties (alternate format)
    elif hasattr(result, 'classification') and hasattr(result, 'confidence'):
        classification = result.classification
        confidence = result.confidence
        reason = getattr(result, 'reason', 'No reason provided')
    # Handle dictionary format (old format)
    elif isinstance(result, dict):
        confidence = result.get('confidence', 0)
        classification = result.get('classification', 'unknown')
        reason = result.get('reason', 'No reason provided')
    else:
        return f"{prefix}UNKNOWN (0.0): Unable to process result format"
    
    # Format the result for output
    return f"{prefix}{classification.upper()} ({confidence:.2f}): {reason}"

# YouTube URL to test - Python Tutorial
test_url = "https://www.youtube.com/watch?v=W2twcSFYlt0"
domain = urlparse(test_url).netloc
video_id = "W2twcSFYlt0"

logger.info(f"Testing URL: {test_url}")
logger.info(f"Video ID: {video_id}")
logger.info("=" * 60)

# Test with different classification methods
logger.info("=== TEST 1: Classification Method Comparison ===")

# Test rule-based classification
rule_classifier = YouTubeClassifier(ClassificationMethod.RULE_BASED)
rule_result = rule_classifier.classify(test_url, domain)
logger.info("RULE-BASED: " + format_result(rule_result))

# Test LLM-based classification if available
llm_classifier = YouTubeClassifier(ClassificationMethod.LLM)
try:
    llm_result = llm_classifier.classify(test_url, domain)
    logger.info("LLM-BASED: " + format_result(llm_result))
except Exception as e:
    logger.info(f"LLM-BASED: Not available - {str(e)}")

# Test OpenAI classification if available
openai_classifier = YouTubeClassifier(ClassificationMethod.OPENAI)
try:
    openai_result = openai_classifier.classify(test_url, domain)
    logger.info("OPENAI-BASED: " + format_result(openai_result))
except Exception as e:
    logger.info(f"OPENAI-BASED: Not available - {str(e)}")

# Test AUTO classification (should pick the best available)
auto_classifier = YouTubeClassifier(ClassificationMethod.AUTO)
auto_result = auto_classifier.classify(test_url, domain)
logger.info("AUTO-SELECTED: " + format_result(auto_result))
# Access metadata from ClassificationResult object
if hasattr(auto_result, 'metadata'):
    if isinstance(auto_result.metadata, dict):
        logger.info(f"AUTO selected method: {auto_result.metadata.get('classification_method', 'unknown')}")
    else:
        logger.info(f"AUTO selected method: {getattr(auto_result.metadata, 'classification_method', 'unknown')}")
elif isinstance(auto_result, dict) and 'metadata' in auto_result:
    logger.info(f"AUTO selected method: {auto_result.get('metadata', {}).get('classification_method', 'unknown')}")
else:
    logger.info("AUTO selected method: unknown")

# Test with real metadata
logger.info("\n=== TEST 2: Using REAL Fetched Metadata ===")
try:
    # Attempt to fetch real metadata using our metadata fetcher
    real_metadata = metadata_fetcher.fetch_metadata_for_youtube(video_id)
    
    if real_metadata and 'error' not in real_metadata:
        logger.info("✓ Successfully fetched real metadata")
        logger.info(f"• Title: {real_metadata.get('title', 'Unknown')}")
        logger.info(f"• Channel: {real_metadata.get('channel', 'Unknown')}")
        
        # Show tags in a more compact form
        tags = real_metadata.get('tags', [])
        if tags:
            logger.info(f"• Tags: {', '.join(tags[:5])}" + (", ..." if len(tags) > 5 else ""))
        
        # Classify with real metadata
        result_with_real_metadata = auto_classifier.classify(test_url, domain, metadata=real_metadata)
        logger.info("\nClassification with REAL Metadata: " + format_result(result_with_real_metadata))
    else:
        logger.warning(f"✗ Could not fetch real metadata: {real_metadata.get('error', 'Unknown error')}")
except Exception as e:
    logger.error(f"✗ Error during real metadata fetching: {str(e)}")
