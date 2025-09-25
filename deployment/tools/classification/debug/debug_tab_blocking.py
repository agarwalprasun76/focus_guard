#!/usr/bin/env python3
"""
Debug tool to test tab blocking functionality.
Simulates the full pipeline from tab detection to blocking decision.
"""

import asyncio
import sys
from datetime import datetime
from focus_guard.core.api.api import ClassifierBlockerAPI
from focus_guard.core.utils.metadata_fetcher import metadata_fetcher


async def test_tab_blocking_pipeline(url: str) -> dict:
    """
    Test the complete tab blocking pipeline for a given URL.
    
    Args:
        url: URL to test blocking for
        
    Returns:
        dict: Complete test results including metadata, classification, and blocking decision
    """
    api = ClassifierBlockerAPI()
    
    print(f"Testing tab blocking pipeline for: {url}")
    print("=" * 60)
    
    # Step 1: Simulate tab detection (what browser component does)
    print("Step 1: Simulating tab detection...")
    tab_metadata = {
        'url': url,
        'title': '',  # Will be filled by metadata fetcher
        'timestamp': datetime.now().isoformat(),
        'domain': url.split('/')[2] if '://' in url else url.split('/')[0]
    }
    
    # Step 2: Fetch metadata (what browser component does for YouTube)
    print("Step 2: Fetching metadata...")
    if 'youtube.com' in url or 'youtu.be' in url:
        metadata = metadata_fetcher.get_youtube_metadata(url)
        if metadata and 'error' not in metadata:
            tab_metadata['title'] = metadata.get('title', '')
            # Handle Unicode encoding for Windows console
            title = metadata.get('title', 'Unknown').encode('ascii', 'replace').decode('ascii')
            channel = metadata.get('channel_title', 'Unknown').encode('ascii', 'replace').decode('ascii')
            print(f"   Title: {title}")
            print(f"   Channel: {channel}")
        else:
            print(f"   Failed to fetch YouTube metadata: {metadata}")
            metadata = None
    else:
        metadata = tab_metadata
        print(f"   Using basic metadata for non-YouTube URL")
    
    # Step 3: Check blocking decision (what browser component calls)
    print("Step 3: Checking blocking decision...")
    try:
        blocking_result = await api.check_blocking_with_details(url, metadata or tab_metadata)
        
        print(f"   Category: {blocking_result.category.name if blocking_result.category else 'UNKNOWN'}")
        print(f"   Classifier: {blocking_result.classifier_name or 'unknown'}")
        print(f"   Should block: {blocking_result.should_block}")
        print(f"   Reason: {blocking_result.reason or 'No reason provided'}")
        
        # Step 4: Simulate tab action
        print("Step 4: Tab action simulation...")
        if blocking_result.should_block:
            print("   [BLOCKED] TAB WOULD BE CLOSED")
            print(f"   Reason: {blocking_result.reason}")
        else:
            print("   [ALLOWED] TAB WOULD REMAIN OPEN")
        
        return {
            'url': url,
            'metadata': metadata,
            'tab_metadata': tab_metadata,
            'classification': {
                'category': blocking_result.category.name if blocking_result.category else 'UNKNOWN',
                'classifier': blocking_result.classifier_name or 'unknown',
                'should_block': blocking_result.should_block,
                'reason': blocking_result.reason or 'No reason provided'
            },
            'action': 'CLOSE_TAB' if blocking_result.should_block else 'ALLOW_TAB',
            'status': 'success'
        }
        
    except Exception as e:
        print(f"   [ERROR] Error in blocking check: {e}")
        return {
            'url': url,
            'status': 'error',
            'error': str(e)
        }


async def test_multiple_urls():
    """Test tab blocking with multiple test URLs."""
    test_urls = [
        "https://www.youtube.com/shorts/OUiAkbjN2uI",  # Entertainment (should block)
        "https://www.youtube.com/watch?v=302eJ3TzJQU",  # Education (should allow)
        "https://www.google.com",  # Non-YouTube (depends on config)
        "https://stackoverflow.com/questions/12345",  # Programming (likely allow)
    ]
    
    results = []
    
    for url in test_urls:
        print(f"\n{'='*80}")
        result = await test_tab_blocking_pipeline(url)
        results.append(result)
        
        # Brief summary
        if result['status'] == 'success':
            action = "[BLOCKED]" if result['action'] == 'CLOSE_TAB' else "[ALLOWED]"
            print(f"\nSUMMARY: {action} - {result['classification']['category']}")
        else:
            print(f"\nSUMMARY: [ERROR] - {result['error']}")
    
    return results


async def main():
    """Main function for interactive testing."""
    print("Tab Blocking Pipeline Debug Tool")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        # Batch mode - test multiple URLs
        await test_multiple_urls()
    elif len(sys.argv) > 1:
        # Command line mode - single URL
        url = sys.argv[1]
        await test_tab_blocking_pipeline(url)
    else:
        # Interactive mode
        print("Options:")
        print("1. Test single URL")
        print("2. Test batch of URLs")
        print("3. Enter custom URL")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            url = input("Enter URL to test: ").strip()
            if url:
                await test_tab_blocking_pipeline(url)
        elif choice == "2":
            await test_multiple_urls()
        elif choice == "3":
            while True:
                url = input("\nEnter URL (or 'quit' to exit): ").strip()
                if url.lower() in ['quit', 'exit', 'q']:
                    break
                if url:
                    await test_tab_blocking_pipeline(url)


if __name__ == '__main__':
    asyncio.run(main())
