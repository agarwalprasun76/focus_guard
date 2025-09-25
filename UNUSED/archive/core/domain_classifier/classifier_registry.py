"""
Classifier Registry Module

This module defines the ClassifierRegistry, which manages all content classifiers
and handles the delegation of classification requests to the appropriate classifier.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from .base_classifier import ContentClassifier

# Set up logging
logger = logging.getLogger(__name__)


class ClassifierRegistry:
    """
    Registry for all content classifiers in the hierarchical classification system.
    
    The registry maintains a list of classifiers sorted by priority and delegates
    classification requests to the appropriate classifier based on capabilities
    and confidence levels.
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self.classifiers: List[ContentClassifier] = []
        self.default_confidence_threshold = 0.7
        
    def register(self, classifier: ContentClassifier) -> None:
        """
        Register a classifier with the registry.
        
        Args:
            classifier: The ContentClassifier instance to register
        """
        self.classifiers.append(classifier)
        # Sort by priority (highest first)
        self.classifiers.sort(key=lambda c: c.priority, reverse=True)
        logger.info(f"Registered classifier: {classifier.__class__.__name__} with priority {classifier.priority}")
        
    def classify(self, url: str, domain: str = None, 
                 confidence_threshold: float = None,
                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify a URL using the appropriate classifier, with support for
        embedded content and autoplay detection.
        
        Args:
            url: The URL to classify
            domain: Optional domain part (extracted from URL if not provided)
            confidence_threshold: Minimum confidence required to accept a classification
                                (uses default if not specified)
            metadata: Optional metadata about the URL to help with classification
                                
        Returns:
            Dict with standardized classification result including embedded content
            and autoplay context if detected
        """
        if not url:
            return self._create_error_result("Missing URL")
            
        # Extract domain if not provided
        if not domain:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                if not domain:
                    return self._create_error_result("Invalid URL format")
            except Exception as e:
                logger.error(f"Error parsing URL {url}: {str(e)}")
                return self._create_error_result(f"Error parsing URL: {str(e)}")
                
        # Use provided threshold or default
        threshold = confidence_threshold or self.default_confidence_threshold
        
        # Shared metadata that can be enriched by each classifier
        # Start with the provided metadata if available
        shared_metadata = metadata.copy() if metadata else {}
        
        # Try each classifier in priority order
        classification_attempts = []
        
        for classifier in self.classifiers:
            try:
                if classifier.can_classify(url, domain, shared_metadata):
                    logger.debug(f"Using {classifier.__class__.__name__} for {url}")
                    result = classifier.classify(url, domain, shared_metadata)
                    
                    # Add to attempts for logging/debugging
                    classification_attempts.append({
                        "classifier": classifier.__class__.__name__,
                        "confidence": result.get("confidence", 0),
                        "classification": result.get("classification", "unknown")
                    })
                    
                    # Return if confidence meets threshold
                    try:
                        # Debug the confidence value before comparison
                        confidence_val = result.get("confidence", 0)
                        logger.debug(f"Confidence value: {confidence_val}, type: {type(confidence_val)}")
                        logger.debug(f"Threshold value: {threshold}, type: {type(threshold)}")
                        
                        if isinstance(confidence_val, dict):
                            logger.error(f"CRITICAL ERROR: Confidence is a dict instead of a float: {confidence_val}")
                            # Try to extract a usable value or use a default
                            confidence_val = 0.6
                            result["confidence"] = confidence_val
                            
                        # Safe comparison with proper type conversion
                        logger.debug(f"Comparing confidence {confidence_val} >= threshold {threshold}")
                        if float(confidence_val) >= float(threshold):
                            logger.debug(f"Confidence meets threshold! Returning result: {result}")
                            # Add metadata about the classifier used
                            if "metadata" not in result:
                                result["metadata"] = {}
                                
                            # Handle embedded content markers
                            if result.get("embedded") or (metadata and metadata.get("embedded_on_domain")):
                                result["is_embedded"] = True
                                result["embedded_on_domain"] = result.get("embedded_on") or metadata.get("embedded_on_domain")
                                logger.info(f"Classified embedded content on {result.get('embedded_on')}")
                            
                            # Handle autoplay detection
                            if result.get("has_autoplay"):
                                result["has_autoplay"] = True
                                result["autoplay_info"] = result.get("autoplay_info", {})
                                logger.info(f"Detected autoplay content in classification result")
                                    
                            result["metadata"]["classifier_name"] = classifier.__class__.__name__
                            result["metadata"]["classification_attempts"] = classification_attempts
                            return result
                        else:
                            logger.debug(f"Confidence below threshold. Result not used: {result}")
                    except Exception as e:
                        logger.error(f"Error comparing confidence to threshold: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        # Continue with default values
                        result["confidence"] = 0.6
                        if "metadata" not in result:
                            result["metadata"] = {}
                        
                        # Continue with the classification despite the comparison error
                        logger.warning(f"Continuing with classification despite comparison error")
                        
                        # Handle embedded content markers
                        if result.get("embedded") or (metadata and metadata.get("embedded_on_domain")):
                            result["is_embedded"] = True
                            result["embedded_on_domain"] = result.get("embedded_on") or metadata.get("embedded_on_domain")
                            logger.info(f"Classified embedded content on {result.get('embedded_on')}")
                        
                        # Handle autoplay detection
                        if result.get("has_autoplay"):
                            result["has_autoplay"] = True
                            result["autoplay_info"] = result.get("autoplay_info", {})
                            logger.info(f"Detected autoplay content in classification result")
                            
                        result["metadata"]["classifier_name"] = classifier.__class__.__name__
                        result["metadata"]["classification_attempts"] = classification_attempts
                        return result
                        
            except Exception as e:
                logger.error(f"Error in classifier {classifier.__class__.__name__} for {url}: {str(e)}")
                # Print full traceback for better debugging
                import traceback
                full_tb = traceback.format_exc()
                logger.error(f"Full traceback: {full_tb}")
                
                # Try to get information about the variables involved
                try:
                    # Get the result structure if available to inspect confidence
                    result_info = "Result not available"
                    if 'result' in locals():
                        result_info = f"Result keys: {result.keys() if hasattr(result, 'keys') else 'No keys'}, "
                        result_info += f"Confidence: {result.get('confidence', 'N/A')}, "
                        result_info += f"Type: {type(result.get('confidence', None))}"
                    logger.error(f"Result info: {result_info}")
                except:
                    logger.error("Could not retrieve result info")
                
                classification_attempts.append({
                    "classifier": classifier.__class__.__name__,
                    "error": str(e),
                    "traceback": full_tb
                })
        
        # If we get here, no classifier was confident enough
        logger.debug(f"No classifier met confidence threshold. Using fallback result")
        return {
            "classification": "neutral",
            "reason": "No classifier was confident enough",
            "confidence": 0.5,
            "metadata": {
                "classification_attempts": classification_attempts
            },
            "timestamp": None  # Will be filled by create_result
        }
        
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create an error result."""
        return {
            "classification": "error",
            "reason": error_message,
            "confidence": 0.0,
            "metadata": {},
            "timestamp": None  # Will be filled by create_result
        }


# Singleton instance
classifier_registry = ClassifierRegistry()
