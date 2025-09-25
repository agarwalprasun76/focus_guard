"""
Publication Classifier

This module provides functionality to classify publication links (academic papers, books, etc.)
based on their content using machine learning models and text extraction techniques.
"""

import os
import re
import logging
import mimetypes
import tempfile
from typing import Dict, Tuple, Optional, Any, List, Union
from urllib.parse import urlparse
import asyncio

# Third-party imports - need to be added to requirements.txt
try:
    import httpx
    from transformers import pipeline
    import trafilatura
    from pdfminer.high_level import extract_text as extract_pdf_text
    import yaml
    from pydantic import BaseModel
    
    IMPORT_SUCCESS = True
except ImportError as e:
    # Re-try just the BaseModel import separately since it's commonly available
    try:
        from pydantic import BaseModel
    except ImportError:
        # Create a simple BaseModel replacement if pydantic is not available
        class BaseModel:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
    IMPORT_SUCCESS = False
    logging.warning(f"Some dependencies for publication classifier not found: {e}. Install requirements.txt")
except ImportError:
    IMPORT_SUCCESS = False
    logging.warning("Some dependencies for publication classifier not found. Install requirements.txt")

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


class ClassificationResult(BaseModel):
    """Model for publication classification results."""
    url: str
    content_type: str
    label: str
    score: float
    decision: str
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PublicationClassifier:
    """Classifies publication links based on content analysis."""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PublicationClassifier, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = None, policy_path: str = None):
        """Initialize the publication classifier.
        
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
        
        # Load policy
        if policy_path is None:
            # Default path in the same directory
            policy_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'publication_policy.yaml'
            )
            
        self.policy_path = policy_path
        self.policy = self._load_policy(policy_path)
        
        # Cache for classification results
        self.cache = {}
        
        self._initialized = True
    
    def _load_model(self):
        """Load the classification model."""
        if not IMPORT_SUCCESS:
            self.logger.error("Required dependencies not installed")
            return False
            
        try:
            self.logger.info(f"Loading classification model: {self.model_name}")
            self._classifier = pipeline(
                "text-classification", 
                model=self.model_name, 
                truncation=True
            )
            return True
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            return False
    
    def _load_policy(self, policy_path: str = None) -> Dict:
        """Load classification policy from YAML file."""
        if not policy_path or not os.path.exists(policy_path):
            self.logger.warning(f"Policy file not found, using defaults: {policy_path}")
            return DEFAULT_POLICY
            
        try:
            with open(policy_path, 'r', encoding='utf-8') as f:
                policy = yaml.safe_load(f)
                self.logger.info(f"Loaded policy from {policy_path}")
                return policy
        except Exception as e:
            self.logger.error(f"Error loading policy file: {str(e)}")
            return DEFAULT_POLICY
    
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
                    reason="Failed to fetch content"
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
                    reason="Failed to extract text"
                )
            
            # Classify
            label, score = self.predict(text)
            decision = self.decide(label, score, url)
            
            # Create result
            result = ClassificationResult(
                url=url,
                content_type=content_type,
                label=label,
                score=score,
                decision=decision,
                reason=f"Content classified as {label} with {score:.2f} confidence",
                metadata={
                    "text_sample": text[:200] + "..." if len(text) > 200 else text,
                    "content_type": content_type
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
                reason=f"Error: {str(e)}"
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
    
    def classify_link_for_focus_guard(self, url: str) -> Dict[str, Any]:
        """Classify a URL and return in focus_guard format.
        
        Args:
            url: URL to classify
            
        Returns:
            Dict with focus_guard classification format
        """
        try:
            # Run the classifier synchronously by creating a new event loop
            result = asyncio.run(self.classify_url(url))
            
            # Map to focus_guard format
            focus_guard_classification = self.map_decision_to_focus_guard(result.decision)
            
            return {
                "classification": focus_guard_classification,
                "reason": result.reason,
                "confidence": result.score,
                "metadata": {
                    "publication_label": result.label,
                    "content_type": result.content_type,
                    **(result.metadata or {})
                }
            }
        except Exception as e:
            logger.error(f"Error in publication classification for {url}: {str(e)}")
            return {
                "classification": "neutral",
                "reason": f"Error in publication classification: {str(e)}",
                "confidence": 0.0,
                "metadata": {}
            }


# Singleton instance for easy import
publication_classifier = PublicationClassifier()
