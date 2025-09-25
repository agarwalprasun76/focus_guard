"""
Metadata Handler

This module provides functionality to fetch and process metadata from various sources
like Google Drive, YouTube, and general web pages.
"""

import re
import json
import logging
import requests
from urllib.parse import urlparse, parse_qs
from typing import Dict, Optional, Any

# Third-party imports (make sure to add these to requirements.txt)
try:
    from bs4 import BeautifulSoup
    import yt_dlp
    import google.auth
    from googleapiclient.discovery import build
    from core.domain_classifier.url_resolver import URLResolver, EmbeddedContentAnalyzer
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False
    logging.warning("Some dependencies not found. Metadata fetching will be limited.")

from core.logger.logger import get_logger
from core.domain_classifier.utils import extract_domain, is_youtube_url, extract_youtube_id, is_drive_url

logger = get_logger(__name__)

class MetadataFetcher:
    """Handles fetching metadata from various sources."""
    
    def __init__(self, google_credentials_path: str = None):
        """Initialize the metadata fetcher.
        
        Args:
            google_credentials_path: Path to Google OAuth2 credentials JSON file
        """
        self.logger = logging.getLogger(__name__)
        self.google_credentials_path = google_credentials_path
        self.drive_service = None
        self.youtube_service = None
        
    def get_drive_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get metadata for a Google Drive file.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Dict containing file metadata or error information
        """
        if not IMPORT_SUCCESS:
            self.logger.warning("Google API client not available. Using mock data.")
            return self._mock_drive_metadata()
            
        try:
            service = self._get_drive_service()
            if not service:
                return {"error": "Could not initialize Google Drive service"}
                
            # Get file metadata
            file_metadata = service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,description,webViewLink,owners,modifiedTime,size',
                supportsAllDrives=True
            ).execute()
            
            return {
                'id': file_metadata.get('id', ''),
                'name': file_metadata.get('name', ''),
                'type': file_metadata.get('mimeType', ''),
                'description': file_metadata.get('description', ''),
                'url': file_metadata.get('webViewLink', ''),
                'owner': file_metadata.get('owners', [{}])[0].get('displayName', '') if file_metadata.get('owners') else '',
                'modified': file_metadata.get('modifiedTime', ''),
                'size': file_metadata.get('size', '0')
            }
            
        except HttpError as error:
            self.logger.error(f"Google Drive API error: {error}")
            return {"error": str(error)}
        except Exception as e:
            self.logger.error(f"Error fetching Google Drive metadata: {str(e)}")
            return {"error": str(e)}
    
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
                'extract_flat': True,
                'force_generic_extractor': False
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
                    'channel': info.get('uploader', ''),
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', []),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'upload_date': info.get('upload_date')
                }
                
                self.logger.info(f"Successfully fetched metadata for YouTube video {video_id}")
                return metadata
            else:
                self.logger.warning(f"Could not extract title from YouTube video {video_id}")
                return {"error": "Metadata extraction failed"}
                
        except Exception as e:
            self.logger.error(f"Error fetching YouTube metadata: {str(e)}")
            # Fallback with basic metadata
            return {
                "error": str(e),
                "video_id": video_id
            }

    def get_metadata_from_url(self, url: str) -> Dict[str, Any]:
        """Get metadata for a URL (could be a Drive file, YouTube video, or generic web page).
        
        Args:
            url: URL to fetch metadata for
            
        Returns:
            Dict containing metadata or error information
        """
        if not IMPORT_SUCCESS:
            logger.warning("Required packages not installed for advanced URL resolution")
            return self._fallback_metadata_extraction(url)
            
        try:
            # First, check if the URL redirects somewhere
            resolver = URLResolver()
            url_info = resolver.resolve_url(url)
            
            # If we had a redirect, use the final URL for classification
            if url_info.get('is_redirect'):
                final_url = url_info.get('final_url')
                logger.info(f"URL {url} redirected to {final_url}")
                url = final_url
            
            # Get the domain for this URL
            domain = extract_domain(url)
            
            # Direct platform handling
            if is_youtube_url(url):
                # Direct YouTube URL
                video_id = extract_youtube_id(url)
                if not video_id:
                    return {"error": "Could not extract YouTube video ID"}
                return self.fetch_metadata_for_youtube(video_id)
                
            elif is_drive_url(url):
                # Google Drive
                file_id = self._extract_drive_file_id(url)
                if not file_id:
                    return {"error": "Could not extract Google Drive file ID"}
                return self.get_drive_metadata(file_id)
            
            else:
                # Check if this URL has embedded content (like YouTube videos on Bing)
                analyzer = EmbeddedContentAnalyzer()
                embedded_content = analyzer.extract_embedded_content(url)
                
                # If we found YouTube content, get its metadata
                for content_id, content_info in embedded_content.items():
                    if content_info.get('type') == 'youtube':
                        video_id = content_info.get('video_id')
                        if video_id:
                            youtube_metadata = self.fetch_metadata_for_youtube(video_id)
                            
                            # Add embedding context to the metadata
                            if youtube_metadata:
                                youtube_metadata['embedded_on_domain'] = domain
                                youtube_metadata['original_url'] = url
                                youtube_metadata['embedding_platform'] = content_info.get('platform', 'Unknown')
                                return youtube_metadata
                
                # If no embedded content was found, treat as a generic webpage
                return self.get_webpage_metadata(url)
                
        except Exception as e:
            logger.error(f"Error fetching metadata for URL {url}: {str(e)}")
            return {"error": f"Metadata fetching failed: {str(e)}"}
                
    def _extract_drive_file_id(self, url: str) -> Optional[str]:
        """Extract Google Drive file ID from a URL
        
        Args:
            url: Google Drive URL
            
        Returns:
            str or None: File ID if found, None otherwise
        """
        parsed_url = urlparse(url)
        
        # Extract file ID based on URL format
        path_parts = parsed_url.path.split('/')
        if '/d/' in parsed_url.path and len(path_parts) > path_parts.index('d') + 1:
            return path_parts[path_parts.index('d') + 1]
            
        # Alternative format with id query parameter
        query_params = parse_qs(parsed_url.query)
        if 'id' in query_params and query_params['id'][0]:
            return query_params['id'][0]
            
        return None
        
    def _fallback_metadata_extraction(self, url: str) -> Dict[str, Any]:
        """Basic metadata extraction when advanced features are unavailable
        
        Args:
            url: URL to extract metadata from
            
        Returns:
            Dict containing basic metadata
        """
        # Basic URL parsing
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Extract YouTube ID if applicable
        video_id = None
        if 'youtube.com' in domain or 'youtu.be' in domain:
            if 'youtube.com' in domain:
                query_params = parse_qs(parsed_url.query)
                video_id = query_params.get('v', [''])[0]
            else:  # youtu.be
                video_id = parsed_url.path.lstrip('/')
        
        return {
            'url': url,
            'domain': domain,
            'video_id': video_id,
            'is_youtube': 'youtube.com' in domain or 'youtu.be' in domain,
            'is_drive': 'drive.google.com' in domain
        }
        
    def get_webpage_metadata(self, url: str) -> Dict[str, Any]:
        """Get metadata from a generic webpage using OpenGraph and meta tags.
        
        Args:
            url: Webpage URL
            
        Returns:
            Dict containing webpage metadata
        """
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract metadata
            metadata = {
                'url': url,
                'domain': extract_domain(url)
            }
            
            # Title
            if soup.title:
                metadata['title'] = soup.title.string.strip()
            
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc:
                metadata['description'] = meta_desc.get('content', '')
            
            # Meta keywords
            keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_tag:
                keywords = keywords_tag.get('content', '')
                metadata['keywords'] = [k.strip() for k in keywords.split(',') if k.strip()]
            
            # Open Graph data
            og_title = soup.find('meta', attrs={'property': 'og:title'})
            if og_title:
                metadata['og_title'] = og_title.get('content', '')
                
            og_type = soup.find('meta', attrs={'property': 'og:type'})
            if og_type:
                metadata['og_type'] = og_type.get('content', '')
                
            # Also check for autoplay content if this is a video site
            if 'youtube.com' in metadata['domain'] or 'vimeo.com' in metadata['domain']:
                # Use our analyzer to detect potential autoplay content
                try:
                    analyzer = EmbeddedContentAnalyzer()
                    video_id = extract_youtube_id(url) if 'youtube.com' in metadata['domain'] else None
                    autoplay_info = analyzer.detect_autoplay_content(url, current_video_id=video_id)
                    if autoplay_info and autoplay_info.get('has_autoplay'):
                        metadata['has_autoplay'] = True
                        metadata['autoplay_video'] = {
                            'id': autoplay_info.get('video_id'),
                            'title': autoplay_info.get('title'),
                            'url': autoplay_info.get('url')
                        }
                except Exception as e:
                    logger.warning(f"Error detecting autoplay content: {e}")
            
            return metadata
                
        except Exception as e:
            logger.error(f"Error fetching webpage metadata: {e}")
            return {"error": f"Failed to fetch webpage metadata: {str(e)}"}
    
    def get_youtube_metadata(self, url: str) -> Dict[str, Any]:
        """Get metadata for a YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dict containing video metadata or error information
        """
        if not IMPORT_SUCCESS:
            self.logger.warning("yt_dlp not available. Using mock data.")
            return self._mock_youtube_metadata()
            
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Extract relevant metadata
                duration = info.get('duration', 0)  # in seconds
                
                return {
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'channel': info.get('uploader', ''),
                    'duration': duration,
                    'duration_minutes': round(duration / 60, 2) if duration else 0,
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'upload_date': info.get('upload_date', ''),
                    'categories': info.get('categories', []),
                    'tags': info.get('tags', []),
                    'url': info.get('webpage_url', url),
                    'thumbnail': info.get('thumbnail', '')
                }
                
        except Exception as e:
            self.logger.error(f"Error fetching YouTube metadata: {str(e)}")
            return {"error": f"YouTube metadata error: {str(e)}"}
    
    def get_webpage_metadata(self, url: str) -> Dict[str, Any]:
        """Get metadata from a generic webpage using OpenGraph and meta tags.
        
        Args:
            url: Webpage URL
            
        Returns:
            Dict containing webpage metadata
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract OpenGraph metadata
            og_data = {}
            for tag in soup.find_all('meta', property=re.compile(r'^og:')):
                og_data[tag['property'][3:]] = tag.get('content', '')
            
            # Extract standard meta tags
            meta_data = {}
            for tag in soup.find_all('meta'):
                name = tag.get('name', tag.get('property', '')).lower()
                if name and tag.get('content'):
                    meta_data[name] = tag['content']
            
            # Get page title
            title = og_data.get('title') or soup.title.string if soup.title else ''
            
            # Get description (prefer OpenGraph, then meta description, then first paragraph)
            description = (
                og_data.get('description') or 
                meta_data.get('description') or 
                (soup.find('p') and soup.find('p').get_text()[:200] + '...')
            )
            
            # Get main content (simplified)
            content = ' '.join([p.get_text() for p in soup.find_all('p')[:5]])
            
            return {
                'title': title,
                'description': description,
                'url': og_data.get('url', url),
                'image': og_data.get('image', ''),
                'site_name': og_data.get('site_name', urlparse(url).netloc),
                'type': og_data.get('type', 'website'),
                'content': content[:1000],  # First 1000 chars of content
                'meta': meta_data
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching webpage metadata: {str(e)}")
            return {"error": f"Webpage metadata error: {str(e)}"}
    
    def _get_drive_service(self):
        """Get an authenticated Google Drive service instance."""
        if self.drive_service:
            return self.drive_service
            
        if not self.google_credentials_path:
            self.logger.warning("No Google credentials provided")
            return None
            
        try:
            creds = None
            # The file token.json stores the user's access and refresh tokens
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json')
            
            # If there are no (valid) credentials, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.google_credentials_path,
                        ['https://www.googleapis.com/auth/drive.readonly']
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            
            self.drive_service = build('drive', 'v3', credentials=creds)
            return self.drive_service
            
        except Exception as e:
            self.logger.error(f"Error initializing Google Drive service: {str(e)}")
            return None
    
    @staticmethod
    def _get_file_type(mime_type: str) -> str:
        """Convert MIME type to a simple file type."""
        if not mime_type:
            return 'unknown'
            
        if 'document' in mime_type or 'text/plain' in mime_type:
            return 'document'
        elif 'spreadsheet' in mime_type:
            return 'spreadsheet'
        elif 'presentation' in mime_type:
            return 'presentation'
        elif 'pdf' in mime_type:
            return 'pdf'
        elif 'image' in mime_type:
            return 'image'
        elif 'video' in mime_type:
            return 'video'
        elif 'audio' in mime_type:
            return 'audio'
        else:
            return 'file'
    
    @staticmethod
    def _mock_drive_metadata() -> Dict[str, Any]:
        """Return mock Google Drive metadata for testing."""
        return {
            "title": "Harry Potter fanfic.pdf",
            "description": "Fan fiction about Harry Potter",
            "mimeType": "application/pdf",
            "url": "https://drive.google.com/file/d/mock123/view",
            "owner": "Test User",
            "modifiedTime": "2023-01-01T12:00:00.000Z",
            "size": 1024,
            "content": "",
            "type": "pdf"
        }
    
    @staticmethod
    def _mock_youtube_metadata() -> Dict[str, Any]:
        """Return mock YouTube metadata for testing."""
        return {
            'title': 'Top 10 Funniest Moments in Harry Potter',
            'description': 'Enjoy a laugh with this Harry Potter compilation',
            'channel': 'Movie Clips',
            'duration': 600,
            'duration_minutes': 10.0,
            'view_count': 12345,
            'like_count': 1000,
            'upload_date': '20220101',
            'categories': ['Entertainment'],
            'tags': ['harry potter', 'funny', 'compilation'],
            'url': 'https://www.youtube.com/watch?v=mock123',
            'thumbnail': 'https://i.ytimg.com/vi/mock123/hqdefault.jpg'
        }

# Singleton instance for easy import
metadata_fetcher = MetadataFetcher()