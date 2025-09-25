"""
Entertainment Content Classifier

This module provides a specialized classifier for entertainment content like
movies, TV shows, gaming, and other media content.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from ..base_classifier import ContentClassifier

# Set up logging
logger = logging.getLogger(__name__)


class EntertainmentClassifier(ContentClassifier):
    """
    Classifier for entertainment content like movies, TV shows, and games.
    
    This classifier identifies entertainment websites and content based on
    domain patterns and URL paths.
    """
    
    def __init__(self):
        """Initialize the entertainment classifier."""
        self.logger = logging.getLogger(__name__)
        
        # Entertainment domains
        self.entertainment_domains = [
            # Video streaming
            # Removed 'youtube.com', 'youtu.be' as they are handled by YouTubeClassifier
            'netflix.com', 'hulu.com', 
            'disneyplus.com', 'hbomax.com', 'primevideo.com',
            'peacocktv.com', 'paramountplus.com', 'crunchyroll.com',
            
            # Movies and TV info
            'imdb.com', 'rottentomatoes.com', 'metacritic.com', 'letterboxd.com',
            'themoviedb.org', 'tvguide.com', 'tvtropes.org',
            
            # Gaming
            'twitch.tv', 'ign.com', 'gamespot.com', 'polygon.com', 'kotaku.com',
            'steam.com', 'steamcommunity.com', 'epicgames.com', 'gog.com',
            
            # Books and fiction
            'goodreads.com', 'audible.com', 'wattpad.com', 'fanfiction.net',
            'archiveofourown.org',
            
            # Social media entertainment
            'tiktok.com', 'instagram.com', 'pinterest.com', 'reddit.com',
            'buzzfeed.com', '9gag.com', 'imgur.com','facebook.com','twitter.com',
        ]
        
        # Entertainment URL patterns
        self.entertainment_patterns = [
            # Movies and TV
            '/movie/', '/title/', '/show/', '/watch/', '/film/',
            '/tv/', '/series/', '/episode/', '/season/', '/trailer/',
            
            # Books and fiction
            '/book/', '/novel/', '/fiction/', '/literature/',
            
            # Gaming
            '/game/', '/gaming/', '/play/', '/steam/', '/dlc/',
            
            # General entertainment
            '/entertainment/', '/celebrity/', '/hollywood/', '/bollywood/',
            '/anime/', '/manga/', '/comic/'
        ]
        
        # Entertainment keywords
        self.entertainment_keywords = [
            "movie", "film", "series", "episode", "season", "trailer",
            "watch", "stream", "netflix", "hulu", "disney+", "hbo",
            "tv show", "television", "comedy", "drama", "action",
            "game", "gaming", "playstation", "xbox", "nintendo", "steam",
            "novel", "fiction", "fanfic", "harry potter", "marvel", "dc",
            "anime", "manga", "comic", "meme", "funny", "humor",
            "celebrity", "actor", "actress", "director", "hollywood",
            "entertainment", "tiktok", "youtube", "viral", "trending"
        ]
        
    @property
    def priority(self) -> int:
        """Return priority (higher = checked first)."""
        return 90  # Very high priority
        
    def can_classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> bool:
        """
        Determine if this classifier can handle the given content.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            bool: True if this is entertainment content
        """
        # Extract domain and path
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Explicitly exclude YouTube domains to avoid classification conflict
            normalized_domain = domain.replace('www.', '')
            if 'youtube.com' in normalized_domain or 'youtu.be' in normalized_domain:
                return False
                
            # Check domain
            for ent_domain in self.entertainment_domains:
                if ent_domain in normalized_domain:
                    return True
                
            # Check path patterns
            for pattern in self.entertainment_patterns:
                if pattern in path:
                    return True
                    
            # Check for keywords in the URL
            for keyword in self.entertainment_keywords:
                if keyword in url.lower():
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error in can_classify: {str(e)}")
            return False
        
    def classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Classify the entertainment content.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            Dict with standardized classification result
        """
        # Parse URL to get more information
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Normalize domain
        normalized_domain = domain.replace('www.', '')
        
        # Special handling for Netflix - always classified as distraction in old classifier
        if 'netflix.com' in normalized_domain:
            return self.create_result(
                classification="distraction",
                reason="Netflix streaming service",
                confidence=0.95,  # Very high confidence
                metadata={
                    "domain": normalized_domain,
                    "classifier": "EntertainmentClassifier",
                    "category": "streaming_video"
                }
            )
        
        # Match domain and get more specific category if possible
        entertainment_type = "general entertainment"
        confidence = 0.85
        
        # Identify the type of entertainment more specifically
        if any(movie_domain in normalized_domain for movie_domain in 
               ['imdb.com', 'rottentomatoes.com', 'metacritic.com']):
            entertainment_type = "movie/TV information"
            confidence = 0.95
            
        elif any(video_domain in normalized_domain for video_domain in 
                 ['youtube.com', 'youtu.be', 'netflix.com', 'hulu.com']):
            entertainment_type = "video streaming"
            confidence = 0.95
            
        elif any(game_domain in normalized_domain for game_domain in 
                 ['twitch.tv', 'ign.com', 'steam.com']):
            entertainment_type = "gaming"
            confidence = 0.95
            
        elif any(book_domain in normalized_domain for book_domain in 
                 ['goodreads.com', 'audible.com', 'wattpad.com']):
            entertainment_type = "books/fiction"
            confidence = 0.95
            
        # Also check path for more information
        if any(movie_pattern in path for movie_pattern in 
               ['/movie/', '/title/', '/film/', '/tv/', '/series/']):
            entertainment_type = "movie/TV content"
            confidence = 0.9
            
        elif any(game_pattern in path for game_pattern in 
                 ['/game/', '/gaming/', '/play/']):
            entertainment_type = "gaming content"
            confidence = 0.9
            
        # Return result
        return self.create_result(
            classification="distraction",
            reason=f"Entertainment content: {entertainment_type}",
            confidence=confidence,
            metadata={
                "entertainment_type": entertainment_type,
                "domain": domain
            }
        )


# Create instance
entertainment_classifier = EntertainmentClassifier()
