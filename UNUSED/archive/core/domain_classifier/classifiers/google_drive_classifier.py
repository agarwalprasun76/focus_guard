"""
Google Drive Classifier

This module provides a specialized classifier for Google Drive and Google Docs content.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urlparse, parse_qs

from ..base_classifier import ContentClassifier
from ..metadata import metadata_fetcher

# Set up logging
logger = logging.getLogger(__name__)


class GoogleDriveClassifier(ContentClassifier):
    """
    Classifier for Google Drive and Google Docs content.
    
    This classifier identifies and classifies Google Drive documents, sheets, 
    presentations, and other file types based on URL and metadata.
    """
    
    def __init__(self):
        """Initialize the Google Drive classifier."""
        # Use the singleton metadata_fetcher instance
        self.metadata_fetcher = metadata_fetcher
        
        # Map Google Drive MIME types to classifications
        self.mime_type_classifications = {
            # Documents - typically useful
            'application/vnd.google-apps.document': ("useful", 0.8),
            'application/vnd.google-apps.spreadsheet': ("useful", 0.8),
            'application/vnd.google-apps.presentation': ("useful", 0.8),
            'application/vnd.google-apps.form': ("useful", 0.8),
            'application/vnd.google-apps.jam': ("useful", 0.8),
            'application/vnd.google-apps.site': ("useful", 0.8),
            
            # Potentially distracting content
            'application/vnd.google-apps.drawing': ("neutral", 0.7),
            'application/vnd.google-apps.map': ("neutral", 0.7),
            
            # Default for unknown types
            'default': ("neutral", 0.6)
        }
        
        # File extension classifications
        self.extension_classifications = {
            # Documents - typically useful
            'pdf': ("useful", 0.8),
            'doc': ("useful", 0.8),
            'docx': ("useful", 0.8),
            'xls': ("useful", 0.8),
            'xlsx': ("useful", 0.8),
            'ppt': ("useful", 0.8),
            'pptx': ("useful", 0.8),
            'txt': ("useful", 0.7),
            
            # Code files - typically useful
            'py': ("useful", 0.8),
            'js': ("useful", 0.8),
            'html': ("useful", 0.8),
            'css': ("useful", 0.8),
            'java': ("useful", 0.8),
            'c': ("useful", 0.8),
            'cpp': ("useful", 0.8),
            
            # Potentially distracting content
            'mp3': ("distraction", 0.7),
            'mp4': ("distraction", 0.7),
            'avi': ("distraction", 0.7),
            'mov': ("distraction", 0.7),
            'wmv': ("distraction", 0.7),
            'jpg': ("neutral", 0.6),
            'jpeg': ("neutral", 0.6),
            'png': ("neutral", 0.6),
            'gif': ("neutral", 0.6),
            
            # Default for unknown extensions
            'default': ("neutral", 0.6)
        }
    
    @property
    def priority(self) -> int:
        """Return priority (higher = checked first)."""
        return 85  # High priority, between entertainment and publications
        
    def can_classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> bool:
        """
        Determine if this classifier can handle the given content.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            bool: True if this is Google Drive content
        """
        # Check for Google Drive domains
        google_drive_domains = [
            'drive.google.com',
            'docs.google.com',
            'sheets.google.com',
            'slides.google.com',
            'forms.google.com'
        ]
        
        return any(domain == gdrive_domain or domain.endswith('.' + gdrive_domain) 
                   for gdrive_domain in google_drive_domains)
        
    def classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Classify the Google Drive content.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            Dict with standardized classification result
        """
        try:
            # Extract file ID from URL
            file_id = self._extract_file_id(url, domain)
            
            if not file_id:
                return self.create_result(
                    classification="neutral",
                    reason="Unable to extract Google Drive file ID",
                    confidence=0.6,
                    metadata={"domain": domain}
                )
                
            # Fetch metadata for the file
            try:
                drive_metadata = self.metadata_fetcher.fetch_metadata_for_google_drive(file_id)
            except Exception as e:
                logger.warning(f"Error fetching Google Drive metadata: {str(e)}")
                # Fall back to URL-based classification
                return self._classify_by_url(url, domain, file_id)
                
            if not drive_metadata:
                return self._classify_by_url(url, domain, file_id)
                
            # Get classification based on MIME type
            mime_type = drive_metadata.get('mimeType', '')
            classification, confidence = self.mime_type_classifications.get(
                mime_type, 
                self.mime_type_classifications['default']
            )
            
            # Adjust classification based on title keywords
            title = drive_metadata.get('title', '')
            if title:
                title_lower = title.lower()
                
                # Check for work/study keywords
                work_keywords = ["report", "assignment", "homework", "study", "notes", 
                                "research", "thesis", "project", "analysis", "plan", "budget"]
                                
                # Check for entertainment keywords
                entertainment_keywords = ["game", "movie", "music", "song", "video", 
                                        "party", "vacation", "holiday", "fun"]
                
                if any(keyword in title_lower for keyword in work_keywords):
                    classification = "useful"
                    confidence = max(confidence, 0.75)
                    
                elif any(keyword in title_lower for keyword in entertainment_keywords):
                    classification = "distraction"
                    confidence = max(confidence, 0.7)
            
            return self.create_result(
                classification=classification,
                reason=f"Google Drive {drive_metadata.get('title', 'document')} ({mime_type})",
                confidence=confidence,
                metadata={
                    "file_id": file_id,
                    "mime_type": mime_type,
                    "title": drive_metadata.get('title', ''),
                    "source": "google_drive"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in Google Drive classifier: {str(e)}")
            return self.create_result(
                classification="error",
                reason=f"Error in Google Drive classifier: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e), "domain": domain}
            )
            
    def _extract_file_id(self, url: str, domain: str) -> Optional[str]:
        """Extract the Google Drive file ID from the URL."""
        try:
            parsed = urlparse(url)
            path = parsed.path
            query = parse_qs(parsed.query)
            
            # Different URL patterns for Google Drive
            if domain == 'drive.google.com':
                # Pattern: drive.google.com/file/d/{fileId}/view
                if '/file/d/' in path:
                    file_id = path.split('/file/d/')[1].split('/')[0]
                    return file_id
                    
                # Pattern: drive.google.com/open?id={fileId}
                elif path == '/open' and 'id' in query:
                    return query['id'][0]
                    
                # Pattern: drive.google.com/uc?id={fileId}
                elif path == '/uc' and 'id' in query:
                    return query['id'][0]
                    
            # Google Docs URLs
            elif domain in ['docs.google.com', 'sheets.google.com', 'slides.google.com']:
                # Pattern: docs.google.com/document/d/{fileId}/edit
                if '/d/' in path:
                    file_id = path.split('/d/')[1].split('/')[0]
                    return file_id
                    
            # Try the generic ID extraction for other cases
            id_match = re.search(r'id=([^&]+)', url)
            if id_match:
                return id_match.group(1)
                
            return None
                
        except Exception as e:
            logger.error(f"Error extracting Google Drive file ID: {str(e)}")
            return None
            
    def _classify_by_url(self, url: str, domain: str, file_id: Optional[str] = None) -> Dict[str, Any]:
        """Classify based on URL when metadata is not available."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Determine document type from URL
        doc_type = "document"
        if "document" in path:
            doc_type = "document"
        elif "spreadsheet" in path or "sheets" in domain:
            doc_type = "spreadsheet"
        elif "presentation" in path or "slides" in domain:
            doc_type = "presentation"
        elif "form" in path or "forms" in domain:
            doc_type = "form"
        
        # Extract file extension if present
        extension = None
        if "." in path.split("/")[-1]:
            extension = path.split("/")[-1].split(".")[-1].lower()
            
        # Classify based on extension if available
        if extension:
            classification, confidence = self.extension_classifications.get(
                extension,
                self.extension_classifications['default']
            )
        else:
            # Default classification for Google Drive documents
            classification = "useful"
            confidence = 0.7
            
        return self.create_result(
            classification=classification,
            reason=f"Google Drive {doc_type}",
            confidence=confidence,
            metadata={
                "file_id": file_id,
                "doc_type": doc_type,
                "extension": extension,
                "source": "google_drive",
                "classification_method": "url_based"
            }
        )


# Create instance
google_drive_classifier = GoogleDriveClassifier()
