"""
Base interfaces for domain-specific classifiers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol, runtime_checkable

from focus_guard.core.domain.models import Domain, Classification

@runtime_checkable
class DomainClassifier(Protocol):
    """Protocol for domain classifiers."""
    
    @property
    def name(self) -> str:
        """Get the name of the classifier."""
        ...
    
    @abstractmethod
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify a domain with optional context."""
        ...


class BaseDomainClassifier(ABC):
    """Base class for domain classifiers."""
    
    def __init__(self, name: str):
        """Initialize with a name for the classifier."""
        self._name = name
    
    @property
    def name(self) -> str:
        """Get the name of the classifier."""
        return self._name
    
    @abstractmethod
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify a domain with optional context.
        
        Args:
            domain: The domain to classify.
            context: Optional context for classification.
            
        Returns:
            A ClassificationResult if classification was successful, None otherwise.
        """
        ...


class RuleBasedDomainClassifier(BaseDomainClassifier):
    """Base class for rule-based domain classifiers."""
    
    def __init__(self, name: str):
        """Initialize with a name for the classifier."""
        super().__init__(name)
    
    @abstractmethod
    def _get_rules(self) -> Dict[str, Any]:
        """Get the classification rules for this domain.
        
        Returns:
            A dictionary of rules for classification.
        """
        ...
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify a domain using the configured rules."""
        # Default implementation - should be overridden by subclasses
        rules = self._get_rules()
        # Apply rules here
        return None


class LLMBasedDomainClassifier(BaseDomainClassifier):
    """Base class for LLM-based domain classifiers."""
    
    def __init__(
        self,
        name: str,
        llm_client: 'LLMClient',  # type: ignore
        system_prompt: str,
        response_format: Dict[str, Any]
    ):
        """Initialize with an LLM client and configuration.
        
        Args:
            name: Name of the classifier.
            llm_client: An LLM client instance.
            system_prompt: System prompt for the LLM.
            response_format: Expected response format specification.
        """
        super().__init__(name)
        self.llm_client = llm_client
        self.system_prompt = system_prompt
        self.response_format = response_format
    
    @abstractmethod
    def _format_prompt(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format the prompt for the LLM.
        
        Args:
            domain: The domain to classify.
            context: Optional context for classification.
            
        Returns:
            A formatted prompt string.
        """
        ...
    
    @abstractmethod
    def _parse_response(
        self,
        response: str,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Classification:
        """Parse the LLM response into a classification result.
        
        Args:
            response: The raw response from the LLM.
            domain: The domain that was classified.
            context: Optional context used for classification.
            
        Returns:
            A ClassificationResult object.
        """
        ...
    
    async def classify(
        self,
        domain: Domain,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Classification]:
        """Classify a domain using the LLM."""
        try:
            prompt = self._format_prompt(domain, context or {})
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            return self._parse_response(response, domain, context)
        except Exception as e:
            import logging
            logging.error(f"LLM classification failed for {domain}: {e}")
            return None
