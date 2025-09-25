#!/usr/bin/env python3
"""
Test YouTube classifier in isolation to debug authentication issues.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the focus_guard package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
from focus_guard.core.classification.classifiers.domains.youtube_llm import LLMBasedYouTubeClassifier
from focus_guard.core.domain.models import Domain

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_single_classification():
    """Test a single YouTube classification to isolate the issue."""
    
    print("Testing YouTube classifier in isolation...")
    print(f"API Key: {os.getenv('OPENAI_API_KEY', 'Not set')[:20]}...")
    
    try:
        # Create OpenAI client with explicit model
        print("\n1. Creating OpenAI client...")
        llm_client = OpenAIClient(model="gpt-4o-mini")
        print("   [OK] OpenAI client created successfully")
        
        # Create YouTube classifier
        print("\n2. Creating YouTube classifier...")
        classifier = LLMBasedYouTubeClassifier(llm_client=llm_client)
        print("   [OK] YouTube classifier created successfully")
        
        # Test classification
        print("\n3. Testing classification...")
        domain = Domain("youtube.com")
        context = {
            "title": "Python Tutorial for Beginners",
            "channel_title": "Programming Academy",
            "description": "Learn Python programming from scratch"
        }
        
        print("   Making API call...")
        result = await classifier.classify(domain, context)
        
        if result:
            print(f"   [SUCCESS] Classification successful!")
            print(f"      Category: {result.category}")
            print(f"      Confidence: {result.confidence}")
            print(f"      Reason: {result.metadata.get('reason', 'N/A')}")
        else:
            print("   [ERROR] Classification returned None")
            
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

def test_direct_api_call():
    """Test direct OpenAI API call to verify authentication."""
    
    print("\n4. Testing direct API call...")
    try:
        llm_client = OpenAIClient(model="gpt-4o-mini")
        
        # Make a simple direct call
        import asyncio
        
        async def make_call():
            response = await llm_client.generate(
                prompt="Say 'Hello, World!' in JSON format with a 'message' field.",
                system_prompt="You are a helpful assistant that responds in JSON."
            )
            return response
        
        response = asyncio.run(make_call())
        
        if response:
            print(f"   [SUCCESS] Direct API call successful!")
            print(f"      Response: {response[:100]}...")
        else:
            print("   [ERROR] Direct API call returned None")
            
    except Exception as e:
        print(f"   [ERROR] Direct API call failed: {e}")

if __name__ == "__main__":
    print("=== YouTube Classifier Authentication Test ===")
    
    # Test direct API call first
    test_direct_api_call()
    
    # Test classifier
    asyncio.run(test_single_classification())
    
    print("\n=== Test Complete ===")
