"""
YouTube utility functions for extracting video IDs and metadata.
Moved from UNUSED/archive/core/domain_classifier/utils.py
"""

from typing import Union
from urllib.parse import urlparse, parse_qs


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed_url = urlparse(url)
        return parsed_url.netloc.lower().replace('www.', '')
    except:
        return ''


def is_youtube_url(url: str) -> bool:
    """
    Check if the URL is a YouTube URL.
    
    Args:
        url: URL to check
        
    Returns:
        bool: True if YouTube URL, False otherwise
    """
    youtube_domains = ['youtube.com', 'youtu.be', 'youtube-nocookie.com']
    domain = extract_domain(url)
    
    return any(yt_domain == domain or domain.endswith('.' + yt_domain) 
               for yt_domain in youtube_domains)


def extract_youtube_id(url: str) -> Union[str, None]:
    """
    Extract YouTube video ID from a URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        str: Video ID or None if not found or not a YouTube URL
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Different YouTube URL formats
        if 'youtube.com' in domain:
            if '/watch' in parsed_url.path:
                query_params = parse_qs(parsed_url.query)
                return query_params.get('v', [''])[0] or None
            elif '/embed/' in parsed_url.path or '/v/' in parsed_url.path:
                path_parts = parsed_url.path.split('/')
                return path_parts[-1] if path_parts[-1] else None
            elif '/shorts/' in parsed_url.path:
                path_parts = parsed_url.path.split('/')
                return path_parts[-1] if path_parts[-1] else None
        elif 'youtu.be' in domain:
            path = parsed_url.path.lstrip('/')
            return path if path else None
        
        return None
    except:
        return None
