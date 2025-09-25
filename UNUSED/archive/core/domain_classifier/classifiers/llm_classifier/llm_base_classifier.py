"""
Base class for LLM-based content classifiers

This module provides the base functionality for using small language models
to classify content as educational, entertainment, or neutral.
"""

import os
import json
import time
import logging
import traceback
from typing import Dict, Any, Tuple, List, Optional

# Import the shared ClassificationResult type
from ..utils import ClassificationResult

# Suppress Hugging Face symlinks warning on Windows
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

# Core imports
from core.logger.logger import get_logger
from core.domain_classifier.base_classifier import ContentClassifier
from core.domain_classifier.metadata import metadata_fetcher

# Set up logging
logger = get_logger('domain_classifier.llm_classifier')

# Try importing the required LLM libraries, but provide graceful fallbacks
TRANSFORMERS_AVAILABLE = False
TORCH_AVAILABLE = False
BNB_AVAILABLE = False

# Check for PyTorch
try:
    import torch
    TORCH_AVAILABLE = True
    logger.info("PyTorch detected - required for LLM functionality")
except ImportError:
    logger.warning("PyTorch not found - LLM will use fallback classification")

# Check for Transformers
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    TRANSFORMERS_AVAILABLE = True
    logger.info("Transformers library detected - LLM functionality available")
except ImportError:
    logger.warning("Transformers library not found - LLM functionality will be limited")
    
# Check for BitsAndBytes (for 8-bit quantization)
try:
    import bitsandbytes
    BNB_AVAILABLE = True
    logger.info("BitsAndBytes detected - 8-bit quantization available")
except ImportError:
    logger.info("BitsAndBytes not found - will use 16-bit precision instead")
    
# Overall LLM availability
LLM_AVAILABLE = TRANSFORMERS_AVAILABLE and TORCH_AVAILABLE


class LLMBaseClassifier(ContentClassifier):
    """
    Base class for classifiers using small language models for content classification.
    
    This classifier uses a small language model (like Llama 3B) to analyze content
    metadata and determine whether it's educational (useful), entertainment (distraction),
    or neutral.
    """
    
    # Default priority value - can be overridden in subclasses
    _priority = 90
    
    @property
    def priority(self) -> int:
        """
        Return the priority of this classifier.
        
        Higher priority classifiers are checked first in the classification chain.
        
        Returns:
            int: Priority value (higher = checked first)
        """
        return self._priority
        
    def can_classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> bool:
        """
        Determine if this classifier can handle the given content.
        Base implementation always returns False, subclasses should override.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            bool: True if this classifier can handle this content, False otherwise
        """
        # Base class can't classify anything directly
        return False
    
    def __init__(self, model_name_or_path: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
        """
        Initialize the LLM-based classifier.
        
        Args:
            model_name_or_path: HuggingFace model name or local path to model
        """
        self.model_name = model_name_or_path
        self.metadata_fetcher = metadata_fetcher
        self.model = None
        self.tokenizer = None
        self.generator = None
        self._load_model()
    
    def _load_model(self):
        """Load the language model if dependencies are available."""
        if not LLM_AVAILABLE:
            logger.warning("Cannot load LLM - required libraries not installed")
            return
            
        try:
            logger.info(f"Loading language model: {self.model_name}")
            
            # First load tokenizer - this is usually lighter weight
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Determine model loading parameters based on available libraries
            model_kwargs = {}
            
            # Use half-precision for memory efficiency if CUDA is available
            if torch.cuda.is_available():
                model_kwargs["torch_dtype"] = torch.float16
                model_kwargs["device_map"] = "auto"
                logger.info("CUDA detected - using GPU acceleration")
            else:
                logger.info("CUDA not detected - using CPU only")
            
            # Use 8-bit quantization if bitsandbytes is available
            if BNB_AVAILABLE and torch.cuda.is_available():
                model_kwargs["load_in_8bit"] = True
                logger.info("Using 8-bit quantization for reduced memory usage")
            else:
                # If no quantization is available, we'll use 16-bit or 32-bit
                # depending on available memory
                pass
            
            # Now try loading the model with the determined parameters
            logger.info(f"Loading model with parameters: {model_kwargs}")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs
            )
            
            # Create generator pipeline with safe defaults
            self.generator = pipeline(
                "text-generation", 
                model=self.model, 
                tokenizer=self.tokenizer,
                max_new_tokens=200  # Limit output length to be safe
            )
            
            logger.info("Language model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load language model: {e}")
            logger.error(traceback.format_exc())
            self.model = None
            self.tokenizer = None
    
    def classify(self, url: str, domain: str, content: str = None, 
                 metadata: Dict[str, Any] = None) -> ClassificationResult:
        """
        Classify content using the language model.
        
        Args:
            url: URL of content to classify
            domain: Domain of the content
            content: Raw content text if available
            metadata: Metadata dictionary if already fetched
            
        Returns:
            Dictionary with classification results
        """
        # Fetch metadata if not provided
        if not metadata:
            metadata = self.metadata_fetcher.fetch_metadata(url)
            if not metadata:
                return self.create_result(
                    "error",
                    "Failed to fetch metadata for LLM classification",
                    0.5
                )
        
        # Skip LLM classification if model couldn't be loaded
        if not self.model or not self.tokenizer:
            logger.warning("LLM classification requested but model not available - using fallback")
            return self._fallback_classification(url, domain, content, metadata)
        
        try:
            # Create prompt for classification
            prompt = self._create_classification_prompt(url, domain, content, metadata)
            logger.info("===== CLASSIFICATION PROMPT DETAILS START =====")
            logger.info(f"Prompt: {prompt}")
            logger.info("===== CLASSIFICATION PROMPT DETAILS END =====")
            
            # Log the full prompt and metadata for debugging
            logger.info("===== CLASSIFICATION REQUEST DETAILS =====")
            logger.info(f"URL: {url}")
            logger.info(f"Domain: {domain}")
            
            # Pretty-print metadata for readability in logs only
            # NOTE: This only truncates the displayed values in logs, not the actual data sent to the LLM
            logger.info("Metadata sent to LLM (truncated for log readability):")
            for key, value in metadata.items():
                if key not in ['error', 'html'] and not key.startswith('_'):
                    # Create a display-only copy of the value for logging
                    display_value = value
                    if isinstance(display_value, str) and len(display_value) > 100:
                        display_value = display_value[:100] + "..."
                    logger.info(f"  {key}: {display_value}")
            
            # Log the full prompt
            logger.info("\nFull LLM Prompt:")
            logger.info(prompt)
            logger.info("========================================\n")
            
            # Generate classification with the LLM
            start_time = time.time()
            classification_result = self._generate_classification(prompt)
            elapsed_time = time.time() - start_time
            
            logger.debug(f"LLM classification completed in {elapsed_time:.2f} seconds")
            
            # Log the raw LLM response
            logger.info("===== LLM RESPONSE =====")
            logger.info(classification_result)
            logger.info("========================\n")
            
            # Parse the LLM's response
            classification, confidence, reason = self._parse_llm_response(classification_result)
            
            # Log the parsed classification results
            logger.info("===== PARSED CLASSIFICATION =====")
            logger.info(f"Classification: {classification}")
            logger.info(f"Confidence: {confidence:.2f}")
            logger.info(f"Reason: {reason}")
            logger.info("================================\n")
            
            # Create standardized result with original metadata preserved
            result = self.create_result(
                classification=classification,
                reason=reason,
                confidence=confidence,
                metadata={
                    **metadata,  # Include original metadata
                    "classifier": "LLMClassifier",
                    "llm_model": self.model_name, 
                    "response_time": elapsed_time
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in LLM classification: {e}")
            logger.error(traceback.format_exc())
            return self._fallback_classification(url, domain, content, metadata)
    
    def _create_classification_prompt(self, url: str, domain: str, content: str, 
                                      metadata: Dict[str, Any]) -> str:
        """
        Create a prompt for the language model to classify the content.
        
        This base implementation provides a generic prompt.
        Subclasses should override this method to provide domain-specific prompts.
        
        Args:
            url: Content URL
            domain: Content domain
            content: Raw content text
            metadata: Content metadata
            
        Returns:
            String prompt for the language model
        """
        title = metadata.get('title', 'Unknown title')
        description = metadata.get('description', 'No description')
        
        # Create a simple prompt for the language model
        prompt = f"""Given the following content from {domain}, classify it as either 'useful' (educational),
'distraction' (entertainment), or 'neutral'. Respond with a JSON object only.

URL: {url}
Title: {title}
Description: {description[:300]}...

Classify this content based on whether it's educational or entertainment.
Respond with a JSON object in this format:
{{
  "classification": "useful|distraction|neutral",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<brief explanation>"
}}
"""
        return prompt
    
    def _generate_classification(self, prompt: str) -> str:
        """
        Generate a classification response using the language model.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            The model's text response
        """
        try:
            # Generate text with the pipeline
            response = self.generator(
                prompt,
                do_sample=True,
                temperature=0.1,  # Low temperature for more deterministic outputs
                max_length=len(self.tokenizer(prompt)["input_ids"]) + 300,  # Limit output length
                num_return_sequences=1
            )
            
            # Extract the generated text
            generated_text = response[0]["generated_text"]
            
            # Extract just the model's response (remove the prompt)
            model_response = generated_text[len(prompt):].strip()
            
            return model_response
            
        except Exception as e:
            logger.error(f"Error generating classification: {e}")
            logger.error(traceback.format_exc())
            return "{}"
    
    def _parse_llm_response(self, response: str) -> Tuple[str, float, str]:
        """
        Parse the LLM's response to extract classification, confidence, and reason.
        
        Args:
            response: The raw text response from the LLM
            
        Returns:
            Tuple of (classification, confidence, reason)
        """
        try:
            # Try to extract JSON from the response
            json_str = self._extract_json(response)
            
            if not json_str:
                logger.warning(f"Could not extract JSON from LLM response: {response[:100]}...")
                return "neutral", 0.5, "Failed to parse LLM response"
                
            # Parse the JSON
            result = json.loads(json_str)
            
            # Extract the classification details
            classification = result.get("classification", "neutral").lower()
            confidence = float(result.get("confidence", 0.5))
            reason = result.get("reason", "No reason provided")
            
            # Validate classification
            if classification not in ["useful", "distraction", "neutral"]:
                logger.warning(f"Invalid classification: {classification}, defaulting to neutral")
                classification = "neutral"
                
            # Clamp confidence between 0 and 1
            confidence = max(0.0, min(confidence, 1.0))
            
            return classification, confidence, reason
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.error(traceback.format_exc())
            return "neutral", 0.5, f"Error parsing response: {str(e)}"
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from a text response that might contain other text.
        
        Args:
            text: Text that might contain JSON
            
        Returns:
            Extracted JSON string or empty string if not found
        """
        # Try to find JSON between curly braces
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if json_match:
            return json_match.group(0)
        
        return ""
    
    def create_result(self, classification: str, reason: str, confidence: float, 
                     metadata: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Create a standardized classification result.
        
        Args:
            classification: 'useful', 'distraction', or 'neutral'
            reason: Human-readable explanation
            confidence: Confidence score (0-1)
            metadata: Optional metadata dict
            
        Returns:
            ClassificationResult object
        """
        # Convert our classification to content_type and label
        content_type = "educational" if classification == "useful" else \
                      "entertainment" if classification == "distraction" else "neutral"
        
        # Normalize the decision
        decision = classification.upper()
        
        # Convert confidence from 0-1 to percentage
        score = confidence * 100
        
        # Create the result object
        return ClassificationResult(
            url=metadata.get("url", ""),
            content_type=content_type,
            label=classification,
            score=score,
            decision=decision,
            reason=reason,
            metadata=metadata
        )

    def _fallback_classification(self, url: str, domain: str, content: str, 
                                 metadata: Dict[str, Any]) -> ClassificationResult:
        """
        Fallback classification when LLM is not available or fails.
        
        This provides a simple keyword-based classification as fallback.
        Subclasses can override this to provide better fallbacks.
        
        Args:
            url: Content URL
            domain: Content domain
            content: Raw content text
            metadata: Content metadata
            
        Returns:
            ClassificationResult object
        """
        # Very simple fallback logic
        title = metadata.get('title', '').lower()
        description = metadata.get('description', '').lower()
        
        educational_keywords = ["learn", "course", "education", "tutorial", "lecture"]
        entertainment_keywords = ["funny", "music", "game", "play", "entertainment"]
        
        edu_score = sum(1 for kw in educational_keywords if kw in title or kw in description)
        ent_score = sum(1 for kw in entertainment_keywords if kw in title or kw in description)
        
        # Make sure metadata has the URL
        if not metadata.get("url"):
            metadata["url"] = url
            
        if edu_score > ent_score:
            return self.create_result(
                "useful", 
                f"Educational content (fallback classification)",
                0.6,
                metadata
            )
        elif ent_score > edu_score:
            return self.create_result(
                "distraction", 
                f"Entertainment content (fallback classification)",
                0.6,
                metadata
            )
        else:
            return self.create_result(
                "neutral", 
                f"Could not determine content type (fallback classification)",
                0.5,
                metadata
            )
