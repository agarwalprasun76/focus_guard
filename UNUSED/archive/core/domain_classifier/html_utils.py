"""
HTML Utilities

This module provides utility functions for HTML parsing and content extraction,
particularly focused on embedded content and video platforms.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Union
from bs4 import BeautifulSoup, Tag

from core.logger.logger import get_logger
from core.domain_classifier.utils import extract_youtube_id, extract_domain

logger = get_logger(__name__)

def extract_video_elements_from_html(html_content: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract video elements from HTML content.
    
    Args:
        html_content: HTML content string
        
    Returns:
        Dict: Dictionary of video elements with IDs as keys
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        video_elements = {}
        
        # Extract iframe video embeds
        iframes = soup.find_all('iframe')
        for idx, iframe in enumerate(iframes):
            src = iframe.get('src', '')
            if not src:
                continue
                
            # YouTube embeds
            video_id = extract_youtube_id(src)
            if video_id:
                video_elements[f'youtube_iframe_{video_id}'] = {
                    'type': 'youtube',
                    'video_id': video_id,
                    'embed_url': src,
                    'platform': 'YouTube',
                    'element_type': 'iframe'
                }
        
        # Extract HTML5 video elements
        videos = soup.find_all('video')
        for idx, video in enumerate(videos):
            video_elements[f'html5_video_{idx}'] = {
                'type': 'html5',
                'element_type': 'video',
                'sources': [src.get('src', '') for src in video.find_all('source')],
                'attributes': {k: v for k, v in video.attrs.items()}
            }
        
        return video_elements
        
    except Exception as e:
        logger.error(f"Error extracting video elements: {str(e)}")
        return {}

def extract_youtube_videos_from_google_search(html_content: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract YouTube videos from Google search results.
    
    Args:
        html_content: HTML content from Google search results page
        
    Returns:
        Dict: Dictionary of YouTube videos with IDs as keys
    """
    videos = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Look for video results with links to YouTube
        video_links = soup.select('a[href*="youtube.com/watch"]')
        for idx, link in enumerate(video_links):
            href = link.get('href', '')
            video_id = extract_youtube_id(href)
            if video_id:
                title_elem = link.select_one('h3')
                title = title_elem.text if title_elem else f"Video {idx+1}"
                videos[f'google_youtube_{video_id}'] = {
                    'type': 'youtube',
                    'video_id': video_id,
                    'embed_url': href,
                    'platform': 'YouTube via Google',
                    'title': title
                }
    except Exception as e:
        logger.error(f"Error extracting videos from Google search: {str(e)}")
    return videos

def extract_youtube_videos_from_bing_search(html_content: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract YouTube videos from Bing search results.
    
    Args:
        html_content: HTML content from Bing search results page
        
    Returns:
        Dict: Dictionary of YouTube videos with IDs as keys
    """
    videos = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Extract video source from Bing's JSON data
        video_data = re.search(r'videoCatalog\s*=\s*(\{.*?\});', html_content)
        if video_data:
            try:
                data = json.loads(video_data.group(1))
                if 'videos' in data and len(data['videos']) > 0:
                    for idx, video in enumerate(data['videos']):
                        source_url = video.get('contentUrl', '')
                        if 'youtube.com' in source_url or 'youtu.be' in source_url:
                            video_id = extract_youtube_id(source_url)
                            if video_id:
                                videos[f'bing_youtube_{video_id}'] = {
                                    'type': 'youtube',
                                    'video_id': video_id,
                                    'embed_url': source_url,
                                    'platform': 'YouTube via Bing',
                                    'title': video.get('name', '')
                                }
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.error(f"Error extracting videos from Bing search: {str(e)}")
    return videos

def extract_youtube_links_from_page(html_content: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract YouTube links from any HTML page.
    
    Args:
        html_content: HTML content
        
    Returns:
        Dict: Dictionary of YouTube links with IDs as keys
    """
    links = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        youtube_links = soup.select('a[href*="youtube.com/watch"], a[href*="youtu.be/"]')
        for idx, link in enumerate(youtube_links):
            href = link.get('href', '')
            video_id = extract_youtube_id(href)
            if video_id:
                links[f'link_youtube_{video_id}'] = {
                    'type': 'youtube',
                    'video_id': video_id,
                    'embed_url': href,
                    'platform': 'YouTube link',
                    'title': link.text.strip() if link.text else 'Linked YouTube video'
                }
    except Exception as e:
        logger.error(f"Error extracting YouTube links: {str(e)}")
    return links

def detect_autoplay_content_from_html(html_content: str, current_video_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Detect autoplay content from YouTube or other video platform HTML.
    
    Args:
        html_content: HTML content of the video page
        current_video_id: ID of the current video to compare against
        
    Returns:
        Dict: Information about detected autoplay content
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract autoplay video info
        autoplay_info = {}
        
        # Look for "Up next" section and video links
        next_links = soup.select('a[href*="watch?v="]')
        
        for link in next_links[:5]:  # Check the first few suggestions
            href = link.get('href', '')
            if 'watch?v=' in href:
                video_id = href.split('watch?v=')[-1].split('&')[0]
                if video_id and video_id != current_video_id:
                    # Found different video that might autoplay
                    title_elem = link.select_one('span')
                    title = title_elem.text if title_elem else "Unknown video"
                    
                    autoplay_info = {
                        'has_autoplay': True,
                        'video_id': video_id,
                        'title': title,
                        'url': f"https://www.youtube.com/watch?v={video_id}"
                    }
                    break
        
        if not autoplay_info:
            return {'has_autoplay': False}
            
        return autoplay_info
        
    except Exception as e:
        logger.error(f"Error detecting autoplay content: {str(e)}")
        return {'has_autoplay': False, 'error': str(e)}

def extract_opengraph_metadata(html_content: str) -> Dict[str, Any]:
    """
    Extract OpenGraph metadata from HTML content.
    
    Args:
        html_content: HTML content string
        
    Returns:
        Dict: Dictionary of OpenGraph metadata
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        metadata = {}
        
        # Extract OpenGraph tags
        og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
        for tag in og_tags:
            property_name = tag.get('property', '').replace('og:', '')
            content = tag.get('content', '')
            if property_name and content:
                metadata[property_name] = content
                
        # Extract title if not in OpenGraph
        if 'title' not in metadata:
            title_tag = soup.find('title')
            if title_tag and title_tag.text:
                metadata['title'] = title_tag.text
                
        # Extract description if not in OpenGraph
        if 'description' not in metadata:
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                metadata['description'] = desc_tag.get('content', '')
                
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting OpenGraph metadata: {str(e)}")
        return {}
