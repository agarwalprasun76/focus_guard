#!/usr/bin/env python3
"""
Test YouTube metadata fetching and classification.
"""

import asyncio
from focus_guard.core.api.api import ClassifierBlockerAPI
from focus_guard.core.utils.metadata_fetcher import metadata_fetcher

async def test_youtube_with_metadata():
    api = ClassifierBlockerAPI()
    
    # Test the YouTube URL from your example
    test_url = 'https://www.youtube.com/shorts/OUiAkbjN2uI'
    print(f'Testing: {test_url}')
    
    # Fetch metadata first
    print('Fetching YouTube metadata...')
    metadata = metadata_fetcher.get_youtube_metadata(test_url)
    
    if metadata and 'error' not in metadata:
        title = metadata.get("title", "Unknown")
        channel = metadata.get("channel_title", "Unknown")
        print(f'Got metadata: {title.encode("ascii", "replace").decode("ascii")}')
        print(f'Channel: {channel.encode("ascii", "replace").decode("ascii")}')
        
        # Test classification with metadata using combined method
        blocking_result = await api.check_blocking_with_details(test_url, metadata)
        
        print(f'Classification result: {"BLOCKED" if blocking_result.should_block else "ALLOWED"}')
        print(f'Reason: {blocking_result.reason}')
        if blocking_result.category:
            print(f'Category: {blocking_result.category.name}')
        if blocking_result.classifier_name:
            print(f'Classified by: {blocking_result.classifier_name}')
    else:
        print(f'Failed to fetch metadata: {metadata}')

if __name__ == '__main__':
    asyncio.run(test_youtube_with_metadata())
