"""
Keyword Classifier

This module provides a general-purpose classifier based on URL keywords and patterns.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from urllib.parse import urlparse
import os

from ..base_classifier import ContentClassifier

# Set up logging
logger = logging.getLogger(__name__)


class KeywordClassifier(ContentClassifier):
    """
    General-purpose classifier based on URL keywords and patterns.
    
    This classifier acts as a fallback when more specialized classifiers
    cannot confidently classify a URL.
    """
    
    def __init__(self):
        """Initialize the keyword classifier with pattern lists."""
        # Useful keywords (work, productivity, learning)
        self.useful_keywords: Set[str] = {
            # Learning and education
            'learn', 'course', 'class', 'lesson', 'tutorial', 'education',
            'university', 'college', 'school', 'academy', 'institute',
            'knowledge', 'study', 'research', 'science', 'academic',
            
            # Work and productivity
            'work', 'job', 'career', 'resume', 'cv', 'hire', 'employment',
            'professional', 'business', 'industry', 'corporate',
            'productivity', 'task', 'project', 'schedule', 'planning',
            'document', 'spreadsheet', 'presentation', 'report',
            
            # Development and creation
            'develop', 'code', 'program', 'software', 'app', 'api',
            'data', 'analytics', 'statistics', 'github', 'stack', 'overflow',
            'documentation', 'manual', 'reference', 'guide', 'help',
            
            # Finance and business
            'finance', 'banking', 'investment', 'stock', 'market',
            'budget', 'accounting', 'tax', 'invoice', 'payment',
            
            # Health and wellness
            'health', 'medical', 'doctor', 'nutrition', 'exercise',
            'fitness', 'wellness', 'medicine', 'therapy', 'treatment'
        }
        
        # Distraction keywords (entertainment, social media, shopping)
        self.distraction_keywords: Set[str] = {
            # Entertainment
            'game', 'play', 'fun', 'entertainment', 'movie', 'video', 'stream',
            'watch', 'tv', 'show', 'series', 'episode', 'film', 'trailer',
            'music', 'song', 'concert', 'festival', 'party', 'celebrity',
            
            # Social media
            'social', 'share', 'friend', 'follow', 'like', 'comment', 'post',
            'status', 'feed', 'trending', 'viral', 'popular', 'chat',
            'message', 'dating', 'match', 'profile', 'selfie', 'photo',
            
            # Shopping and deals
            'shop', 'buy', 'purchase', 'deal', 'discount', 'sale', 'cheap',
            'offer', 'coupon', 'price', 'product', 'item', 'cart', 'checkout',
            'order', 'delivery', 'shipping', 'amazon', 'ebay', 'walmart',
            
            # Gaming
            'game', 'gaming', 'play', 'player', 'steam', 'xbox', 'playstation',
            'nintendo', 'console', 'download', 'dlc', 'mmorpg', 'rpg', 'fps',
            
            # News and media
            'gossip', 'celebrity', 'star', 'headline', 'tabloid', 'buzz',
            'clickbait', 'scandal', 'controversy', 'drama', 'paparazzi'
        }
        
        # Neutral keywords (information, tools, references)
        self.neutral_keywords: Set[str] = {
            'info', 'information', 'data', 'facts', 'details', 'description',
            'review', 'compare', 'analysis', 'overview', 'summary',
            'tool', 'utility', 'converter', 'calculator', 'generator',
            'tracker', 'monitor', 'check', 'validate', 'verify',
            'reference', 'dictionary', 'encyclopedia', 'wiki', 'faq',
            'forum', 'discussion', 'community', 'board', 'group'
        }
        
        # Domain-specific patterns for classification
        self.domain_patterns = {
            # Useful domains
            'useful': [
                r'\.edu$', r'\.gov$', r'\.org$',  # Educational, government, non-profit
                r'docs\.', r'sheets\.', r'slides\.', r'forms\.',  # Document tools
                r'github\.', r'gitlab\.', r'bitbucket\.',  # Code repositories
                r'stackoverflow\.', r'stackexchange\.',  # Programming Q&A
                r'linkedin\.', r'indeed\.', r'glassdoor\.',  # Career
                r'coursera\.', r'udemy\.', r'edx\.', r'khan',  # Learning platforms
                r'medium\.', r'dev\.to', r'hackernoon\.',  # Tech articles
                r'trello\.', r'asana\.', r'jira\.',  # Project management
                r'calendar\.', r'mail\.'  # Productivity tools
            ],
            
            # Distraction domains
            'distraction': [
                r'facebook\.', r'twitter\.', r'instagram\.',  # Social media
                r'tiktok\.', r'snapchat\.', r'pinterest\.',
                r'reddit\.', r'tumblr\.', r'quora\.',
                r'youtube\.', r'vimeo\.', r'twitch\.',  # Video
                r'netflix\.', r'hulu\.', r'disneyplus\.',  # Streaming
                r'spotify\.', r'soundcloud\.', r'pandora\.',  # Music
                r'amazon\.', r'ebay\.', r'etsy\.',  # Shopping
                r'buzzfeed\.', r'boredpanda\.', r'9gag\.',  # Entertainment
                r'ign\.', r'gamespot\.', r'kotaku\.',  # Gaming
                r'espn\.', r'bleacherreport\.'  # Sports
            ],
            
            # Neutral domains
            'neutral': [
                r'google\.com$', r'bing\.com$', r'yahoo\.com$',  # Search engines
                r'wikipedia\.', r'wikihow\.',  # Reference
                r'weather\.', r'accuweather\.',  # Weather
                r'maps\.', r'openstreetmap\.',  # Maps
                r'translate\.', r'dictionary\.',  # Language tools
                r'news\.'  # News (could be useful or distraction)
            ]
        }

    @property
    def priority(self) -> int:
        """Return priority (higher = checked first)."""
        return 30  # Low priority, used as fallback
        
    def can_classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> bool:
        """
        Keyword classifier can attempt to classify any URL.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            bool: True for any URL (fallback classifier)
        """
        return True  # This classifier can try to classify any URL
        
    def classify(self, url: str, domain: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Classify a URL based on keywords and patterns.
        
        Args:
            url: The full URL to classify
            domain: The domain part of the URL
            metadata: Optional metadata that may help with classification
            
        Returns:
            Dict with standardized classification result
        """
        try:
            # First check domain patterns
            domain_class, domain_confidence = self._classify_by_domain_pattern(domain)
            
            # Then check URL keywords
            keyword_class, keyword_confidence, matched_keywords = self._classify_by_keywords(url)
            
            # Use the more confident result, or domain pattern if equal
            if domain_confidence >= keyword_confidence:
                classification = domain_class
                confidence = domain_confidence
                reason = f"Domain pattern match for {domain}"
                metadata_dict = {"match_type": "domain_pattern"}
            else:
                classification = keyword_class
                confidence = keyword_confidence
                reason = f"Keyword matches: {', '.join(matched_keywords)}"
                metadata_dict = {
                    "match_type": "keywords",
                    "matched_keywords": matched_keywords
                }
            
            return self.create_result(
                classification=classification,
                reason=reason,
                confidence=confidence,
                metadata=metadata_dict
            )
            
        except Exception as e:
            logger.error(f"Error in keyword classifier: {str(e)}")
            return self.create_result(
                classification="neutral",  # Default to neutral on error
                reason="Error in keyword classification",
                confidence=0.5,
                metadata={"error": str(e)}
            )
            
    def _classify_by_domain_pattern(self, domain: str) -> Tuple[str, float]:
        """Classify based on domain patterns."""
        domain = domain.lower()
        
        for classification, patterns in self.domain_patterns.items():
            for pattern in patterns:
                if re.search(pattern, domain):
                    # Higher confidence for more specific matches
                    confidence = 0.7 if classification != "neutral" else 0.6
                    return classification, confidence
                    
        # Default if no patterns match
        return "neutral", 0.5
        
    def _classify_by_keywords(self, url: str) -> Tuple[str, float, List[str]]:
        """Classify based on keywords in the URL."""
        url_lower = url.lower()
        
        # Count keyword matches
        useful_matches = []
        distraction_matches = []
        neutral_matches = []
        
        # Check for useful keywords
        for keyword in self.useful_keywords:
            if keyword in url_lower:
                useful_matches.append(keyword)
                
        # Check for distraction keywords
        for keyword in self.distraction_keywords:
            if keyword in url_lower:
                distraction_matches.append(keyword)
                
        # Check for neutral keywords
        for keyword in self.neutral_keywords:
            if keyword in url_lower:
                neutral_matches.append(keyword)
                
        # Determine classification based on matches
        useful_count = len(useful_matches)
        distraction_count = len(distraction_matches)
        neutral_count = len(neutral_matches)
        
        # No matches at all
        if useful_count == 0 and distraction_count == 0 and neutral_count == 0:
            return "neutral", 0.5, []
            
        # Calculate confidence based on keyword count differences
        total_count = useful_count + distraction_count + neutral_count
        
        if useful_count > distraction_count and useful_count > neutral_count:
            confidence = 0.6 + min((useful_count / total_count) * 0.2, 0.2)
            return "useful", confidence, useful_matches
            
        elif distraction_count > useful_count and distraction_count > neutral_count:
            confidence = 0.6 + min((distraction_count / total_count) * 0.2, 0.2)
            return "distraction", confidence, distraction_matches
            
        elif neutral_count > useful_count and neutral_count > distraction_count:
            confidence = 0.5 + min((neutral_count / total_count) * 0.1, 0.1)
            return "neutral", confidence, neutral_matches
            
        # Mixed signals, return the category with most matches
        if useful_count >= distraction_count and useful_count >= neutral_count:
            return "useful", 0.6, useful_matches
        elif distraction_count >= useful_count and distraction_count >= neutral_count:
            return "distraction", 0.6, distraction_matches
        else:
            return "neutral", 0.55, neutral_matches


# Create instance
keyword_classifier = KeywordClassifier()
