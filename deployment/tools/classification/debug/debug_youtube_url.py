#!/usr/bin/env python3
"""
Simple YouTube URL classification debug tool.
Thin wrapper around existing classification infrastructure.
"""

import asyncio
import sys
from focus_guard.core.api.api import ClassifierBlockerAPI
from focus_guard.core.utils.metadata_fetcher import metadata_fetcher


async def debug_youtube_classification(url: str) -> dict:
    """
    Debug YouTube classification for a given URL.
    
    Args:
        url: YouTube URL to classify
        
    Returns:
        dict: Classification results with metadata, category, blocking decision, etc.
    """
    api = ClassifierBlockerAPI()
    
    # Fetch metadata
    metadata = metadata_fetcher.get_youtube_metadata(url)
    
    if metadata and 'error' not in metadata:
        # Get classification and blocking details in one call
        blocking_result = await api.check_blocking_with_details(url, metadata)
        
        return {
            'url': url,
            'metadata': {
                'title': metadata.get('title', 'Unknown'),
                'channel': metadata.get('channel_title', 'Unknown'),
                'description': metadata.get('description', '')[:200] + '...' if metadata.get('description', '') else '',
                'duration': metadata.get('duration', 'Unknown'),
                'view_count': metadata.get('view_count', 'Unknown'),
                'categories': metadata.get('categories', []),
                'tags': metadata.get('tags', [])[:5]  # First 5 tags only
            },
            'classification': {
                'category': blocking_result.category.name if blocking_result.category else 'UNKNOWN',
                'classifier': blocking_result.classifier_name or 'unknown',
                'should_block': blocking_result.should_block,
                'reason': blocking_result.reason or 'No reason provided'
            },
            'status': 'success'
        }
    else:
        return {
            'url': url,
            'status': 'error',
            'error': metadata.get('error', 'Failed to fetch metadata') if metadata else 'No metadata returned'
        }


async def main():
    """Interactive mode for testing YouTube URLs."""
    print("YouTube Classification Debug Tool")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        # Command line mode
        url = sys.argv[1]
        result = await debug_youtube_classification(url)
        print_result(result)
    else:
        # Interactive mode
        print("Enter YouTube URLs to test (or 'quit' to exit):")
        
        while True:
            try:
                url = input("\nYouTube URL: ").strip()
                
                if url.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not url:
                    continue
                    
                if 'youtube.com' not in url and 'youtu.be' not in url:
                    print("Please enter a valid YouTube URL")
                    continue
                
                print(f"\nAnalyzing: {url}")
                result = await debug_youtube_classification(url)
                print_result(result)
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")


def print_result(result: dict):
    """Print classification result in a readable format."""
    if result['status'] == 'error':
        print(f"[ERROR] {result['error']}")
        return
    
    metadata = result['metadata']
    classification = result['classification']
    
    # Use safe encoding for Windows console
    title = metadata['title'].encode('ascii', 'replace').decode('ascii')
    channel = metadata['channel'].encode('ascii', 'replace').decode('ascii')
    
    print(f"\nTitle: {title}")
    print(f"Channel: {channel}")
    print(f"Duration: {metadata['duration']} seconds" if isinstance(metadata['duration'], int) else f"Duration: {metadata['duration']}")
    print(f"Views: {metadata['view_count']}")
    
    if metadata['description']:
        desc = metadata['description'].encode('ascii', 'replace').decode('ascii')
        print(f"Description: {desc}")
    
    if metadata['categories']:
        print(f"Categories: {', '.join(metadata['categories'])}")
    
    if metadata['tags']:
        print(f"Tags: {', '.join(metadata['tags'])}")
    
    print(f"\nClassification:")
    print(f"   Category: {classification['category']}")
    print(f"   Classifier: {classification['classifier']}")
    
    status = "[BLOCKED]" if classification['should_block'] else "[ALLOWED]"
    print(f"\n{status}")
    print(f"   Reason: {classification['reason']}")


if __name__ == '__main__':
    asyncio.run(main())
