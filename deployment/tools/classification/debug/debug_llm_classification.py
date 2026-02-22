"""Test script for LLM-enabled YouTube classification."""

# CRITICAL: Set API key in environment
import os

# # Set the API key in environment for this session
# api_key = "REDACTED_OPENAI_KEY_REMOVED"
# os.environ['OPENAI_API_KEY'] = api_key
# print(f"Set OPENAI_API_KEY environment variable")
    
# SECURITY: API key should be set via environment variable, not hardcoded
# Set via: $env:OPENAI_API_KEY="your-key-here" (PowerShell) or export OPENAI_API_KEY="your-key-here" (bash)
if 'OPENAI_API_KEY' not in os.environ:
    print("ERROR: OPENAI_API_KEY environment variable not set!")
    print("Please set it via: $env:OPENAI_API_KEY='your-key-here' (PowerShell)")
    exit(1)
print(f"Using OPENAI_API_KEY from environment")

import asyncio
import logging
import time
from typing import Dict, Any
from focus_guard.core.classification.classifiers.domains.youtube_base import YouTubeClassifier
from focus_guard.core.domain.models import Domain

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_llm_youtube_classification():
    """Test LLM YouTube classification directly."""
    
    print("=== Testing LLM YouTube Classification ===")
    
    # Create YouTube classifier with LLM enabled
    try:
        youtube_classifier = YouTubeClassifier.create_default()
        print(f"Created classifier: {youtube_classifier.name}")
        print(f"Internal classifiers: {len(youtube_classifier.classifiers)}")
        for i, classifier in enumerate(youtube_classifier.classifiers):
            print(f"  {i}: {classifier.__class__.__name__} (name: {classifier.name})")
            if hasattr(classifier, 'llm_client'):
                print(f"     - Has LLM client: {type(classifier.llm_client).__name__}")
                print(f"     - Model: {getattr(classifier.llm_client, 'model', 'unknown')}")
        
        # Verify environment variable is set
        print(f"OPENAI_API_KEY in environment: {'OPENAI_API_KEY' in os.environ}")
        print(f"API key starts with: {os.environ.get('OPENAI_API_KEY', 'NOT_SET')[:10]}...")
        
        # Test cases
        test_cases = [
            {
                'name': 'Sports Video (Should Block)',
                'url': 'https://www.youtube.com/watch?v=wgZZhHOZJJQ',
                'title': '20 FUNNIEST MOMENTS IN TENNIS HISTORY',
                'expected': 'SPORTS | ENTERTAINMENT'
            },
            {
                'name': 'Educational Content',
                'url': 'https://www.youtube.com/watch?v=302eJ3TzJQU',
                'title': 'Introduction to Geometry',
                'expected': 'EDUCATION'
            },
            {
                'name': 'Gaming Content',
                'url': 'https://www.youtube.com/shorts/PbUzxamcdWo',
                'title': 'Minecraft',
                'expected': 'GAMING'
            },
            {
                'name': 'News Content',
                'url': 'https://www.youtube.com/watch?v=5oJI3sUAU68&list=RDNS5oJI3sUAU68&start_radio=1',
                'title': 'Disturbing details revealed in Minneapolis shooting: Tremendous volume of gunfire',
                'expected': 'NEWS'
            }
        ]
        
        domain = Domain("youtube.com")
        for test_case in test_cases[0:1]:
            context = {
                'url': test_case['url'],
                'title': test_case['title'],
                'timestamp': '2025-08-28T20:11:00',
                'domain': 'youtube.com'
            }
            
            print(f"\n--- {test_case['name']} ---")
            print(f"URL: {test_case['url']}")
            print(f"Title: {test_case['title']}")
            print(f"Context: {context}")
            print(f"Expected: {test_case['expected']}")
            
            start_time = asyncio.get_event_loop().time()
            result = await youtube_classifier.classify(domain, context)
            end_time = asyncio.get_event_loop().time()
            
            if result:
                print(f"Actual: {result.category}")
                print(f"Confidence: {result.confidence}")
                print(f"Classifier used: {result.metadata.get('classifier', 'unknown')}")
                print(f"Method: {result.metadata.get('method', 'unknown')}")
                print(f"Classification time: {end_time - start_time:.2f}s")
                
                # Check if result matches expectation
                if str(result.category).upper().endswith(test_case['expected']):
                    print("CORRECT")
                else:
                    print("INCORRECT")
            else:
                print("No classification result")
                print("FAILED")
            
    except Exception as e:
        print(f"Error testing LLM classification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_youtube_classification())
