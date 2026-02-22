#!/usr/bin/env python3
"""
Integration tests for YouTube classifier with real video URLs.

Tests the full pipeline:
1. Metadata extraction from real YouTube videos
2. LLM-based classification with extracted metadata
3. End-to-end classification accuracy
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the focus_guard package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
from focus_guard.core.classification.classifiers.domains.youtube_llm import LLMBasedYouTubeClassifier
from focus_guard.core.domain.models import Domain

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Real YouTube video test cases with expected classifications
# These are actual YouTube videos that should be classified correctly
REAL_YOUTUBE_TEST_VIDEOS = [
    # Educational content
    {
        "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc",
        "expected_category": "EDUCATION",
        "expected_usefulness": "EDUCATIONAL",
        "description": "Python Tutorial for Beginners (Programming with Mosh)",
    },
    {
        "url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
        "expected_category": "EDUCATION",
        "expected_usefulness": "EDUCATIONAL",
        "description": "Learn Python - Full Course for Beginners (freeCodeCamp)",
    },
    {
        "url": "https://www.youtube.com/watch?v=8hly31xKli0",
        "expected_category": "EDUCATION",
        "expected_usefulness": "EDUCATIONAL",
        "description": "Algorithms and Data Structures Tutorial (freeCodeCamp)",
    },
    # Gaming content - trailers
    {
        "url": "https://www.youtube.com/watch?v=MmB9b5njVbA",
        "expected_category": "ENTERTAINMENT",
        "expected_usefulness": "DISTRACTION",
        "description": "Official Minecraft Trailer (game trailer = entertainment)",
    },
    # Gaming content - actual gameplay/let's play
    {
        "url": "https://www.youtube.com/shorts/tNRcypF_RjU",
        "expected_category": "GAMING",
        "expected_usefulness": "DISTRACTION",
        "description": "Minecraft Let's Play gameplay video",
    },
    {
        "url": "https://www.youtube.com/shorts/JnEkheSMQcA",
        "expected_category": "GAMING",
        "expected_usefulness": "DISTRACTION",
        "description": "Fortnite gameplay highlights",
    },
    # Entertainment/Music
    {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "expected_category": "ENTERTAINMENT",
        "expected_usefulness": "DISTRACTION",
        "description": "Rick Astley - Never Gonna Give You Up (Music Video)",
    },
    # Educational music (violin/classical)
    {
        "url": "https://www.youtube.com/watch?v=I03Hs6dwj7E",
        "expected_category": "EDUCATION",
        "expected_usefulness": "EDUCATIONAL",
        "description": "Bach Violin Sonata (Classical Performance)",
    },
]


async def fetch_youtube_metadata(video_id: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata for a YouTube video."""
    try:
        from focus_guard.core.utils.metadata_fetcher import metadata_fetcher
        metadata = metadata_fetcher.fetch_metadata_for_youtube(video_id)
        if metadata and 'error' not in metadata:
            return metadata
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch metadata for {video_id}: {e}")
        return None


async def test_single_classification():
    """Test a single YouTube classification with mock context."""
    
    print("Testing YouTube classifier with mock context...")
    api_key = os.getenv('OPENAI_API_KEY', '')
    print(f"API Key: {'...'+api_key[-4:] if api_key else 'Not set'}")
    
    try:
        # Create OpenAI client with explicit model
        print("\n1. Creating OpenAI client...")
        llm_client = OpenAIClient(model="gpt-4o-mini")
        print("   [OK] OpenAI client created successfully")
        
        # Create YouTube classifier
        print("\n2. Creating YouTube classifier...")
        classifier = LLMBasedYouTubeClassifier(llm_client=llm_client)
        print("   [OK] YouTube classifier created successfully")
        
        # Test classification with mock context
        print("\n3. Testing classification with mock context...")
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
            return True
        else:
            print("   [ERROR] Classification returned None")
            return False
            
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_real_video_classification(video_info: Dict[str, Any]) -> Dict[str, Any]:
    """Test classification of a real YouTube video with metadata fetching."""
    from focus_guard.core.utils.youtube_utils import extract_youtube_id
    
    url = video_info["url"]
    video_id = extract_youtube_id(url)
    
    result = {
        "url": url,
        "video_id": video_id,
        "expected_category": video_info["expected_category"],
        "expected_usefulness": video_info["expected_usefulness"],
        "description": video_info["description"],
        "success": False,
        "metadata_fetched": False,
        "actual_category": None,
        "actual_usefulness": None,
        "confidence": None,
        "reason": None,
        "error": None,
    }
    
    if not video_id:
        result["error"] = "Could not extract video ID"
        return result
    
    try:
        # Step 1: Fetch real metadata
        metadata = await fetch_youtube_metadata(video_id)
        
        if metadata:
            result["metadata_fetched"] = True
            result["title"] = metadata.get("title", "Unknown")
            result["channel"] = metadata.get("channel_title", "Unknown")
        else:
            # Use fallback context from test case description
            metadata = {
                "title": video_info["description"],
                "url": url,
            }
        
        # Step 2: Classify with LLM
        llm_client = OpenAIClient(model="gpt-4o-mini")
        classifier = LLMBasedYouTubeClassifier(llm_client=llm_client)
        
        domain = Domain("youtube.com")
        context = {
            "url": url,
            "video_id": video_id,
            **metadata
        }
        
        classification = await classifier.classify(domain, context)
        
        if classification:
            result["actual_category"] = str(classification.category).upper()
            result["actual_usefulness"] = classification.metadata.get("usefulness", "UNKNOWN")
            result["confidence"] = classification.confidence
            result["reason"] = classification.metadata.get("reason", "N/A")
            
            # Check if classification matches expected
            category_match = result["actual_category"] == result["expected_category"]
            usefulness_match = result["actual_usefulness"] == result["expected_usefulness"]
            result["success"] = category_match  # Primary success is category match
            result["usefulness_match"] = usefulness_match
        else:
            result["error"] = "Classification returned None"
            
    except Exception as e:
        result["error"] = str(e)
        
    return result


async def test_real_videos_batch():
    """Test classification of multiple real YouTube videos."""
    print("\n" + "=" * 70)
    print("REAL YOUTUBE VIDEO CLASSIFICATION TEST")
    print("=" * 70)
    
    results = []
    passed = 0
    failed = 0
    
    for i, video_info in enumerate(REAL_YOUTUBE_TEST_VIDEOS, 1):
        print(f"\n[{i}/{len(REAL_YOUTUBE_TEST_VIDEOS)}] Testing: {video_info['description'][:50]}...")
        
        result = await test_real_video_classification(video_info)
        results.append(result)
        
        if result["success"]:
            passed += 1
            status = "[PASS]"
        else:
            failed += 1
            status = "[FAIL]"
        
        print(f"   {status} Expected: {result['expected_category']}, Got: {result['actual_category']}")
        if result.get("metadata_fetched"):
            title = result.get("title", "")[:40]
            print(f"   Title: {title}...")
        if result.get("error"):
            print(f"   Error: {result['error']}")
        if result.get("reason"):
            reason = result["reason"][:60] if len(result.get("reason", "")) > 60 else result.get("reason", "")
            print(f"   Reason: {reason}...")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total: {len(results)}, Passed: {passed}, Failed: {failed}")
    print(f"Accuracy: {passed/len(results)*100:.1f}%")
    
    return results


async def test_direct_api_call():
    """Test direct OpenAI API call to verify authentication."""
    
    print("\nTesting direct OpenAI API call...")
    try:
        llm_client = OpenAIClient(model="gpt-4o-mini")
        
        response = await llm_client.generate(
            prompt="Say 'Hello, World!' in JSON format with a 'message' field.",
            system_prompt="You are a helpful assistant that responds in JSON."
        )
        
        if response:
            print(f"   [SUCCESS] Direct API call successful!")
            print(f"      Response: {response[:100]}...")
            return True
        else:
            print("   [ERROR] Direct API call returned None")
            return False
            
    except Exception as e:
        print(f"   [ERROR] Direct API call failed: {e}")
        return False


async def run_all_tests():
    """Run all YouTube classification tests."""
    print("=" * 70)
    print("YOUTUBE CLASSIFIER INTEGRATION TESTS")
    print("=" * 70)
    
    # Test 1: Direct API call
    print("\n--- Test 1: OpenAI API Connection ---")
    api_ok = await test_direct_api_call()
    
    if not api_ok:
        print("\n[ABORT] API connection failed. Cannot proceed with classification tests.")
        return False
    
    # Test 2: Single classification with mock context
    print("\n--- Test 2: Single Classification (Mock Context) ---")
    mock_ok = await test_single_classification()
    
    # Test 3: Real video classification batch
    print("\n--- Test 3: Real Video Classification (with Metadata Fetching) ---")
    results = await test_real_videos_batch()
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"API Connection: {'PASS' if api_ok else 'FAIL'}")
    print(f"Mock Classification: {'PASS' if mock_ok else 'FAIL'}")
    
    passed = sum(1 for r in results if r["success"])
    print(f"Real Video Tests: {passed}/{len(results)} passed")
    
    return api_ok and mock_ok and passed >= len(results) // 2


if __name__ == "__main__":
    print("=== YouTube Classifier Integration Test Suite ===\n")
    
    success = asyncio.run(run_all_tests())
    
    print("\n=== Test Suite Complete ===")
    sys.exit(0 if success else 1)
