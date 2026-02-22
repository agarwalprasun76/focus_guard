"""
YouTube metadata fetcher using yt-dlp.
Moved from UNUSED/archive/core/domain_classifier/metadata.py
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Create a silent logger for yt-dlp to suppress all output
class SilentLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def critical(self, msg): pass

silent_logger = SilentLogger()

# Try to import yt-dlp
try:
    import yt_dlp
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False
    logger.warning("yt-dlp not available. YouTube metadata fetching will be limited.")


class MetadataFetcher:
    """Handles fetching metadata from YouTube videos."""
    
    def __init__(self):
        """Initialize the metadata fetcher."""
        self.logger = logging.getLogger(__name__)
        
    def fetch_metadata_for_youtube(self, video_id: str) -> Dict[str, Any]:
        """Fetch metadata for a YouTube video.
        
        Args:
            video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
            
        Returns:
            Dict containing video metadata including title, description, channel, tags
        """
        try:
            if not IMPORT_SUCCESS:
                self.logger.warning("Required packages not installed for YouTube metadata fetching")
                return {"error": "Dependencies not installed"}
                
            # Configure yt-dlp to extract metadata only (no download)
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': False,  # Need full extraction for metadata
                'force_generic_extractor': False,
                # Add headers to avoid 403 errors
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                },
                # Reduce retry attempts to minimize error spam
                'retries': 1,
                'fragment_retries': 0,
                # Don't ignore errors - we need the metadata even with warnings
                'ignoreerrors': False,
                'no_color': True,
                'noprogress': True,
                'logger': silent_logger,  # Use our custom silent logger
            }
            
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Use yt-dlp to extract metadata
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            # Extract relevant metadata fields
            if info and 'title' in info:
                metadata = {
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'channel_title': info.get('uploader', ''),  # Use channel_title to match LLM classifier expectations
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', []),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'comment_count': info.get('comment_count'),
                    'upload_date': info.get('upload_date'),
                    'language': info.get('language', 'unknown')
                }
                
                self.logger.info(f"Successfully fetched metadata for YouTube video {video_id}: {metadata.get('title', 'Unknown')}")
                return metadata
            else:
                self.logger.warning(f"Could not extract title from YouTube video {video_id}")
                return {"error": "Metadata extraction failed"}
                
        except Exception as e:
            # Silently handle errors to avoid spam in logs
            self.logger.debug(f"YouTube metadata fetch failed for {video_id}: {str(e)}")
            # Return minimal fallback metadata that won't break classification
            return {
                "title": "Unknown Video",
                "channel_title": "Unknown Channel", 
                "description": "",
                "tags": [],
                "video_id": video_id,
                "metadata_available": False
            }

    def get_youtube_metadata(self, url: str) -> Dict[str, Any]:
        """Get metadata for a YouTube video from URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            Dict containing video metadata or error information
        """
        from focus_guard.core.utils.youtube_utils import extract_youtube_id
        
        video_id = extract_youtube_id(url)
        if not video_id:
            return {"error": "Could not extract YouTube video ID"}
            
        return self.fetch_metadata_for_youtube(video_id)


# Singleton instance for easy import
metadata_fetcher = MetadataFetcher()
