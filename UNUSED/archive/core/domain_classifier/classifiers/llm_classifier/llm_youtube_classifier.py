"""
YouTube-specific LLM classifier

This module provides a specialized LLM classifier for YouTube content,
optimized for distinguishing between educational and entertainment videos.
"""

import os
import re
import json
from typing import Dict, Any, Optional, Tuple, List

# Core imports
from core.logger.logger import get_logger
from core.domain_classifier.utils import EDUCATIONAL_CHANNELS
from .llm_base_classifier import LLMBaseClassifier

# Set up logging
logger = get_logger('domain_classifier.llm_youtube_classifier')


class LLMYouTubeClassifier(LLMBaseClassifier):
    """
    YouTube-specific LLM classifier that analyzes video metadata to determine content type.
    
    This classifier specializes in YouTube content and uses video metadata like titles,
    descriptions, tags, etc. to provide more accurate classifications for YouTube videos.
    """
    
    # Set YouTube classifier to have high priority (but below domain blocklists)
    _priority = 85
    
    def can_classify(self, url: str, domain: str) -> bool:
        """
        Determine if this classifier can handle YouTube content.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            
        Returns:
            bool: True if this is YouTube content, False otherwise
        """
        # Check if this is a YouTube domain
        youtube_domains = ['youtube.com', 'youtu.be', 'youtube-nocookie.com']
        if any(domain.endswith(yt_domain) for yt_domain in youtube_domains):
            return True
            
        return False
    
    def __init__(self, model_name_or_path: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
        """
        Initialize the YouTube-specific LLM classifier.
        
        Args:
            model_name_or_path: The name or path of the pretrained model to use.
        """
        # Set priority before calling super().__init__ to ensure proper initialization
        self._priority = 95  # Set high priority to match YouTubeClassifier
        super().__init__(model_name_or_path)
        
    def can_classify(self, url: str, domain: str) -> bool:
        """
        Check if this classifier can handle the given URL.
        
        Args:
            url: URL to check
            domain: Domain of the URL
            
        Returns:
            True if this classifier can handle the URL
        """
        youtube_domains = ["youtube.com", "youtu.be", "m.youtube.com"]
        return any(ytd in domain for ytd in youtube_domains)
    
    def _create_classification_prompt(self, url: str, domain: str, 
                                     content: str, metadata: Dict[str, Any]) -> str:
        """
        Create a YouTube-specific classification prompt.
        
        Args:
            url: Video URL
            domain: Video domain
            content: Raw content text (unused for YouTube)
            metadata: Video metadata
            
        Returns:
            Prompt string for the LLM
        """
        # Extract YouTube-specific metadata
        title = metadata.get('title', 'Unknown video title')
        description = metadata.get('description', 'No description')
        channel = metadata.get('channel', 'Unknown channel')
        tags = metadata.get('tags', [])
        categories = metadata.get('categories', [])
        duration = metadata.get('duration', 0)
        
        # Format tags and categories for the prompt
        formatted_tags = ', '.join(tags[:20]) if tags else 'No tags'  # Limit to 20 tags
        formatted_categories = ', '.join(categories) if categories else 'No category'
        
        # Use the full description to give LLM maximum context
        # We previously truncated to 500 chars, but this led to missing important context
        
        # Educational channel check
        is_edu_channel = channel in EDUCATIONAL_CHANNELS
        edu_channel_note = "(Known educational channel)" if is_edu_channel else ""
        
        # Create a YouTube-specific prompt
        prompt = f"""You are an AI designed to classify YouTube content as either:
1. 'useful' (educational content that helps users learn)
2. 'distraction' (entertainment content that may distract users)
3. 'neutral' (content that doesn't clearly fit either category)

Analyze the following YouTube video metadata:

URL: {url}
Title: {title}
Channel: {channel} {edu_channel_note}
Category: {formatted_categories}
Tags: {formatted_tags}
Duration: {duration} seconds
Description:
{description}

Classification guidelines:
- 'useful': Educational videos, tutorials, documentaries, how-to guides, lectures
- 'distraction': Music videos, gaming, comedy, vlogs, entertainment shows
- 'neutral': News, product reviews, or content that serves both purposes

Respond ONLY with a JSON object in this format:
{{
  "classification": "useful|distraction|neutral",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<brief explanation for classification>"
}}
"""
        return prompt

    def _fallback_classification(self, url: str, domain: str, content: str,
                               metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        YouTube-specific fallback classification when LLM fails.
        
        This provides a more sophisticated YouTube-specific fallback.
        
        Args:
            url: Video URL
            domain: Video domain
            content: Raw content text
            metadata: Video metadata
            
        Returns:
            Classification result dictionary
        """
        title = metadata.get('title', '').lower()
        description = metadata.get('description', '').lower() 
        channel = metadata.get('channel', '')
        tags = [tag.lower() for tag in metadata.get('tags', [])]
        categories = [cat.lower() for cat in metadata.get('categories', [])]
        
        # Check if it's a known educational channel
        if channel in EDUCATIONAL_CHANNELS:
            return self.create_result(
                "useful",
                f"Educational YouTube channel: {channel}",
                0.85,
                metadata
            )
            
        # Check video categories
        educational_categories = ["education", "science & technology", "howto & style"]
        entertainment_categories = ["music", "gaming", "comedy", "entertainment", "sports"]
        
        for category in categories:
            if category in educational_categories:
                return self.create_result(
                    "useful",
                    f"Educational YouTube category: {category}",
                    0.8, 
                    metadata
                )
            if category in entertainment_categories:
                return self.create_result(
                    "distraction",
                    f"Entertainment YouTube category: {category}",
                    0.8,
                    metadata
                )
                
        # Check for educational patterns in title/description
        edu_patterns = [
            r'\b(tutorial|course|learn|lesson|education|lecture|how to)\b',
            r'\bexplain(s|ed|ing)?\b'
        ]
        
        for pattern in edu_patterns:
            if re.search(pattern, title) or re.search(pattern, description):
                return self.create_result(
                    "useful",
                    "Educational content based on title/description keywords",
                    0.7,
                    metadata
                )
                
        # Check for entertainment patterns
        ent_patterns = [
            r'\b(gameplay|funny|music video|song|official video|trailer|vlog)\b',
            r'\b(episode|season|show|series)\b'
        ]
        
        for pattern in ent_patterns:
            if re.search(pattern, title) or re.search(pattern, description):
                return self.create_result(
                    "distraction",
                    "Entertainment content based on title/description keywords",
                    0.7, 
                    metadata
                )
                
        # If we can't determine, return neutral
        return self.create_result(
            "neutral",
            "Could not confidently classify YouTube content",
            0.5,
            metadata
        )
