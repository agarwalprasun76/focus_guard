"""
OpenAI-based content classifiers

This module provides classifier implementations that use OpenAI's API
for more accurate content classification.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

# Core imports
from core.logger.logger import get_logger

# To avoid circular imports, we use relative imports directly in the class
# The LLMBaseClassifier import happens inside the class definition

logger = get_logger(__name__)

# Check if OpenAI SDK is available
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI SDK not installed - OpenAIClassifier will not be available")
    OPENAI_AVAILABLE = False


def load_config() -> Dict[str, Any]:
    """
    Load OpenAI configuration from config file or use defaults.
    
    Returns:
        Dict containing OpenAI configuration
    """
    config_path = Path(__file__).parent / "config" / "openai_config.json"
    default_config = {
        "api_key": "",
        "models": {
            "default": "gpt-4o-mini",
            "standard": "gpt-4.1-mini",
            "premium": "gpt-4o",
            "fast": "gpt-4.1-nano"
        },
        "parameters": {
            "temperature": 0.1,
            "max_tokens": 300,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        }
    
    try:
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
                logger.info(f"Loaded OpenAI config from {config_path}")
                return config
        else:
            logger.warning(f"No config file found at {config_path}, using defaults")
            return default_config
    except Exception as e:
        logger.error(f"Error loading OpenAI config: {e}, using defaults")
        return default_config


# Import here inside the file to avoid circular imports
from .llm_base_classifier import LLMBaseClassifier
from ..utils import ClassificationResult

class OpenAIBaseClassifier(LLMBaseClassifier):
    """
    Base class for classifiers using OpenAI's API for content classification.
    
    This classifier sends content metadata to OpenAI's API to determine whether
    it's educational (useful), entertainment (distraction), or neutral.
    """
    
    # Default priority value - higher than local LLM
    _priority = 95
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, model_tier: str = "standard"):
        """
        Initialize the OpenAI-based classifier.
        
        Args:
            api_key: OpenAI API key (defaults to config file, then OPENAI_API_KEY environment variable)
            model: Explicit model name to use (overrides model_tier if provided)
            model_tier: Which model tier to use from config ("standard", "premium", or "fast")
        """
        # Load configuration
        self.config = load_config()
        
        # Don't call parent's __init__ as we're not loading a local model
        self.model = None
        self.tokenizer = None
        self.generator = None
        
        # Set model name based on parameters or config
        if model:
            # Explicitly provided model name takes precedence
            self.model_name = model
        else:
            # Otherwise use the tier from config
            self.model_name = self.config["models"].get(
                model_tier, self.config["models"]["default"]
            )
            
        logger.info(f"Using OpenAI model: {self.model_name}")
            
        # Try to get API key from parameters, config, or environment
        self.api_key = api_key or self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OpenAI API key provided - please set one in config file or OPENAI_API_KEY environment variable")
            
        # Get model parameters from config
        self.model_params = self.config.get("parameters", {})
        logger.debug(f"Using model parameters: {self.model_params}")
            
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"OpenAI client initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            self.client = None
            
    def _generate_classification(self, prompt: str) -> str:
        """
        Generate a classification using OpenAI's API.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            API response text
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized")
            
        try:
            # Log the model and parameters being used
            logger.info(f"Requesting classification from {self.model_name}")
            logger.info(f"API Key (first 5 chars): {self.api_key[:5]}...")
            
            # Get parameters from config
            params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "You are a specialized content classification assistant."},
                    {"role": "user", "content": prompt}
                ],
                # Use parameters from config, with defaults
                "temperature": self.model_params.get("temperature", 0.1),
                "max_tokens": self.model_params.get("max_tokens", 300),
                "top_p": self.model_params.get("top_p", 1.0),
                "frequency_penalty": self.model_params.get("frequency_penalty", 0.0),
                "presence_penalty": self.model_params.get("presence_penalty", 0.0)
            }
            
            # Log API parameters
            logger.debug(f"OpenAI API parameters: {params}")
            
            # Make the API call to OpenAI
            try:
                logger.info("Making API call to OpenAI...")
                response = self.client.chat.completions.create(**params)
                logger.info("OpenAI API call successful!")
            except Exception as api_error:
                logger.error(f"OpenAI API call failed: {api_error}")
                # Print detailed error info
                if hasattr(api_error, 'json'):
                    try:
                        logger.error(f"Error details: {api_error.json()}")
                    except:
                        pass
                raise
            
            # Extract the response text
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                logger.error("Empty response from OpenAI API")
                return ""
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
            
    def classify(self, url: str, domain: str, content: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Classify content using OpenAI API.
        
        Args:
            url: URL of the content
            domain: Domain of the URL
            content: Optional content text
            metadata: Optional metadata dictionary
            
        Returns:
            Classification result with category, confidence, and reason
        """
        if not self.can_classify(url, domain):
            logger.warning("OpenAI API not available - using fallback classification")
            return self._fallback_classify(url, domain, content, metadata)
        
        try:
            prompt = self._create_classification_prompt(url, domain, content, metadata)
            
            # Log the full prompt for debugging and prompt engineering
            logger.debug(f"\nFull classification prompt:\n{'-'*50}\n{prompt}\n{'-'*50}")
            
            # Use the OpenAI API to generate classification
            llm_response = self._generate_classification(prompt)
            
            # Log the raw response
            logger.debug(f"\nRaw LLM response:\n{'-'*50}\n{llm_response}\n{'-'*50}")
            
            # Parse the response
            classification, confidence, reason = self._parse_response(llm_response)
            
            # Create and return the standardized result
            # Make sure metadata includes the URL
            if metadata and not metadata.get("url"):
                metadata["url"] = url
                
            result = self.create_result(
                classification=classification,
                reason=reason,
                confidence=confidence,
                metadata={
                    **(metadata or {}),
                    "classifier": "OpenAIClassifier",
                    "model": self.model_name,
                    "domain": domain
                }
            )
            
            # Log parsed result
            logger.info(f"Classification result: {result.label} (score: {result.score:.2f}) - {result.reason}")
            
            return result
        except Exception as e:
            logger.error(f"Error during OpenAI classification: {e}")
            logger.warning("Using fallback classification due to OpenAI API error")
            return self._fallback_classification(url, domain, content, metadata)
            
    def _parse_response(self, response: str) -> Tuple[str, float, str]:
        """
        Parse the OpenAI API response into classification components.
        
        Args:
            response: Raw response from the OpenAI API
            
        Returns:
            Tuple of (classification, confidence, reason)
        """
        try:
            # For JSON responses, try to parse directly
            import json
            import re
            
            # Extract JSON if it exists in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # Extract classification components
                classification = result.get("classification", "").lower()
                confidence = float(result.get("confidence", 0.5))
                reason = result.get("reason", "No reason provided")
                
                # Map to our standard values if needed
                if classification not in ["useful", "distraction", "neutral"]:
                    # Try to map other values to our classification scheme
                    if any(word in classification.lower() for word in ["education", "informative", "learning", "academic", "work"]):
                        classification = "useful"
                    elif any(word in classification.lower() for word in ["entertainment", "distract", "waste", "leisure", "fun"]):
                        classification = "distraction"
                    else:
                        classification = "neutral"
                
                # Ensure confidence is in 0-1 range
                confidence = max(0.0, min(confidence, 1.0))
                
                return classification, confidence, reason
            
            # If no JSON, try to parse the text directly
            lower_resp = response.lower()
            
            # Simple text-based extraction
            if "useful" in lower_resp or "educational" in lower_resp:
                classification = "useful"
            elif "distraction" in lower_resp or "entertainment" in lower_resp:
                classification = "distraction"
            else:
                classification = "neutral"
            
            # Try to extract confidence
            confidence_match = re.search(r'confidence[:\s]+(\d+(?:\.\d+)?)', lower_resp)
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            
            # Ensure confidence is in 0-1 range
            confidence = max(0.0, min(confidence, 1.0))
            
            # Extract reason if present
            reason_match = re.search(r'reason[:\s]+([^\n]+)', lower_resp)
            reason = reason_match.group(1) if reason_match else "No explicit reason provided"
            
            return classification, confidence, reason
            
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            # Default to neutral classification in case of parsing error
            return "neutral", 0.5, f"Error parsing response: {str(e)}"
    
    def can_classify(self, url: str, domain: str) -> bool:
        """
        Determine if this classifier can handle the given content.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            
        Returns:
            True if OpenAI client is available, False otherwise
        """
        return OPENAI_AVAILABLE and self.client is not None


class OpenAIYouTubeClassifier(OpenAIBaseClassifier):
    """
    YouTube-specific OpenAI classifier that analyzes video metadata.
    
    This classifier specializes in YouTube content and uses OpenAI's powerful models
    to provide more accurate classifications for YouTube videos.
    """
    
    # Set priority high to use it preferentially when available
    _priority = 98
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, model_tier: str = "standard"):
        """
        Initialize the YouTube-specific OpenAI classifier.
        
        Args:
            api_key: OpenAI API key (defaults to config file, then OPENAI_API_KEY environment variable)
            model: Explicit model name to use (overrides model_tier if provided)
            model_tier: Which model tier to use from config ("standard", "premium", or "fast")
        """
        super().__init__(api_key=api_key, model=model, model_tier=model_tier)
        
    def can_classify(self, url: str, domain: str) -> bool:
        """
        Determine if this classifier can handle YouTube content.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            
        Returns:
            True if this is YouTube content and OpenAI is available
        """
        # First check if OpenAI is available
        if not super().can_classify(url, domain):
            return False
            
        # Check if this is a YouTube domain
        youtube_domains = ['youtube.com', 'youtu.be', 'youtube-nocookie.com']
        return any(domain.endswith(yt_domain) for yt_domain in youtube_domains)
        
    def _create_classification_prompt(self, url: str, domain: str, 
                                    content: Optional[str] = None,
                                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a prompt for the OpenAI API tailored for YouTube content.
        
        Args:
            url: Video URL
            domain: Video domain
            content: Raw content text (unused for YouTube)
            metadata: Video metadata
            
        Returns:
            Prompt string for the OpenAI API
        """
        # Extract YouTube-specific metadata
        title = metadata.get('title', 'Unknown video title')
        description = metadata.get('description', 'No description')
        channel = metadata.get('channel', 'Unknown channel')
        tags = metadata.get('tags', [])
        categories = metadata.get('categories', [])
        duration = metadata.get('duration', 0)
        
        # Format tags and categories for the prompt
        formatted_tags = ', '.join(tags[:20]) if tags else 'No tags'
        formatted_categories = ', '.join(categories) if categories else 'No category'
        
        # Create a YouTube-specific prompt
        prompt = f"""Analyze this YouTube video's metadata and classify it as either:
- USEFUL (educational content that helps users learn or improve skills)
- DISTRACTION (entertainment content like music videos, comedy, vlogs, etc.)
- NEUTRAL (content that doesn't clearly fit either category)

YouTube video details:
URL: {url}
Title: {title}
Channel: {channel}
Categories: {formatted_categories}
Duration: {duration} seconds
Tags: {formatted_tags}

Full description:
{description}

Provide your classification in JSON format like this:
{{
  "classification": "useful|distraction|neutral",
  "confidence": [0.0-1.0],
  "reason": "Brief explanation for the classification"
}}

Consider these guidelines:
- Music videos, movie trailers, vlogs, gaming videos are typically DISTRACTION
- Tutorials, documentaries, educational lectures, how-to guides are typically USEFUL
- Focus on content type, not quality or popularity
- The video title, channel, and description are your main clues
"""
        return prompt
