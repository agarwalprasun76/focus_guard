"""
Publication Classifier

This module provides functionality to classify publication links (academic papers, books, etc.)
based on their content using machine learning models and text extraction techniques.
It adapts to work within the hierarchical classification system.
"""

import os
import re
import logging
import mimetypes
import tempfile
import asyncio
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, List, Union
from urllib.parse import urlparse

# Import base classifier
from ..base_classifier import ContentClassifier
from .utils import ClassificationResult

# Third-party imports - need to be added to requirements.txt
try:
    import httpx
    from transformers import pipeline
    import trafilatura
    from pdfminer.high_level import extract_text as extract_pdf_text
    import yaml
    
    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    logging.warning(f"Some dependencies for publication classifier not found: {e}. Install requirements.txt")

# Set up logging
logger = logging.getLogger(__name__)

# Default model for classification
DEFAULT_MODEL = "institutional/institutional-books-topic-classifier-bert"

# Default policy settings
DEFAULT_POLICY = {
    "block_classes": [
        "LANGUAGE AND LITERATURE",
        "FINE ARTS",
        "MUSIC AND BOOKS ON MUSIC"
    ],
    "allow_classes": [
        "SCIENCE", 
        "EDUCATION",
        "TECHNOLOGY",
        "SOCIAL SCIENCES",
        "MEDICINE"
    ],
    "file_blocklist": [".epub", ".mobi", ".mp3", ".mp4"],
    "threshold": 0.85
}


class PublicationClassifier(ContentClassifier):
    """
    Classifier for academic and professional publications.
    
    This classifier uses machine learning models to analyze publication content
    and classify it based on its academic or professional relevance.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(PublicationClassifier, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = None, policy_path: str = None):
        """
        Initialize the publication classifier.
        
        Args:
            model_name: Name of the Hugging Face model to use
            policy_path: Path to YAML policy file
        """
        if hasattr(self, '_initialized'):
            return
            
        self.logger = logging.getLogger(__name__)
        
        # Initialize model
        self.model_name = model_name or DEFAULT_MODEL
        self._classifier = None
        
        # Academic domains
        self.academic_domains = [
            # Research and academic journals
            'scholar.google.com', 'jstor.org', 'sciencedirect.com', 
            'arxiv.org', 'researchgate.net', 'academia.edu', 'ieee.org',
            'springerlink.com', 'nature.com', 'acm.org', 'pubmed.ncbi.nlm.nih.gov',
            'ssrn.com', 'wiley.com', 'tandfonline.com', 'sagepub.com', 
            'apa.org', 'eric.ed.gov', 'nih.gov', 'research.google.com', 'research.google',
            
            # University domains
            'edu', 'ac.uk', 'ac.jp', 'uni-', '.uni.'
        ]
        
        # Publication URL patterns
        self.publication_patterns = [
            # Common paper identifiers
            '/doi/', '/abstract/', '/article/', '/paper/', '/publication/',
            '/journal/', '/conference/', '/proceedings/', '/research/',
            '/thesis/', '/dissertation/', '/preprint/', '/postprint/',
            
            # File extensions
            '.pdf', '.doc', '.docx'
        ]
        
        # Load policy
        if policy_path is None:
            # Default path in the same directory
            policy_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '../publication_policy.yaml'
            )
            
        self.policy_path = policy_path
        self.policy = self._load_policy(policy_path)
        
        # Cache for classification results
        self.cache = {}
        
        self._initialized = True
    
    def _load_model(self):
        """Load the classification model."""
        if not IMPORT_SUCCESS:
            self.logger.warning("Cannot load publication model - dependencies not installed")
            return False
            
        try:
            self.logger.info(f"Loading publication classifier model: {self.model_name}")
            self._classifier = pipeline('text-classification', model=self.model_name)
            return True
        except Exception as e:
            self.logger.error(f"Failed to load publication classifier model: {e}")
            return False
            
    def _load_policy(self, policy_path: str = None):
        """Load classification policy from YAML file."""
        if not policy_path or not os.path.exists(policy_path):
            self.logger.warning(f"Policy file not found: {policy_path}, using defaults")
            return DEFAULT_POLICY
            
        try:
            with open(policy_path, 'r', encoding='utf-8') as f:
                policy = yaml.safe_load(f)
                self.logger.info(f"Loaded policy from {policy_path}")
                return policy
        except Exception as e:
            self.logger.error(f"Error loading policy file: {e}")
            return DEFAULT_POLICY
            
    def can_classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> bool:
        """
        Check if this classifier can handle the URL.
        
        Args:
            url: The URL to check
            domain: The domain of the URL
            metadata: Optional metadata
            
        Returns:
            True if this is likely a publication URL, False otherwise
        """
        # Simple pattern matching for common academic/publication URLs
        patterns = [
            r'\.pdf$',  # PDF files
            r'arxiv\.org',  # arXiv
            r'researchgate\.net',  # ResearchGate
            r'academia\.edu',  # Academia
            r'scholar\.google\.',  # Google Scholar
            r'doi\.org',  # DOI links
            r'jstor\.org',  # JSTOR
            r'sciencedirect\.com',  # ScienceDirect
            r'springer\.com',  # Springer
            r'ieee\.org',  # IEEE
            r'acm\.org',  # ACM Digital Library
            r'ssrn\.com',  # SSRN
            r'wiley\.com',  # Wiley
            r'tandfonline\.com',  # Taylor & Francis
            r'cambridge\.org/core',  # Cambridge Core
            r'oup\.com',  # Oxford University Press
            r'nature\.com',  # Nature journals
            r'sciencemag\.org',  # Science
            r'pnas\.org',  # PNAS
            r'pubmed\.ncbi\.nlm\.nih\.gov',  # PubMed
            r'books\.google\.',  # Google Books
        ]
        
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        # Check file extension for documents
        doc_extensions = ['.pdf', '.doc', '.docx', '.epub', '.mobi']
        for ext in doc_extensions:
            if url.lower().endswith(ext):
                return True
                
        return False
    
    async def fetch_content_chunk(self, url: str, range_size: int = 65535) -> Tuple[str, bytes]:
        """Fetch a chunk of content from the URL to determine type and extract text.
        
        Args:
            url: The URL to fetch
            range_size: Size of the range to fetch in bytes
            
        Returns:
            Tuple of (content_type, content_bytes)
        """
        try:
            headers = {"Range": f"bytes=0-{range_size}"}
            
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                
            content_type = response.headers.get("content-type", "")
            if not content_type:
                content_type = mimetypes.guess_type(url)[0] or ""
                
            return content_type.lower(), response.content
        except Exception as e:
            self.logger.error(f"Error fetching content: {str(e)}")
            return "", b""
    
    def extract_text(self, content_type: str, content: bytes, url: str = "") -> str:
        """Extract text from content based on content type.
        
        Args:
            content_type: MIME type of the content
            content: Raw content bytes
            url: Original URL (for reference)
            
        Returns:
            Extracted text
        """
        try:
            # PDF handling
            if 'application/pdf' in content_type:
                # Write to temp file and extract with pdfminer
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(content)
                    tmp_name = tmp.name
                
                try:
                    text = extract_pdf_text(tmp_name)
                    os.unlink(tmp_name)
                    return text or ""
                except Exception as pdf_ex:
                    self.logger.error(f"PDF extraction error: {str(pdf_ex)}")
                    os.unlink(tmp_name)
                    return ""
            
            # HTML handling
            elif 'text/html' in content_type:
                try:
                    return trafilatura.extract(content.decode('utf-8', errors='ignore')) or ""
                except Exception as html_ex:
                    self.logger.error(f"HTML extraction error: {str(html_ex)}")
                    # Fallback to simple tag stripping
                    text = content.decode('utf-8', errors='ignore')
                    text = re.sub(r'<[^>]+>', ' ', text)
                    return re.sub(r'\s+', ' ', text).strip()
            
            # Plain text handling
            elif 'text/' in content_type:
                return content.decode('utf-8', errors='ignore')
            
            # Unknown format
            else:
                self.logger.warning(f"Unsupported content type: {content_type}")
                return ""
                
        except Exception as e:
            self.logger.error(f"Error extracting text: {str(e)}")
            return ""
    
    def predict(self, text: str, max_len: int = 2048) -> Tuple[str, float]:
        """Predict the class of the text.
        
        Args:
            text: The text to classify
            max_len: Maximum text length to use
            
        Returns:
            Tuple of (label, score)
        """
        if not text:
            return "UNKNOWN", 0.0
            
        if not self._classifier:
            success = self._load_model()
            if not success:
                return "UNKNOWN", 0.0
        
        try:
            # Truncate to avoid OOM issues
            truncated_text = text[:max_len]
            
            # Run prediction
            result = self._classifier(truncated_text)[0]
            label = result['label']
            score = result['score']
            
            return label, score
        except Exception as e:
            self.logger.error(f"Error in prediction: {str(e)}")
            return "UNKNOWN", 0.0
    
    def decide(self, label: str, score: float, url: str) -> str:
        """Decide whether to allow or block based on classification.
        
        Args:
            label: The predicted class
            score: Confidence score (0-1)
            url: Original URL
            
        Returns:
            Decision: "block" or "allow"
        """
        # Check file extension blocklist
        _, ext = os.path.splitext(urlparse(url).path)
        if ext.lower() in self.policy.get('file_blocklist', []):
            return "block"
        
        # Check confidence threshold
        threshold = self.policy.get('threshold', 0.85)
        if score < threshold:
            return "neutral"  # Not confident enough
        
        # Check block/allow lists
        if label in self.policy.get('block_classes', []):
            return "block"
        
        if label in self.policy.get('allow_classes', []):
            return "allow"
        
        # Default to neutral
        return "neutral"
    
    async def classify_url(self, url: str) -> ClassificationResult:
        """Classify a URL as an academic/professional publication.
        
        Args:
            url: The URL to classify
            
        Returns:
            ClassificationResult object
        """
        # Check cache first
        if url in self.cache:
            return self.cache[url]
        
        try:
            # Fetch content sample
            content_type, content = await self.fetch_content_chunk(url)
            if not content:
                return ClassificationResult(
                    url=url,
                    content_type="unknown",
                    label="UNKNOWN",
                    score=0.0,
                    decision="error",
                    reason="Failed to fetch content",
                    metadata={}
                )
            
            # Extract text
            text = self.extract_text(content_type, content, url)
            if not text:
                return ClassificationResult(
                    url=url,
                    content_type=content_type,
                    label="UNKNOWN",
                    score=0.0,
                    decision="error",
                    reason="Failed to extract text",
                    metadata={}
                )
            
            # Classify
            label, score = self.predict(text)
            decision = self.decide(label, score, url)
            
            # Map decision to focus_guard classification
            classification = self.map_decision_to_focus_guard(decision)
            
            # Create result
            result = ClassificationResult(
                url=url,
                content_type=content_type,
                label=label,
                score=score,
                decision=decision,
                reason=f"Content classified as {label} with {score:.2f} confidence",
                metadata={
                    "text_sample": text[:200] + "..." if len(text) > 200 else text
                }
            )
            
            # Cache result
            self.cache[url] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error classifying URL {url}: {str(e)}")
            return ClassificationResult(
                url=url,
                content_type="unknown",
                label="UNKNOWN",
                score=0.0,
                decision="error",
                reason=f"Error: {str(e)}",
                metadata={}
            )

    def map_decision_to_focus_guard(self, decision: str) -> str:
        """Map publication classifier decision to focus_guard classification.
        
        Args:
            decision: The publication classifier decision ("block", "allow", "neutral", "error")
            
        Returns:
            focus_guard classification ("distraction", "useful", "neutral", "error")
        """
        mapping = {
            "block": "distraction",
            "allow": "useful",
            "neutral": "neutral",
            "error": "error"
        }
        return mapping.get(decision, "neutral")
        
    def classify(self, url: str, content: str = "", content_type: str = "") -> ClassificationResult:
        """Synchronous wrapper for classify_url
        
        Args:
            url: The URL to classify
            content: Optional content to classify (if already fetched)
            content_type: Optional content type (if already known)
            
        Returns:
            ClassificationResult with classification details
        """
        try:
            # Use asyncio to run the async classify_url method
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.classify_url(url))
            
            # Map the decision to focus_guard format if needed
            focus_guard_classification = self.map_decision_to_focus_guard(result.decision)
            
            # If the mapping changed the classification, update the result
            if focus_guard_classification != result.decision:
                result = ClassificationResult(
                    url=result.url,
                    content_type=result.content_type,
                    label=result.label,
                    score=result.score,
                    decision=focus_guard_classification,
                    reason=result.reason,
                    metadata=result.metadata
                )
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error in publication classifier: {str(e)}")
            return ClassificationResult(
                url=url,
                content_type="unknown",
                label="UNKNOWN",
                score=0.0,
                decision="error",
                reason=f"Error in publication classifier: {str(e)}",
                metadata={"error": str(e)}
            )
    
    @property
    def priority(self) -> int:
        """
        Return the priority of this classifier.
        
        Higher priority classifiers are checked first in the classification chain.
        
        Returns:
            int: Priority value (higher = checked first)
        """
        return 500  # Medium priority


# Create instance
publication_classifier = PublicationClassifier()
