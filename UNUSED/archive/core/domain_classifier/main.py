"""
Main Initialization Module for Hierarchical Classifier

This module initializes the hierarchical classification system by registering
all available specialized classifiers with the classifier registry.
"""

import logging
from .classifier_registry import classifier_registry
from .hierarchical_classifier import link_classifier
from .classifiers.entertainment_classifier import entertainment_classifier
from .classifiers.publication_classifier import publication_classifier
from .classifiers.google_drive_classifier import google_drive_classifier
from .classifiers.youtube_classifier import youtube_classifier
from .classifiers.keyword_classifier import keyword_classifier

# Set up logging
logger = logging.getLogger(__name__)


def initialize_classification_system():
    """Initialize the hierarchical classification system by registering all classifiers."""
    logger.info("Initializing hierarchical classification system...")
    
    # Register classifiers in priority order (highest priority first)
    # More specialized classifiers should have higher priority
    classifier_registry.register(google_drive_classifier)  # Priority: 90
    classifier_registry.register(youtube_classifier)       # Priority: 85
    classifier_registry.register(publication_classifier)   # Priority: 80
    classifier_registry.register(entertainment_classifier) # Priority: 70
    classifier_registry.register(keyword_classifier)       # Priority: 30
    
    logger.info(f"Registered {len(classifier_registry.classifiers)} classifiers")
    return link_classifier


# Initialize the system when the module is imported
initialized_classifier = initialize_classification_system()