#!/usr/bin/env python3
"""
Test script to verify LLM YouTube classification with API key.
"""

import os
import asyncio
import logging
from focus_guard.core.classification.classifiers.domains.youtube import create_youtube_classifier
from focus_guard.core.domain.models import Domain

# Check for API key in environment
if 'OPENAI_API_KEY' not in os.environ:
    print("ERROR: OPENAI_API_KEY environment variable not set")
    print("Please set it with: setx OPENAI_API_KEY \"your-api-key-here\"")
    exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_llm_enabled():
    """Test LLM YouTube classification with API key."""
    
    print("=== Testing LLM-Enabled YouTube Classification ===")
    
    # Check if API key is available
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        print(f"OpenAI API Key found: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("No OpenAI API Key found in environment")
        return
    
    # Create YouTube classifier with LLM enabled
    try:
        youtube_classifier = create_youtube_classifier(use_llm=True, use_rules=True)
        print(f"Created classifier: {youtube_classifier.name}")
        
        # Check internal classifiers
        if hasattr(youtube_classifier, 'classifiers'):
            print(f"Internal classifiers: {len(youtube_classifier.classifiers)}")
            for i, classifier in enumerate(youtube_classifier.classifiers):
                print(f"  {i}: {classifier.__class__.__name__} (name: {getattr(classifier, 'name', 'unknown')})")
        
        # Test domain and context
        domain = Domain("youtube.com")
        
        # Test with entertainment content
        entertainment_context = {
            'url': 'https://www.youtube.com/watch?v=abc123',
            'title': 'EPIC FAILS Compilation 2024 - Funny Moments',
            'timestamp': '2025-08-28T20:00:00',
            'domain': 'youtube.com'
        }
        
        print(f"\n--- Testing Entertainment Content ---")
        print(f"Title: {entertainment_context['title']}")
        result = await youtube_classifier.classify(domain, entertainment_context)
        if result:
            print(f"Category: {result.category}")
            print(f"Confidence: {result.confidence}")
            print(f"Classifier used: {result.metadata.get('classifier', 'unknown')}")
            print(f"Method: {result.metadata.get('method', 'unknown')}")
        
        # Test with educational content
        education_context = {
            'url': 'https://www.youtube.com/watch?v=302eJ3TzJQU',
            'title': 'Advanced Geometry Tutorial - Understanding Complex Theorems',
            'timestamp': '2025-08-28T20:00:00',
            'domain': 'youtube.com'
        }
        
        print(f"\n--- Testing Educational Content ---")
        print(f"Title: {education_context['title']}")
        result = await youtube_classifier.classify(domain, education_context)
        if result:
            print(f"Category: {result.category}")
            print(f"Confidence: {result.confidence}")
            print(f"Classifier used: {result.metadata.get('classifier', 'unknown')}")
            print(f"Method: {result.metadata.get('method', 'unknown')}")
            
    except Exception as e:
        print(f"Error testing LLM classification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_enabled())
