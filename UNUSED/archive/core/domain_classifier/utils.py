"""
Domain Classification Utilities

This module provides helper functions for URL parsing and classification.
"""

import re
from typing import Union
from urllib.parse import urlparse, parse_qs

# Domain extraction regex
DOMAIN_REGEX = re.compile(r'^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/\n]+)')

# URL patterns for different platforms
YOUTUBE_URL_PATTERNS = [
    r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([^&\?\/]+)',
    r'youtube\.com\/watch.*?\?v=([^&]+)',
    r'youtube\.com\/shorts\/([^&\?\/]+)'
]

GOOGLE_SEARCH_PATTERNS = [
    r'google\.com\/search',
    r'google\.[a-z]{2,}\/search'
]

BING_SEARCH_PATTERNS = [
    r'bing\.com\/search',
    r'bing\.com\/videos'
]

# Content classification constants
EDUCATIONAL_KEYWORDS = [
    "education", "educational", "learn", "tutorial", "course", 
    "lecture", "academic", "university", "school", "teach",
    "howto", "science", "math", "engineering", "programming",
    "coding", "development", "history", "documentary", "ted",
    "violin", "orchestra", "piano", "business", "finance", "quarterly", 
    "review", "analysis", "corporate", "management", "strategy", "professional"
]

ENTERTAINMENT_KEYWORDS = [
    "entertainment", "funny", "comedy", "prank", "challenge", 
    "vlog", "gaming", "game", "play", "lets play", "stream",
    "music", "song", "concert", "official", "trailer", "movie",
    "show", "series", "episode", "highlights", "compilation",
    "reaction", "review", "unboxing", "haul", "makeup", "beauty"
]

EDUCATIONAL_CHANNELS = [
    "Khan Academy", "Crash Course", "TED", "TED-Ed", "MIT OpenCourseWare",
    "Vsauce", "SciShow", "Veritasium", "3Blue1Brown", "Physics Girl",
    "Computerphile", "Numberphile", "Minute Physics", "Code.org",
    "The Coding Train", "freeCodeCamp.org", "Two Minute Papers", "Code Academy"
]


def extract_domain(url: str) -> str:
    """
    Extract the domain part from a URL.
    
    Args:
        url: The URL to extract domain from
        
    Returns:
        str: Domain name without subdomains (e.g. example.com)
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain
    except:
        return ""


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
        elif 'youtu.be' in domain:
            path = parsed_url.path.lstrip('/')
            return path if path else None
        
        return None
    except:
        return None


def is_drive_url(url: str) -> bool:
    """
    Check if the URL is a Google Drive URL.
    
    Args:
        url: URL to check
        
    Returns:
        bool: True if Google Drive URL, False otherwise
    """
    domain = extract_domain(url)
    return 'drive.google.com' in domain


def extract_host_without_www(url: str) -> str:
    """
    Extract the host from a URL without www. prefix.
    
    Args:
        url: URL to extract host from
        
    Returns:
        str: Host name without www.
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        
        if host.startswith('www.'):
            host = host[4:]
            
        return host
    except:
        return ""


def normalize_url(url: str) -> str:
    """
    Normalize a URL by ensuring it has a scheme.
    
    Args:
        url: URL to normalize
        
    Returns:
        str: Normalized URL
    """
    if not url:
        return url
        
    if not url.startswith(('http://', 'https://')):
        return 'https://' + url
        
    return url


def get_url_path_components(url: str) -> list:
    """
    Get path components from a URL.
    
    Args:
        url: URL to extract path components from
        
    Returns:
        list: Path components
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        return path.split('/') if path else []
    except:
        return []


# ---- URL Pattern Detection Utilities ----

def is_search_results_page(url: str) -> bool:
    """
    Determine if URL is from a search engine results page.
    
    Args:
        url: URL to check
        
    Returns:
        bool: True if URL is from a search results page
    """
    if not url:
        return False
    
    # Google search patterns
    for pattern in GOOGLE_SEARCH_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
            
    # Bing search patterns
    for pattern in BING_SEARCH_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
            
    return False

def get_platform_from_url(url: str) -> str:
    """
    Extract platform name from URL.
    
    Args:
        url: URL to extract platform from
        
    Returns:
        str: Platform name (Google, Bing, YouTube, etc.) or empty string if unknown
    """
    if not url:
        return ""
        
    domain = extract_domain(url)
    
    if not domain:
        return ""
        
    # Extract platform from domain
    if 'google' in domain:
        return 'Google'
    elif 'bing' in domain:
        return 'Bing'
    elif 'youtube' in domain or 'youtu.be' in domain:
        return 'YouTube'
    elif 'facebook' in domain:
        return 'Facebook'
    elif 'twitter' in domain:
        return 'Twitter'
    elif 'linkedin' in domain:
        return 'LinkedIn'
    elif 'reddit' in domain:
        return 'Reddit'
    else:
        # Try to extract a reasonable platform name from domain
        parts = domain.split('.')
        if parts and len(parts[0]) > 1:
            return parts[0].capitalize()
        else:
            return domain.capitalize()

# ---- Content Classification Utilities ----

def count_keywords_in_text(text: str, keywords: list) -> int:
    """
    Count how many keywords appear in text.
    Uses whole-word matching to avoid false positives from substring matches.
    
    Args:
        text: Text to search in
        keywords: List of keywords to search for
        
    Returns:
        int: Number of keywords found in text
    """
    import re
    if not text or not keywords:
        return 0
        
    text = text.lower()
    count = 0
    
    for keyword in keywords:
        # Use word boundary \b to ensure we match whole words only
        # This prevents matching 'ted' inside 'directed'
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, text):
            count += 1
            
    return count

def calculate_educational_score(metadata: dict) -> float:
    """
    Calculate educational score based on metadata.
    
    Args:
        metadata: Content metadata
        
    Returns:
        float: Educational score between 0.0 and 1.0
    """
    if not metadata:
        return 0.0
        
    score = 0.0
    total_weight = 0.0
    
    # Check title (highest weight)
    if 'title' in metadata and metadata['title']:
        title_count = count_keywords_in_text(metadata['title'], EDUCATIONAL_KEYWORDS)
        title_weight = 3.0
        score += title_count * title_weight
        total_weight += title_weight
    
    # Check channel (high weight for educational channels)
    if 'channel' in metadata and metadata['channel']:
        if any(channel.lower() in metadata['channel'].lower() for channel in EDUCATIONAL_CHANNELS):
            score += 5.0
        channel_weight = 2.0
        total_weight += channel_weight
    
    # Check description
    if 'description' in metadata and metadata['description']:
        desc_count = count_keywords_in_text(metadata['description'], EDUCATIONAL_KEYWORDS)
        desc_weight = 1.5
        score += desc_count * desc_weight
        total_weight += desc_weight
    
    # Check tags
    if 'tags' in metadata and metadata['tags'] and isinstance(metadata['tags'], list):
        tags_text = ' '.join(str(tag) for tag in metadata['tags'])
        tag_count = count_keywords_in_text(tags_text, EDUCATIONAL_KEYWORDS)
        tag_weight = 1.0
        score += tag_count * tag_weight
        total_weight += tag_weight
    
    # Normalize score to 0.0-1.0 range
    if total_weight > 0:
        return min(1.0, score / (total_weight * 2))
    else:
        return 0.0

# ---- Enhanced metadata and classification utilities ----

def format_metadata(metadata: dict) -> dict:
    """
    Format and clean metadata for display or processing.
    
    Args:
        metadata: Raw metadata dictionary from MetadataFetcher
        
    Returns:
        dict: Cleaned and formatted metadata with standardized fields
    """
    if not metadata or not isinstance(metadata, dict):
        return {}
        
    formatted = {}
    
    # Copy basic fields
    for key in ['title', 'description', 'channel', 'tags', 'view_count',
               'embedded', 'embedded_on_domain', 'embedding_platform', 'original_url']:
        if key in metadata:
            formatted[key] = metadata[key]
    
    # Format tags if present
    if 'tags' in formatted and isinstance(formatted['tags'], list):
        # Ensure all tags are strings and limit length if excessive
        formatted['tags'] = [str(tag) for tag in formatted['tags'][:20]]
    
    # Truncate description if too long
    if 'description' in formatted and isinstance(formatted['description'], str) and len(formatted['description']) > 1000:
        formatted['description'] = formatted['description'][:1000] + '...'
    
    # Add detection flags
    formatted['has_metadata'] = len(formatted) > 0
    
    # Add content type if possible to determine
    if 'channel' in metadata or 'video_id' in metadata:
        formatted['content_type'] = 'video'
    elif 'document_type' in metadata:
        formatted['content_type'] = metadata['document_type']
    
    return formatted


def get_embedded_info(classification_result: dict) -> dict:
    """
    Extract embedded content information from a classification result.
    
    Args:
        classification_result: Dictionary with classification results
        
    Returns:
        dict: Information about embedded content if present
    """
    embedded_info = {}
    
    if not classification_result or not isinstance(classification_result, dict):
        return embedded_info
    
    # Check if this is embedded content
    if classification_result.get('embedded', False):
        embedded_info['is_embedded'] = True
        
        # Copy embedding details
        for key in ['embedded_on_domain', 'embedding_platform', 'original_url']:
            if key in classification_result:
                embedded_info[key] = classification_result[key]
                
        # Add source information
        if 'embedded_on_domain' in classification_result:
            domain = classification_result['embedded_on_domain']
            if 'google' in domain:
                embedded_info['source'] = 'Google Search'
            elif 'bing' in domain:
                embedded_info['source'] = 'Bing Search'
            else:
                embedded_info['source'] = f'{domain.capitalize()} Embed'
    else:
        embedded_info['is_embedded'] = False
    
    return embedded_info


def get_autoplay_info(classification_result: dict) -> dict:
    """
    Extract autoplay information from a classification result.
    
    Args:
        classification_result: Dictionary with classification results
        
    Returns:
        dict: Information about autoplay content if present
    """
    autoplay_info = {}
    
    if not classification_result or not isinstance(classification_result, dict):
        return autoplay_info
    
    # Check for autoplay content
    if classification_result.get('has_autoplay', False):
        autoplay_info['has_autoplay'] = True
        
        # Copy autoplay details if present
        if 'autoplay_info' in classification_result and isinstance(classification_result['autoplay_info'], dict):
            for key, value in classification_result['autoplay_info'].items():
                autoplay_info[key] = value
    else:
        autoplay_info['has_autoplay'] = False
    
    return autoplay_info


def summarize_classification(classification_result: dict) -> dict:
    """
    Create a summary of classification results, including embedded content
    and autoplay detection information.
    
    Args:
        classification_result: Dictionary with classification results
        
    Returns:
        dict: Summary of classification with key information
    """
    if not classification_result or not isinstance(classification_result, dict):
        return {'classification': 'unknown', 'confidence': 0, 'error': 'Invalid classification result'}
    
    summary = {
        'classification': classification_result.get('classification', 'unknown'),
        'confidence': classification_result.get('confidence', 0),
        'classifier': classification_result.get('classifier', 'unknown'),
    }
    
    # Add metadata availability flag
    summary['has_metadata'] = bool(classification_result.get('metadata', {}))
    
    # Get embedded content information
    embedded_info = get_embedded_info(classification_result)
    if embedded_info.get('is_embedded', False):
        summary['embedded'] = True
        summary['embedded_info'] = embedded_info
    
    # Get autoplay information
    autoplay_info = get_autoplay_info(classification_result)
    if autoplay_info.get('has_autoplay', False):
        summary['has_autoplay'] = True
        summary['autoplay_info'] = autoplay_info
    
    return summary
