#!/usr/bin/env python3
"""
Test YouTube Shorts classification for the specific URL.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def test_shorts_classification():
    print("Testing YouTube Shorts classification...")
    
    url = "https://www.youtube.com/shorts/At3syx84D34"
    
    # Test 1: Metadata extraction
    print(f"\n1. Testing metadata extraction for: {url}")
    
    from focus_guard.core.utils.youtube_utils import extract_youtube_id
    from focus_guard.core.utils.metadata_fetcher import metadata_fetcher
    
    video_id = extract_youtube_id(url)
    print(f"   Video ID: {video_id}")
    
    if video_id:
        metadata = metadata_fetcher.fetch_metadata_for_youtube(video_id)
        if metadata and 'error' not in metadata:
            print(f"   SUCCESS: Metadata extracted")
            print(f"   Title: {metadata.get('title', 'N/A')}")
            print(f"   Channel: {metadata.get('channel_title', 'N/A')}")
            print(f"   Duration: {metadata.get('duration', 'N/A')} seconds")
            print(f"   View Count: {metadata.get('view_count', 'N/A')}")
            if metadata.get('description'):
                desc = metadata['description'][:150] + "..." if len(metadata['description']) > 150 else metadata['description']
                print(f"   Description: {desc}")
        else:
            print(f"   FAILED: {metadata.get('error', 'Unknown error')}")
            return False
    else:
        print("   FAILED: Could not extract video ID")
        return False
    
    # Test 2: Classification with API
    print(f"\n2. Testing classification with API...")
    
    from focus_guard.core.api.api import ClassifierBlockerAPI
    from focus_guard.core.domain.domain_utils_new import extract_domain_from_url
    
    api = ClassifierBlockerAPI()
    domain = extract_domain_from_url(url)
    print(f"   Domain: {domain}")
    
    category = await api.classify_domain(domain, url)
    if category:
        print(f"   Classification: {category.name}")
    else:
        print(f"   No classification returned")
    
    # Test 3: Blocking decision using combined method
    print(f"\n3. Testing blocking decision...")
    
    blocking_result = await api.check_blocking_with_details(url)
    
    status = "BLOCKED" if blocking_result.should_block else "ALLOWED"
    print(f"   Decision: {status}")
    print(f"   Reason: {blocking_result.reason or 'No reason provided'}")
    if blocking_result.category:
        print(f"   Category: {blocking_result.category.name}")
    if blocking_result.classifier_name:
        print(f"   Classified by: {blocking_result.classifier_name}")
    
    print(f"\nTest complete for YouTube Shorts URL")
    return True

if __name__ == "__main__":
    asyncio.run(test_shorts_classification())
