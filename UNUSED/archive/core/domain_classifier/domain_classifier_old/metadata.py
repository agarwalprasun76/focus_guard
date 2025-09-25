"""
Metadata Handler

This module provides functionality to fetch and process metadata from various sources
like Google Drive, YouTube, and general web pages.
"""

import re
import logging
from typing import Dict, Optional, Any
from urllib.parse import urlparse, parse_qs

# Third-party imports (make sure to add these to requirements.txt)
try:
    import requests
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from bs4 import BeautifulSoup
    import yt_dlp
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False
    logging.warning("Some dependencies not found. Metadata fetching will be limited.")

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
            
            # Get file content for text files
            content = ""
            if file_metadata.get('mimeType', '').startswith('text/'):
                try:
                    content = service.files().get_media(fileId=file_id).execute().decode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Could not fetch file content: {str(e)}")
            
            return {
                "title": file_metadata.get('name', ''),
                "description": file_metadata.get('description', ''),
                "mimeType": file_metadata.get('mimeType', ''),
                "url": file_metadata.get('webViewLink', ''),
                "owner": file_metadata.get('owners', [{}])[0].get('displayName', '') if file_metadata.get('owners') else '',
                "modifiedTime": file_metadata.get('modifiedTime', ''),
                "size": int(file_metadata.get('size', 0)) if file_metadata.get('size') else 0,
                "content": content,
                "type": self._get_file_type(file_metadata.get('mimeType', ''))
            }
            
        except HttpError as e:
            self.logger.error(f"Error fetching Google Drive metadata: {str(e)}")
            return {"error": f"Google Drive API error: {str(e)}"}
        except Exception as e:
            self.logger.error(f"Unexpected error in get_drive_metadata: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
    
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