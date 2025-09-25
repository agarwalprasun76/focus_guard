"""
Common utilities and shared types for classifiers

This module provides shared data types and utility functions used by
multiple classifiers in the system.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel


class ClassificationResult(BaseModel):
    """Model for content classification results."""
    url: str
    content_type: str
    label: str
    score: float
    decision: str
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
