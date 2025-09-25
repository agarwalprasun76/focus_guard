"""
Base LLM classifier interface.

This module defines the base interface for all LLM-based classifiers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
import logging

from focus_guard.core.domain.models import Classification, Domain

logger = logging.getLogger(__name__)

@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM clients."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text from the LLM."""
        ...


class BaseLLMClassifier(ABC):
    """Base class for LLM-based classifiers."""
    
    def __init__(self, client: LLMClient, system_prompt: str):
        """Initialize with an LLM client and system prompt."""
        self.client = client
        self.system_prompt = system_prompt
    
    @abstractmethod
    async def _format_prompt(self, domain: Domain, context: Dict[str, Any]) -> str:
        """Format the prompt for the LLM."""
        ...
    
    @abstractmethod
    def _parse_response(self, response: str) -> Classification:
        """Parse the LLM response into a classification result."""
        ...
    
    async def classify(
        self,
        domain: Domain,
        context: Dict[str, Any]
    ) -> Optional[Classification]:
        """Classify content using the LLM."""
        try:
            prompt = await self._format_prompt(domain, context)
            response = await self.client.generate(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            classification = self._parse_response(response)
            if classification:
                classification.domain = domain
            return classification
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return None
