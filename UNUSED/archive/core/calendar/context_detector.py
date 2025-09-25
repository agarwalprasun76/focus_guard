"""
Enhanced context detection using sentence transformers for semantic understanding of calendar events.
"""
from typing import List, Dict, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class ContextDetector:
    """
    Uses sentence transformers to detect context from calendar event titles and descriptions.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the context detector with a pre-trained sentence transformer model.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model = SentenceTransformer(model_name)
        self.context_embeddings = {}
        self.context_definitions = {}
        
        # Define context categories with example phrases
        self.define_contexts()
        
    def define_contexts(self):
        """Define the contexts we want to detect with example phrases."""
        self.context_definitions = {
            "meeting": [
                "team meeting", "standup", "sync", "1:1", "discussion",
                "planning", "review", "retrospective", "workshop"
            ],
            "focus_work": [
                "focus time", "deep work", "coding", "writing", 
                "development", "implementation", "research"
            ],
            "math_science": [
                "math", "calculus", "algebra", "physics", "chemistry",
                "problem set", "homework", "study session", "research"
            ],
            "break": [
                "lunch", "break", "coffee", "walk", "rest", "dinner",
                "breakfast", "gym", "exercise"
            ],
            "after_hours": [
                "personal time", "evening", "night", "weekend", "off hours"
            ]
        }
        
        # Pre-compute embeddings for all context phrases
        for context, phrases in self.context_definitions.items():
            self.context_embeddings[context] = self.model.encode(phrases)
    
    def detect_context(self, text: str, threshold: float = 0.4) -> List[Tuple[str, float]]:
        """
        Detect the most likely contexts from the input text.
        
        Args:
            text: Input text (event title/description)
            threshold: Minimum similarity score to consider a match
            
        Returns:
            List of (context, score) tuples, sorted by score descending
        """
        if not text or not text.strip():
            return []
            
        # Encode the input text
        text_embedding = self.model.encode([text], convert_to_tensor=True)
        
        # Calculate similarity with each context
        results = []
        for context, context_embeddings in self.context_embeddings.items():
            # Calculate cosine similarity with all phrases for this context
            similarities = cosine_similarity(
                text_embedding.cpu().numpy(),
                context_embeddings
            )
            # Take the maximum similarity score for this context
            max_similarity = float(np.max(similarities))
            if max_similarity >= threshold:
                results.append((context, max_similarity))
        
        # Sort by score descending
        return sorted(results, key=lambda x: x[1], reverse=True)
    
    def get_primary_context(self, text: str, threshold: float = 0.4) -> Optional[str]:
        """
        Get the most likely context for the given text.
        
        Args:
            text: Input text (event title/description)
            threshold: Minimum similarity score to consider a match
            
        Returns:
            The most likely context, or None if no context matches above threshold
        """
        contexts = self.detect_context(text, threshold)
        return contexts[0][0] if contexts else None

# Singleton instance
_context_detector = None

def get_context_detector() -> ContextDetector:
    """Get or create the singleton context detector instance."""
    global _context_detector
    if _context_detector is None:
        _context_detector = ContextDetector()
    return _context_detector
