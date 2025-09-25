#!/usr/bin/env python3
"""
Test script to check if LLM classifier can be enabled.
"""

import logging
from focus_guard.core.classification.classifiers.domains.youtube import create_youtube_classifier

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_llm_classifier():
    """Test if LLM classifier can be created."""
    
    print("=== Testing LLM Classifier Creation ===")
    
    # Test with LLM enabled
    try:
        print("Attempting to create YouTube classifier with LLM enabled...")
        youtube_classifier = create_youtube_classifier(use_llm=True, use_rules=True)
        print(f"SUCCESS! Created classifier: {youtube_classifier}")
        print(f"Classifier name: {youtube_classifier.name}")
        
        # Check what classifiers are inside
        if hasattr(youtube_classifier, '_classifiers'):
            print(f"Internal classifiers: {youtube_classifier._classifiers}")
            for i, classifier in enumerate(youtube_classifier._classifiers):
                print(f"  {i}: {classifier} (name: {getattr(classifier, 'name', 'unknown')})")
        
    except Exception as e:
        print(f"FAILED to create LLM classifier: {e}")
        import traceback
        traceback.print_exc()
        
        print("\nFalling back to rule-based only...")
        try:
            youtube_classifier = create_youtube_classifier(use_llm=False, use_rules=True)
            print(f"Rule-based classifier created: {youtube_classifier}")
        except Exception as e2:
            print(f"Even rule-based failed: {e2}")

if __name__ == "__main__":
    test_llm_classifier()
