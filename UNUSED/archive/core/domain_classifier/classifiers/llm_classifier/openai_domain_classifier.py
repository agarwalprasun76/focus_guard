"""
OpenAI-based domain classifier for general web content.

This module provides a classifier that uses OpenAI's API
to determine if general web content is educational, entertainment, or neutral.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple

from .openai_classifier import OpenAIBaseClassifier


class OpenAIDomainClassifier(OpenAIBaseClassifier):
    """
    OpenAI-based classifier for general domain links.
    
    This classifier uses OpenAI's API to classify general web content
    as educational, entertainment, or neutral.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, model_tier: str = "standard"):
        """Initialize the OpenAI domain classifier.
        
        Args:
            api_key: OpenAI API key (defaults to config file, then OPENAI_API_KEY environment variable)
            model: Explicit model name to use (overrides model_tier if provided)
            model_tier: Which model tier to use from config ("standard", "premium", or "fast")
        """
        super().__init__(api_key=api_key, model=model, model_tier=model_tier)
        self._logger = logging.getLogger("focus_guard.domain_classifier.llm_classifier.openai_domain")
        self._logger.info("OpenAI domain classifier initialized")
    
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
        Create a prompt for the OpenAI model to classify the content.
        
        Args:
            url: The URL of the content
            domain: The domain of the content
            content: The content to classify
            metadata: Additional metadata about the content
            
        Returns:
            str: A prompt for the OpenAI model
        """
        # Extract metadata
        title = metadata.get('title', '')
        description = metadata.get('description', '')
        keywords = metadata.get('keywords', [])
        
        # Create a prompt for the OpenAI model
        prompt = f"""Classify the following web content as either 'useful' (educational), 
'distraction' (entertainment), or 'neutral'.

URL: {url}
Domain: {domain}
Title: {title}
Description: {description}
Keywords: {', '.join(keywords) if isinstance(keywords, list) else keywords}

You MUST respond with a valid JSON object in the following format:
{{
  "classification": "useful" or "distraction" or "neutral",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<brief explanation for the classification>"
}}

Do not include any other text outside of the JSON object. The JSON must be valid and parseable.
Example response:
{{
  "classification": "useful",
  "confidence": 0.85,
  "reason": "This content appears to be educational material about mathematics."
}}
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> Tuple[str, float, str]:
        """
        Parse the LLM's response to extract classification, confidence, and reason.
        
        This method extends the parent's implementation to handle simple text responses
        like 'useful', 'distraction', or 'neutral' in addition to JSON responses.
        
        Args:
            response: The raw text response from the LLM
            
        Returns:
            Tuple of (classification, confidence, reason)
        """
        try:
            # First try to extract JSON from the response
            json_str = self._extract_json(response)
            
            if json_str:
                # Parse the JSON
                result = json.loads(json_str)
                
                # Extract the classification details
                classification = result.get("classification", "neutral").lower()
                confidence = float(result.get("confidence", 0.7))
                reason = result.get("reason", "No reason provided")
                
                # Validate classification
                if classification not in ["useful", "distraction", "neutral"]:
                    # Try to map other values to our classification scheme
                    if any(word in classification.lower() for word in ["education", "informative", "learning", "academic", "work"]):
                        classification = "useful"
                    elif any(word in classification.lower() for word in ["entertainment", "distract", "waste", "leisure", "fun"]):
                        classification = "distraction"
                    else:
                        classification = "neutral"
                        
                # Clamp confidence between 0 and 1
                confidence = max(0.0, min(confidence, 1.0))
                
                return classification, confidence, reason
            else:
                # If no JSON found, check for simple text responses
                response_lower = response.lower().strip()
                
                # Check for direct classification keywords
                if "useful" in response_lower or any(word in response_lower for word in ["education", "informative", "learning", "academic", "work"]):
                    return "useful", 0.7, "Direct text response indicates educational content"
                elif "distraction" in response_lower or any(word in response_lower for word in ["entertainment", "distract", "waste", "leisure", "fun"]):
                    return "distraction", 0.7, "Direct text response indicates entertainment content"
                elif "neutral" in response_lower:
                    return "neutral", 0.6, "Direct text response indicates neutral content"
                
                # If we got here, log that we couldn't parse the response
                self._logger.warning(f"Could not extract JSON or classification from LLM response: {response[:100]}...")
                return "neutral", 0.5, "Failed to parse LLM response"
                
        except Exception as e:
            self._logger.error(f"Error parsing LLM response: {e}")
            return "neutral", 0.5, f"Error parsing response: {str(e)}"
    
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
        
        # Check for API key availability
        api_key_available = hasattr(self, 'api_key') and self.api_key
        if not api_key_available:
            self._logger.warning("No OpenAI API key available, using fallback classification")
            return self._fallback_classification(url, domain, "", metadata)
        
        # Try to classify with OpenAI
        try:
            # Create a prompt for the OpenAI model
            prompt = self._create_classification_prompt(url, domain, "", metadata)
            
            # Generate a response from OpenAI
            response = self._generate_classification(prompt)
            
            # Parse the response
            classification, confidence, reason = self._parse_llm_response(response)
            
            # If we got a valid classification, return it
            if classification in ["useful", "distraction", "neutral"]:
                return {
                    "classification": classification,
                    "confidence": confidence,
                    "reason": reason
                }
            
            # If we got here, the response couldn't be parsed properly
            self._logger.warning(f"OpenAI response couldn't be parsed properly: {response[:50]}...")
        except Exception as e:
            self._logger.error(f"Error classifying with OpenAI: {e}")
        
        # Fall back to keyword-based classification
        self._logger.info(f"Using fallback classification for {url}")
        return self._fallback_classification(url, domain, "", metadata)
    
    def _fallback_classification(self, url: str, domain: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide a fallback classification when the OpenAI API fails.
        
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
        
        # Special domain-based classification
        if domain:
            # Educational domains
            edu_domains = ['khanacademy.org', 'coursera.org', 'edx.org', 'udemy.com', 'udacity.com',
                          'wikipedia.org', 'github.com', 'stackoverflow.com', 'medium.com']
            # Entertainment domains
            ent_domains = ['netflix.com', 'youtube.com', 'twitch.tv', 'tiktok.com', 'instagram.com',
                          'facebook.com', 'reddit.com', 'twitter.com', 'spotify.com']
                          
            for edu_domain in edu_domains:
                if edu_domain in domain:
                    return {
                        "classification": "useful",
                        "confidence": 0.9,
                        "reason": f'Domain {domain} is known to be educational'
                    }
                    
            for ent_domain in ent_domains:
                if ent_domain in domain:
                    return {
                        "classification": "distraction",
                        "confidence": 0.9,
                        "reason": f'Domain {domain} is known to be entertainment'
                    }
        
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
            for keyword in keywords:
                if keyword.lower() in educational_keywords:
                    edu_count += 1
                if keyword.lower() in entertainment_keywords:
                    ent_count += 1
        elif isinstance(keywords, str):
            for edu_kw in educational_keywords:
                if edu_kw in keywords:
                    edu_count += 1
            for ent_kw in entertainment_keywords:
                if ent_kw in keywords:
                    ent_count += 1
        
        # Determine classification based on counts
        if edu_count > ent_count and edu_count > 0:
            return {
                "classification": "useful",
                "confidence": min(0.5 + (edu_count * 0.05), 0.9),
                "reason": f'Content contains {edu_count} educational keywords'
            }
        elif ent_count > edu_count and ent_count > 0:
            return {
                "classification": "distraction",
                "confidence": min(0.5 + (ent_count * 0.05), 0.9),
                "reason": f'Content contains {ent_count} entertainment keywords'
            }
        else:
            return {
                "classification": "neutral",
                "confidence": 0.5,
                "reason": 'No clear classification pattern detected'
            }
