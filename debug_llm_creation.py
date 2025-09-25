#!/usr/bin/env python3
"""Debug script to test LLM classifier creation step by step."""

import os
import sys
import logging

# Fix Unicode encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check for API key in environment
if 'OPENAI_API_KEY' not in os.environ:
    print("ERROR: OPENAI_API_KEY environment variable not set")
    print("Please set it with: setx OPENAI_API_KEY \"your-api-key-here\"")
    exit(1)

print("=== Debug LLM Classifier Creation ===")
print(f"OpenAI API Key: {os.environ.get('OPENAI_API_KEY', 'NOT SET')[:20]}...")

# Step 1: Test OpenAI client creation
print("\n--- Step 1: Testing OpenAI Client Creation ---")
try:
    from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
    print("[SUCCESS] OpenAI client import successful")
    
    llm_client = OpenAIClient()
    print("[SUCCESS] OpenAI client creation successful")
except Exception as e:
    print(f"[ERROR] OpenAI client creation failed: {e}")
    import traceback
    traceback.print_exc()

# Step 2: Test LLM YouTube classifier creation
print("\n--- Step 2: Testing LLM YouTube Classifier Creation ---")
try:
    from focus_guard.core.classification.classifiers.domains.youtube_llm import LLMBasedYouTubeClassifier
    print("[SUCCESS] LLM YouTube classifier import successful")
    
    llm_classifier = LLMBasedYouTubeClassifier(llm_client=llm_client)
    print("[SUCCESS] LLM YouTube classifier creation successful")
    print(f"  Name: {llm_classifier.name}")
except Exception as e:
    print(f"[ERROR] LLM YouTube classifier creation failed: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Test composite YouTube classifier creation
print("\n--- Step 3: Testing Composite YouTube Classifier Creation ---")
try:
    from focus_guard.core.classification.classifiers.domains.youtube_base import YouTubeClassifier
    print("[SUCCESS] YouTube base classifier import successful")
    
    composite_classifier = YouTubeClassifier.create_default()
    print("[SUCCESS] Composite YouTube classifier creation successful")
    print(f"  Name: {composite_classifier.name}")
    print(f"  Number of internal classifiers: {len(composite_classifier.classifiers)}")
    
    for i, classifier in enumerate(composite_classifier.classifiers):
        print(f"    {i}: {classifier.__class__.__name__} (name: {classifier.name})")
        
except Exception as e:
    print(f"[ERROR] Composite YouTube classifier creation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Debug Complete ===")
