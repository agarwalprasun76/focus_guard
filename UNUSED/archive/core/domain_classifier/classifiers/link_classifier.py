"""
Link Classifier

This module provides functionality to classify links based on their path, query parameters,
and content metadata, complementing the domain-based classification with more granular analysis.
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Pattern, Tuple, Union, Any
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

# Import from parent directory
from core.domain_classifier.metadata import MetadataFetcher, metadata_fetcher
# Import the publication classifier
try:
    from core.domain_classifier.classifiers.publication_classifier import PublicationClassifier, publication_classifier
    PUBLICATION_CLASSIFIER_AVAILABLE = True
except ImportError:
    PUBLICATION_CLASSIFIER_AVAILABLE = False
    logging.warning("Publication classifier not available. Install required dependencies.")

# Set up logging
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

class LinkClassifier:
    """Classifies links as useful, distracting, or neutral."""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LinkClassifier, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, metadata_fetcher=None):
        """Initialize the link classifier.
        
        Args:
            metadata_fetcher: Optional MetadataFetcher instance. If not provided,
                           the singleton instance will be used.
        """
        if not hasattr(self, '_initialized'):
            self.metadata_fetcher = metadata_fetcher or metadata_fetcher
            self.logger = logging.getLogger(__name__)
            self._setup_patterns()
            self._setup_keywords()
            self._publication_domains = [
                'arxiv.org', 'researchgate.net', 'academia.edu', 'ssrn.com',
                'sciencedirect.com', 'springer.com', 'ieee.org', 'acm.org',
                'jstor.org', 'wiley.com', 'tandfonline.com', 'nature.com',
                'science.org', 'apa.org', 'pubmed.ncbi.nlm.nih.gov'
            ]
            self._initialized = True
    
    def _result(self, classification, reason=None, confidence=1.0, metadata=None):
        """Create a standardized result dictionary."""
        return {
            "classification": classification,
            "reason": reason,
            "confidence": min(max(confidence, 0.0), 1.0),  # Clamp between 0 and 1
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    
    def _setup_patterns(self):
        # Domain-specific patterns
        self.domain_patterns = {
            # Google Drive patterns
            "drive.google.com": {
                "distracting": [
                    r"/file/d/[^/]+/view\?.*",  # File view
                    r"/drive/folders/[^/]+",     # Folders
                    r"/drive/(u/\\d+/)?folders/[^/]+"  # Shared folders
                ],
                "useful": [
                    r"/document/d/[^/]+/edit",    # Docs
                    r"/spreadsheets/d/[^/]+/edit", # Sheets
                    r"/presentation/d/[^/]+/edit"  # Slides
                ]
            },
            # YouTube patterns
            "youtube.com": {
                "distracting": [
                    r"/watch\\?v=",       # Regular videos
                    r"/shorts/",          # Shorts
                    r"/feed/trending",    # Trending
                    r"/gaming"            # Gaming
                ],
                "useful": [
                    r"/playlist\\?list=",  # Playlists
                    r"/c/",               # Channels
                    r"/user/"             # User channels
                ]
            }
        }
    
    def _setup_keywords(self):
        # Keyword lists for content classification
        self.distraction_keywords = [
            "fanfic", "harry potter", "trailer", "gameplay", "netflix", "tiktok", 
            "meme", "comic", "entertainment", "game", "movie", "tv show", "series",
            "funny", "humor", "gaming", "video", "watch", "stream", "music", "song"
        ]
        
        self.useful_keywords = [
            "report", "slides", "research", "summary", "meeting", "notes", 
            "dashboard", "document", "presentation", "spreadsheet", "work",
            "project", "study", "paper", "thesis", "assignment", "homework",
            "journal", "conference", "proceedings", "dissertation", "article",
            "publication", "preprint", "manuscript", "academic", "scientific"
        ]
    
    def classify_link(self, url: str, domain: str) -> Dict[str, Any]:
        """Classify a link based on URL and domain.
        
        Args:
            url: Full URL to classify
            domain: Domain part of the URL
            
        Returns:
            Classification result as a dictionary with classification, confidence, and reason
        """
        # Parse URL
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parsed.query.lower()
        fragment = parsed.fragment.lower()
        
        domain_key = self._get_domain_key(domain)
        
        # Check if this is entertainment content (IMDB, etc.)
        if self._is_entertainment_content(url, domain, path):
            return self._result("distraction", f"Entertainment content from {domain}", confidence=0.9)
        
        # First check if this is a Drive or YouTube URL which need special handling
        if domain in ['drive.google.com', 'docs.google.com'] or domain.endswith('.drive.google.com'):
            # Attempt to classify Google Drive link
            if drive_file_id := self._extract_drive_file_id(url):
                return self._classify_google_drive(url, drive_file_id)
        
        if domain in ['youtube.com', 'youtu.be', 'www.youtube.com']:
            # Attempt to classify YouTube link
            if video_id := self._extract_youtube_id(url):
                return self._classify_youtube(url, video_id)
                
        # Check if this is a publication that can be classified by the publication classifier
        if publication_classifier is not None and self._is_potential_publication(url, domain, path):
            try:
                publication_result = publication_classifier.classify_link_for_focus_guard(url)
                if publication_result['confidence'] >= 0.7:  # Only use if reasonably confident
                    return publication_result
            except Exception as e:
                self.logger.exception(f"Error using publication classifier for {url}: {str(e)}")
        
        # 1. Check for distracting patterns (highest priority)
        if self._matches_patterns(domain_key, path, query, fragment, self.domain_patterns.get(domain_key, {}).get("distracting", [])):
            return self._result(
                "distraction",
                "URL matches distracting pattern",
                confidence=0.9
            )
        
        # 2. Check for useful patterns
        if self._matches_patterns(domain_key, path, query, fragment, self.domain_patterns.get(domain_key, {}).get("useful", [])):
            return self._result(
                "useful",
                "URL matches useful pattern",
                confidence=0.9
            )
        
        # 3. Check for keywords in URL
        url_text = f"{path} {query} {fragment}"
        
        # Check for distracting keywords
        distraction_score = self._score_keywords(url_text, self.distraction_keywords)
        if distraction_score > 0:
            return self._result(
                "distraction",
                f"URL contains {distraction_score} distracting keywords",
                confidence=min(0.8, 0.5 + (distraction_score * 0.1))
            )
        
        # Check for useful keywords
        useful_score = self._score_keywords(url_text, self.useful_keywords)
        if useful_score > 0:
            return self._result(
                "useful",
                f"URL contains {useful_score} useful keywords",
                confidence=min(0.7, 0.4 + (useful_score * 0.1))
            )
        
        # 4. If we have a metadata fetcher, try to get more information
        if self.metadata_fetcher:
            try:
                # Special handling for Google Drive
                if "drive.google.com" in domain_key:
                    return self._classify_google_drive(url)
                
                # Special handling for YouTube
                if "youtube.com" in domain_key or "youtu.be" in domain_key:
                    return self._classify_youtube(url)
                
                # For other domains, try to fetch metadata
                return self._classify_with_metadata(url)
            except Exception as e:
                self.logger.warning(f"Error in metadata-based classification: {str(e)}")
        
        # 5. If we get here, we couldn't make a confident classification
        return self._result(
            "neutral", 
            "No specific classification could be determined",
            confidence=0.5
        )

    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            netloc = urlparse(url).netloc
            return netloc.split(':')[0]  # Remove port if present
        except Exception:
            return ""

    def _get_domain_key(self, domain: str) -> str:
        """Get a normalized domain key for pattern matching.
        
        Args:
            domain: Domain to normalize
            
        Returns:
            Normalized domain for pattern matching
        """
        # Remove www. prefix if present
        domain_key = domain.replace('www.', '')
        
        # Special handling for known domains
        if domain_key in ['docs.google.com', 'sheets.google.com', 'slides.google.com']:
            return 'drive.google.com'
            
        return domain_key

    def _matches_patterns(self, domain: str, path: str, query: str, fragment: str, patterns: List[str]) -> bool:
        """Check if URL matches any patterns for a given domain."""
        for pattern in patterns:
            if re.search(pattern, f"{path} {query} {fragment}", re.IGNORECASE):
                return True
        return False

    def _score_keywords(self, text: str, keywords: List[str]) -> int:
        """Score text based on the number of matching keywords."""
        if not text or not keywords:
            return 0
            
        text = text.lower()
        score = 0
        
        for keyword in keywords:
            # Simple substring match
            if keyword in text:
                score += 1
                
                # Bonus for exact word matches
                if re.search(rf'\b{re.escape(keyword)}\b', text):
                    score += 1
                    
                    # Additional bonus for multiple exact matches
                    matches = len(re.findall(rf'\b{re.escape(keyword)}\b', text))
                    if matches > 1:
                        score += min(matches - 1, 3)  # Cap bonus points
                        
        return score
        
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing common tracking parameters and fragments."""
        if not url:
            return url
            
        try:
            # Parse the URL
            parsed = urlparse(url)
            
            # Keep the scheme, netloc, and path
            scheme = parsed.scheme or 'https'
            netloc = parsed.netloc or ''
            path = parsed.path or ''
            
            # Process query parameters
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            tracking_params = ['utm_', 'fbclid', 'gclid', 'mc_', 'igshid', 'ref_', 'feature', 'app', 'ref']
            
            # Remove tracking parameters
            filtered_params = {}
            for param, values in query_params.items():
                if not any(param.lower().startswith(tp) for tp in tracking_params):
                    filtered_params[param] = values
            
            # Rebuild the query string
            query = ''
            if filtered_params:
                query_parts = []
                for param, values in filtered_params.items():
                    for value in values:
                        query_parts.append(f"{param}={value}" if value else param)
                query = '&'.join(query_parts)
            
            # Reconstruct the URL
            return urlunparse((scheme, netloc, path, '', query, ''))
            
        except Exception as e:
            self.logger.warning(f"Error normalizing URL {url}: {str(e)}")
            return url
    
    def _classify_google_drive(self, url: str) -> Dict[str, Any]:
        """Classify a Google Drive URL using metadata."""
        try:
            # Extract file ID from URL
            file_id = self.extract_drive_file_id(url)
            if not file_id:
                return self._result("neutral", "Could not extract file ID from Google Drive URL")
                
            # Get metadata from the fetcher
            metadata = self.metadata_fetcher.get_drive_metadata(file_id)
            if not metadata or 'error' in metadata:
                return self._result(
                    "neutral", 
                    "Could not fetch metadata for Google Drive file",
                    metadata=metadata
                )
                
            return self._classify_with_metadata(metadata, source="google_drive")
            
        except Exception as e:
            logger.error(f"Error classifying Google Drive URL {url}: {str(e)}", exc_info=True)
            return self._result("error", f"Error processing Google Drive URL: {str(e)}")
    
    def _classify_youtube(self, url: str) -> Dict[str, Any]:
        """Classify a YouTube URL using metadata."""
        try:
            metadata = self.metadata_fetcher.get_youtube_metadata(url)
            if not metadata or 'error' in metadata:
                return self._result(
                    "neutral", 
                    "Could not fetch metadata for YouTube video",
                    metadata=metadata
                )
                
            return self._classify_with_metadata(metadata, source="youtube")
            
        except Exception as e:
            logger.error(f"Error classifying YouTube URL {url}: {str(e)}", exc_info=True)
            return self._result("error", f"Error processing YouTube URL: {str(e)}")
    
    def _classify_with_metadata(self, metadata: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Classify content based on metadata from various sources."""
        if not metadata or not isinstance(metadata, dict):
            return self._result("neutral", "No metadata available")
            
        # Extract text content from metadata
        text_parts = []
        
        # Common fields
        for field in ['title', 'description', 'name', 'content', 'summary']:
            if metadata.get(field):
                text_parts.append(str(metadata[field]).lower())
        
        # Source-specific fields
        if source == 'youtube':
            if metadata.get('channel'):
                text_parts.append(metadata['channel'].lower())
            if metadata.get('tags') and isinstance(metadata['tags'], list):
                text_parts.extend(tag.lower() for tag in metadata['tags'] if tag)
        elif source == 'google_drive':
            if metadata.get('mimeType'):
                text_parts.append(metadata['mimeType'].lower())
        
        # Combine all text for analysis
        content = ' '.join(text_parts)
        
        # Calculate scores
        distraction_score = self._score_keywords(content, self.distraction_keywords)
        useful_score = self._score_keywords(content, self.useful_keywords)
        
        # Determine classification
        if useful_score > 0 and distraction_score > 0:
            if useful_score >= distraction_score:
                return self._result(
                    "useful",
                    f"Content appears useful (useful_score: {useful_score}, distraction_score: {distraction_score})",
                    confidence=min(0.8, 0.4 + (useful_score * 0.1)),
                    metadata={"useful_score": useful_score, "distraction_score": distraction_score, "source": source}
                )
            else:
                return self._result(
                    "distraction", 
                    f"Content appears distracting (distraction_score: {distraction_score}, useful_score: {useful_score})",
                    confidence=min(0.9, 0.5 + (distraction_score * 0.1)),
                    metadata={"distraction_score": distraction_score, "useful_score": useful_score, "source": source}
                )
        elif distraction_score > 0:
            return self._result(
                "distraction", 
                f"Content appears distracting (score: {distraction_score})",
                confidence=min(0.9, 0.5 + (distraction_score * 0.1)),
                metadata={"distraction_score": distraction_score, "source": source}
            )
        elif useful_score > 0:
            return self._result(
                "useful",
                f"Content appears useful (score: {useful_score})",
                confidence=min(0.8, 0.4 + (useful_score * 0.1)),
                metadata={"useful_score": useful_score, "source": source}
            )
        
        return self._result(
            "neutral",
            "Content appears neutral",
            confidence=0.5,
            metadata={"source": source}
        )
    
    def _classify_with_metadata_fallback(self, url: str) -> Dict[str, Any]:
        """Fallback classification using generic metadata."""
        try:
            metadata = self.metadata_fetcher.get_webpage_metadata(url)
            if not metadata or 'error' in metadata:
                return self._result("neutral", "Could not fetch webpage metadata")
                
            return self._classify_with_metadata(metadata, source="webpage")
            
        except Exception as e:
            logger.warning(f"Error in metadata fallback for {url}: {str(e)}")
            return self._result("neutral", "Error in metadata analysis")

    # The following methods would be implemented to fetch actual metadata
    def extract_drive_file_id(self, url: str) -> Optional[str]:
        """Extract Google Drive file ID from URL."""
        if not url:
            return None
            
        # Handle standard Google Drive URL formats
        patterns = [
            # File URLs
            r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/open\?id=([^&]+)',
            # Folder URLs
            r'drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)',
            # Google Docs/Sheets/Slides
            r'docs\.google\.com/(?:\w+/)*d/([a-zA-Z0-9_-]+)',
            # General pattern that should catch most variations
            r'[&?](?:id|key)=([a-zA-Z0-9_-]+)'
        ]
        
        # First try specific patterns
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
                
        # Fallback to a more general pattern
        general_pattern = r'[\?&](?:id|key)=([a-zA-Z0-9_-]+)'
        match = re.search(general_pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
            
        # Try to extract from path segments
        path_segments = url.split('/')
        for i, segment in enumerate(path_segments):
            if segment in ['d', 'file', 'folders'] and i + 1 < len(path_segments):
                # Get the next segment, but remove any query parameters
                file_id = path_segments[i + 1].split('?')[0]
                if file_id and len(file_id) > 10:  # Basic validation
                    return file_id
                    
        return None

    def get_drive_metadata(self, file_id: str) -> Dict:
        """Get metadata for a Google Drive file.
        
        In a real implementation, this would use the Google Drive API.
        For now, it returns a mock response.
        """
        # This is a mock implementation
        return {
            "title": "Harry Potter fanfic.pdf",
            "description": "Fan fiction about Harry Potter",
            "mimeType": "application/pdf",
            "name": "Harry Potter fanfic.pdf"
        }

    def get_youtube_metadata(self, url: str) -> Dict:
        """Get metadata for a YouTube video.
        
        In a real implementation, this would use the YouTube API.
        For now, it returns a mock response.
        """
        return {
            "title": "Top 10 Funniest Moments in Harry Potter",
            "description": "Enjoy a laugh with this Harry Potter compilation",
            "channel": "Movie Clips"
        }

    def get_page_title_and_description(self, url: str) -> Dict:
        """Get page title and description.
        
        In a real implementation, this would fetch and parse the webpage.
        For now, it returns an empty dict.
        """
        return {}


    def _is_potential_publication(self, url: str, domain: str, path: str) -> bool:
        """
        Determine if the URL is potentially a publication that should be classified
        using the publication classifier.
        
        Args:
            url: The URL to check
            domain: The domain of the URL
            path: The path of the URL
            
        Returns:
            bool: True if the URL is potentially a publication, False otherwise
        """
        # Check for known academic domains
        academic_domains = [
            'arxiv.org', 'researchgate.net', 'academia.edu', 'ssrn.com',
            'sciencedirect.com', 'springer.com', 'ieee.org', 'acm.org', 
            'jstor.org', 'wiley.com', 'tandfonline.com', 'nature.com',
            'science.org', 'apa.org', 'pubmed.ncbi.nlm.nih.gov'
        ]
        
        if any(academic_domain in domain for academic_domain in academic_domains):
            return True
            
        # Check for PDF files
        if path.endswith('.pdf'):
            return True
            
        # Check for DOI patterns
        if '/doi/' in path or 'doi.org' in domain:
            return True
            
        # Check for common academic URL patterns
        academic_patterns = [
            '/article/', '/abstract/', '/full/', '/content/',
            '/publication/', '/document/', '/paper/', '/journal/',
            '/proceedings/', '/conference/', '/preprint/', '/pdf/'
        ]
        
        for pattern in academic_patterns:
            if pattern in path:
                return True
                
        return False
                
    def _is_entertainment_content(self, url: str, domain: str, path: str) -> bool:
        """
        Determine if the URL is entertainment content like movies, TV shows, etc.
        
        Args:
            url: The URL to check
            domain: The domain of the URL
            path: The path of the URL
            
        Returns:
            bool: True if the URL is entertainment content, False otherwise
        """
        # Entertainment domains
        entertainment_domains = [
            'imdb.com', 'rottentomatoes.com', 'metacritic.com', 'letterboxd.com',
            'netflix.com', 'hulu.com', 'disneyplus.com', 'hbomax.com',
            'primevideo.com', 'youtube.com', 'goodreads.com', 'audible.com'
        ]
        
        # Check domain
        if any(ent_domain in domain for ent_domain in entertainment_domains):
            return True
            
        # Check for entertainment content patterns in URL
        entertainment_patterns = [
            '/movie/', '/title/', '/show/', '/watch/', '/film/',
            '/tv/', '/series/', '/episode/', '/season/', '/trailer/',
            '/book/', '/novel/', '/fiction/', '/literature/'
        ]
        
        for pattern in entertainment_patterns:
            if pattern in path.lower():
                return True
                
        return False

# Singleton instance for easy import
link_classifier = LinkClassifier()