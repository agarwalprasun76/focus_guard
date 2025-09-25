"""
LLM-based domain classifier for general web content.

This module provides a classifier that uses small language models
to determine if general web content is educational, entertainment, or neutral.
"""

import logging
from typing import Dict, Any, Optional, Tuple

from .llm_base_classifier import LLMBaseClassifier


class LLMDomainClassifier(LLMBaseClassifier):
    """
    LLM-based classifier for general domain links.
    
    This classifier uses small language models to classify general web content
    as educational, entertainment, or neutral.
    """
    
    def __init__(self):
        """Initialize the LLM domain classifier."""
        super().__init__()
        self._logger = logging.getLogger("focus_guard.domain_classifier.llm_classifier.domain")
        self._logger.info("LLM domain classifier initialized")
    
    def can_classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> bool:
        """
        Determine if this classifier can handle the given content.
        
        This classifier can handle any general web content with sufficient metadata.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            bool: True if this classifier can handle this content, False otherwise
        """
        # Basic check for URL and domain
        if not url or not domain:
            return False
        
        # Check if we have enough metadata to make a classification
        if metadata:
            # If we have a title or description, we can attempt classification
            if metadata.get('title') or metadata.get('description'):
                return True
        
        # Default to True for testing purposes
        # In a production environment, we might want to be more selective
        return True
    
    def _create_classification_prompt(self, url: str, domain: str, content: str, metadata: Dict[str, Any]) -> str:
        """
        Create a prompt for the language model to classify the content.
        
        Args:
            url: The URL of the content
            domain: The domain of the content
            content: The content to classify
            metadata: Additional metadata about the content
            
        Returns:
            str: A prompt for the language model
        """
        # Extract metadata
        title = metadata.get('title', '')
        description = metadata.get('description', '')
        keywords = metadata.get('keywords', [])
        
        # Create a prompt for the LLM
        prompt = f"""Classify the following web content as either 'useful' (educational), 
        'distraction' (entertainment), or 'neutral'.
        
        URL: {url}
        Domain: {domain}
        Title: {title}
        Description: {description}
        Keywords: {', '.join(keywords) if isinstance(keywords, list) else keywords}
        
        Respond with just one word: 'useful', 'distraction', or 'neutral'.
        """
        return prompt
    
    def classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Classify the content based on URL, domain, and metadata.
        
        This overrides the parent method to use the provided metadata directly
        instead of trying to fetch it again.
        
        Args:
            url: The URL of the content to classify
            domain: The domain of the content
            metadata: Optional metadata about the content
            
        Returns:
            dict: A classification result
        """
        # Use provided metadata or empty dict
        if metadata is None:
            metadata = {}
            
        # Check if we can classify this content
        if not self.can_classify(url, domain, metadata):
            self._logger.info(f"Cannot classify: {url}")
            return {}
            
        # Try to classify with the LLM if available
        if self.model and self.tokenizer:
            try:
                # Create a prompt for the LLM
                prompt = self._create_classification_prompt(url, domain, "", metadata)
                
                # Generate a response from the LLM
                response = self._generate_classification(prompt)
                
                # Parse the response
                result = self._parse_llm_response(response)
                if result:
                    return result
            except Exception as e:
                self._logger.error(f"Error classifying with LLM: {e}")
                
        # Fall back to keyword-based classification
        return self._fallback_classification(url, domain, "", metadata)
    
    def _fallback_classification(self, url: str, domain: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide a fallback classification when the LLM fails.
        
        Args:
            url: The URL of the content
            domain: The domain of the content
            content: The content to classify
            metadata: Additional metadata about the content
            
        Returns:
            dict: A classification result
        """
        # Extract metadata for fallback classification
        title = metadata.get('title', '').lower()
        description = metadata.get('description', '').lower()
        keywords = metadata.get('keywords', [])
        if isinstance(keywords, list):
            keywords = [k.lower() for k in keywords]
        elif isinstance(keywords, str):
            keywords = keywords.lower()
        else:
            keywords = ''
        
        # Educational keywords
        educational_keywords = [
            'learn', 'education', 'course', 'tutorial', 'guide', 'how-to',
            'university', 'college', 'school', 'academic', 'research',
            'science', 'math', 'history', 'programming', 'study'
        ]
        
        # Entertainment keywords
        entertainment_keywords = [
            'game', 'play', 'fun', 'entertainment', 'movie', 'tv', 'show',
            'music', 'video', 'stream', 'watch', 'listen', 'social',
            'meme', 'funny', 'joke', 'comedy', 'amusement'
        ]
        
        # Count matches for each category
        edu_count = 0
        ent_count = 0
        
        # Check title
        for keyword in educational_keywords:
            if keyword in title:
                edu_count += 2  # Title matches are weighted more
        for keyword in entertainment_keywords:
            if keyword in title:
                ent_count += 2  # Title matches are weighted more
        
        # Check description
        for keyword in educational_keywords:
            if keyword in description:
                edu_count += 1
        for keyword in entertainment_keywords:
            if keyword in description:
                ent_count += 1
        
        # Check keywords
        if isinstance(keywords, list):
            for keyword in educational_keywords:
                if keyword in keywords:
                    edu_count += 1
            for keyword in entertainment_keywords:
                if keyword in keywords:
                    ent_count += 1
        elif isinstance(keywords, str):
            for keyword in educational_keywords:
                if keyword in keywords:
                    edu_count += 1
            for keyword in entertainment_keywords:
                if keyword in keywords:
                    ent_count += 1
        
        # Determine classification based on counts
        if edu_count > ent_count and edu_count > 0:
            classification = "useful"
            confidence = min(0.7, 0.5 + (edu_count - ent_count) * 0.05)
        elif ent_count > edu_count and ent_count > 0:
            classification = "distraction"
            confidence = min(0.7, 0.5 + (ent_count - edu_count) * 0.05)
        else:
            classification = "neutral"
            confidence = 0.5
        
        return {
            "classification": classification,
            "confidence": confidence,
            "reason": f"Fallback classification based on keyword matching (edu={edu_count}, ent={ent_count})"
        }
