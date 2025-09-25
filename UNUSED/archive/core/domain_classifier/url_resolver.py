"""
URL Resolver: Handles URL resolution, following redirects, and analyzing embedded content.
"""
import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional

from core.logger.logger import get_logger
from core.domain_classifier.utils import extract_domain, extract_youtube_id, is_search_results_page, get_platform_from_url
from core.domain_classifier.html_utils import (
    extract_video_elements_from_html,
    extract_youtube_videos_from_google_search,
    extract_youtube_videos_from_bing_search,
    extract_youtube_links_from_page,
    detect_autoplay_content_from_html
)

logger = get_logger(__name__)

class URLResolver:
    """Follows redirects and identifies the final destination URL"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def resolve_url(self, url):
        """Follow redirects and identify the final destination URL
        
        Args:
            url (str): The URL to resolve
            
        Returns:
            dict: Information about the URL, including final destination if redirected
        """
        try:
            response = self.session.head(url, allow_redirects=True, timeout=5)
            final_url = response.url
            return {
                'original_url': url,
                'final_url': final_url,
                'redirect_chain': [r.url for r in response.history],
                'is_redirect': len(response.history) > 0
            }
        except Exception as e:
            logger.warning(f"Failed to resolve URL {url}: {str(e)}")
            return {'original_url': url, 'error': str(e)}


class EmbeddedContentAnalyzer:
    """Detects embedded video content from platforms like YouTube in third-party pages"""
    
    def extract_embedded_content(self, url: str) -> Dict[str, Any]:
        """Extract embedded video URLs and metadata from a page
        
        Args:
            url (str): The URL to analyze for embedded content
            
        Returns:
            Dict[str, Any]: Dictionary of detected embedded content
        """
        try:
            # Get platform information for better context
            platform = get_platform_from_url(url)
            is_search_page = is_search_results_page(url)
            
            # Fetch page content
            response = requests.get(url, timeout=10)
            html_content = response.text
            
            # Dictionary to store all embeds
            embeds = {}
            
            # Extract video elements (iframes, etc.)
            video_elements = extract_video_elements_from_html(html_content)
            embeds.update(video_elements)
            
            # Platform specific extraction
            if 'google' in url.lower() and is_search_page:
                google_videos = extract_youtube_videos_from_google_search(html_content)
                embeds.update(google_videos)
            
            if 'bing' in url.lower():
                bing_videos = extract_youtube_videos_from_bing_search(html_content)
                embeds.update(bing_videos)
            
            # Look for regular YouTube links in any page
            youtube_links = extract_youtube_links_from_page(html_content)
            embeds.update(youtube_links)
            
            # Add source platform information to all embeds
            for key, embed in embeds.items():
                if 'source_platform' not in embed:
                    embed['source_platform'] = platform
            
            return embeds
            
        except Exception as e:
            logger.warning(f"Failed to analyze page for embedded content: {str(e)}")
            return {}
    
    # This method is removed in favor of using the utility function extract_youtube_id

    def detect_autoplay_content(self, url: str, current_video_id: Optional[str] = None) -> Dict[str, Any]:
        """Check if a page has autoplay content that differs from the current video
        
        Args:
            url (str): The YouTube or video platform URL
            current_video_id (str, optional): The ID of the currently playing video
            
        Returns:
            Dict[str, Any]: Information about autoplay content, if detected
        """
        if 'youtube.com' not in url and 'youtu.be' not in url:
            return {'has_autoplay': False}
            
        try:
            # Use the utility function to detect autoplay content
            response = requests.get(url, timeout=10)
            autoplay_info = detect_autoplay_content_from_html(response.text, current_video_id)
            return autoplay_info
            
        except Exception as e:
            logger.warning(f"Failed to detect autoplay content: {str(e)}")
            return {'has_autoplay': False, 'error': str(e)}
