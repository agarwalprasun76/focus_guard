#!/usr/bin/env python3
"""
Simple test to verify YouTube metadata extraction.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_metadata():
    print("Testing YouTube metadata extraction...")
    
    from focus_guard.core.utils.youtube_utils import extract_youtube_id
    from focus_guard.core.utils.metadata_fetcher import metadata_fetcher
    
    url = "https://www.youtube.com/watch?v=m_C4uC-kWA4"
    video_id = extract_youtube_id(url)
    print(f"Video ID: {video_id}")
    
    if video_id:
        metadata = metadata_fetcher.fetch_metadata_for_youtube(video_id)
        if metadata and 'error' not in metadata:
            print(f"SUCCESS: Got title: {metadata.get('title', 'N/A')}")
            print(f"Channel: {metadata.get('channel_title', 'N/A')}")
            return True
        else:
            print(f"FAILED: {metadata.get('error', 'Unknown error')}")
    return False

if __name__ == "__main__":
    test_metadata()
