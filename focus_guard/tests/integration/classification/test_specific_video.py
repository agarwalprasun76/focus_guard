#!/usr/bin/env python3
"""
Test YouTube classification for a specific video.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def test_video_classification():
    url = "https://www.youtube.com/watch?v=H2bRYtE5l18"
    
    print(f"Testing YouTube classification for: {url}")
    
    # Test metadata extraction
    from focus_guard.core.utils.youtube_utils import extract_youtube_id
    from focus_guard.core.utils.metadata_fetcher import metadata_fetcher
    
    video_id = extract_youtube_id(url)
    print(f"Video ID: {video_id}")
    
    if video_id:
        metadata = metadata_fetcher.fetch_metadata_for_youtube(video_id)
        if metadata and 'error' not in metadata:
            # Handle Unicode characters for Windows console
            title = metadata.get('title', 'N/A').encode('ascii', 'replace').decode('ascii')
            channel = metadata.get('channel_title', 'N/A').encode('ascii', 'replace').decode('ascii')
            print(f"Title: {title}")
            print(f"Channel: {channel}")
            print(f"Duration: {metadata.get('duration', 'N/A')} seconds")
            print(f"View Count: {metadata.get('view_count', 'N/A')}")
            if metadata.get('description'):
                desc = metadata['description'][:200] + "..." if len(metadata['description']) > 200 else metadata['description']
                desc = desc.encode('ascii', 'replace').decode('ascii')
                print(f"Description: {desc}")
        else:
            print(f"Metadata extraction failed: {metadata.get('error', 'Unknown error')}")
            return
    
    # Test classification
    from focus_guard.core.api.api import ClassifierBlockerAPI
    from focus_guard.core.domain.domain_utils_new import extract_domain_from_url
    
    api = ClassifierBlockerAPI()
    domain = extract_domain_from_url(url)
    
    category = await api.classify_domain(domain, url)
    print(f"Classification: {category.name if category else 'None'}")
    
    # Test blocking decision using combined method
    blocking_result = await api.check_blocking_with_details(url)
    
    status = "BLOCKED" if blocking_result.should_block else "ALLOWED"
    print(f"Decision: {status}")
    print(f"Reason: {blocking_result.reason or 'No reason provided'}")
    if blocking_result.category:
        print(f"Category: {blocking_result.category.name}")
    if blocking_result.classifier_name:
        print(f"Classified by: {blocking_result.classifier_name}")

if __name__ == "__main__":
    asyncio.run(test_video_classification())
