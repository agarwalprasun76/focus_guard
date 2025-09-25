from core.domain_classifier.classifiers.youtube_classifier import YouTubeClassifier
from core.domain_classifier.classifiers.entertainment_classifier import EntertainmentClassifier
from core.domain_classifier.classifiers.keyword_classifier import KeywordClassifier
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
    confidence = result.get('confidence', 0)
    classification = result.get('classification', 'unknown')
    reason = result.get('reason', 'No reason provided')
    
    # For JSON results, extract just the key information
    return f"{prefix}{classification.upper()} ({confidence:.2f}): {reason}"

# YouTube URL to test - an educational video about quadratic equations
test_url = "https://youtu.be/vVRGOSV4dmQ"
video_id = "vVRGOSV4dmQ"

# Prepare mock metadata for educational content
mock_metadata = {
    "title": "Quadratic Equations | Solve by factoring | Free Math Videos",
    "description": "Learn how to solve quadratic equations by factoring. This educational math tutorial explains step-by-step solutions.",
    "channel": "Math Education Channel",
    "tags": ["mathematics", "education", "tutorial", "quadratic equations", "algebra"],
    "categories": ["Education"]
}
domain = urlparse(test_url).netloc

# Test with YouTubeClassifier directly
youtube_classifier = YouTubeClassifier()
logger.info("=== TEST 1: YouTubeClassifier Only ===")

# Test without metadata first (URL-based classification)
result_without_metadata = youtube_classifier.classify(test_url, domain)
logger.info("TEST 1.1 - WITHOUT Metadata: " + format_result(result_without_metadata))

# Test with mock educational metadata
result_with_mock_metadata = youtube_classifier.classify(test_url, domain, metadata=mock_metadata)
logger.info("TEST 1.2 - WITH MOCK Metadata: " + format_result(result_with_mock_metadata))

# Now test with REAL fetched metadata
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
        result_with_real_metadata = youtube_classifier.classify(test_url, domain, metadata=real_metadata)
        logger.info("TEST 2.1 - WITH REAL Metadata: " + format_result(result_with_real_metadata))
    else:
        logger.warning(f"✗ Could not fetch real metadata: {real_metadata.get('error', 'Unknown error')}")
except Exception as e:
    logger.error(f"✗ Error during real metadata fetching: {str(e)}")

# Test with the full ClassifierRegistry
logger.info("\n=== TEST 3: Full ClassifierRegistry Testing ===")
registry = ClassifierRegistry()

# Check if any classifiers were registered
if not registry.classifiers:
    # Manually register our classifiers
    registry.register(YouTubeClassifier())
    registry.register(EntertainmentClassifier())
    registry.register(KeywordClassifier())
    logger.info("✓ Registered 3 classifiers in priority order")
else:
    logger.info(f"✓ Found {len(registry.classifiers)} pre-registered classifiers")

# Show a summary of registered classifiers that can classify this URL
classifiable_count = 0
for classifier in registry.classifiers:
    if classifier.can_classify(test_url, domain):
        classifiable_count += 1
logger.info(f"• {classifiable_count} of {len(registry.classifiers)} classifiers can handle this URL")

# Testing each classifier individually WITH METADATA (but show more concise results)
classifier_results = []
for classifier in registry.classifiers:
    if classifier.can_classify(test_url, domain):
        result = classifier.classify(test_url, domain, metadata=mock_metadata)
        classifier_results.append({
            "name": classifier.__class__.__name__,
            "classification": result['classification'],
            "confidence": result['confidence'],
            "reason": result['reason']
        })

# Display individual classifier results in a concise format
if classifier_results:
    logger.info("TEST 3.1 - Individual Classifiers with Mock Metadata:")
    for idx, res in enumerate(classifier_results, 1):
        logger.info(f"   {idx}. {res['name']}: {res['classification'].upper()} ({res['confidence']:.2f}) - {res['reason']}")
else:
    logger.info("No classifiers could classify this URL")

# Full registry classification tests

# 1. WITHOUT metadata first (URL-based classification)
result_without_metadata = registry.classify(test_url, domain)
logger.info("\nTEST 3.2 - Full Registry WITHOUT Metadata:")
logger.info("   " + format_result(result_without_metadata))

# 2. WITH educational metadata
shared_metadata = mock_metadata.copy()
result_with_metadata = registry.classify(test_url, domain, metadata=shared_metadata)
logger.info("\nTEST 3.3 - Full Registry WITH Metadata:")
logger.info("   " + format_result(result_with_metadata))

# Show which classifier won in each case
logger.info("\n=== TEST RESULTS SUMMARY ===")
without_meta_classifier = result_without_metadata['metadata'].get('classifier', 'Unknown')
with_meta_classifier = result_with_metadata['metadata'].get('classifier', 'Unknown')
logger.info(f"WITHOUT Metadata: {without_meta_classifier} classified as {result_without_metadata['classification'].upper()}")
logger.info(f"WITH Metadata:    {with_meta_classifier} classified as {result_with_metadata['classification'].upper()}")

# Compare the confidence scores
without_confidence = result_without_metadata.get('confidence', 0)
with_confidence = result_with_metadata.get('confidence', 0)

if with_confidence > without_confidence:
    logger.info(f"\n✓ SUCCESS: Metadata improved classification confidence by {(with_confidence - without_confidence):.2f}")
elif with_confidence < without_confidence:
    logger.info(f"\n! UNEXPECTED: Metadata decreased classification confidence by {(without_confidence - with_confidence):.2f}")
else:
    logger.info("\n! NEUTRAL: Metadata did not change classification confidence")
