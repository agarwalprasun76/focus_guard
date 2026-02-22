"""
Base interfaces for domain-specific classifiers."""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol, runtime_checkable

from focus_guard.core.domain.models import Domain, Category, Classification


def clean_llm_json(text: str) -> str:
    """Clean LLM response to extract JSON.
    
    Handles common LLM response patterns like code fences.
    """
    if text is None:
        return "{}"
    txt = text.strip()
    if "```" in txt:
        if "```json" in txt.lower():
            try:
                return txt.lower().split("```json", 1)[1].split("```", 1)[0].strip()
            except Exception:
                pass
        try:
            return txt.split("```", 1)[1].split("```", 1)[0].strip()
        except Exception:
            pass
    return txt


def parse_llm_classification_response(
    response: str,
    domain: Domain,
    classifier_name: str,
    categories: list,
    usefulness_values: list,
) -> Classification:
    """Parse a standard LLM classification response into a Classification object.
    
    Args:
        response: Raw LLM response string
        domain: The domain being classified
        classifier_name: Name of the classifier for metadata
        categories: List of valid category strings
        usefulness_values: List of valid usefulness strings
        
    Returns:
        Classification object with parsed data in metadata
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if response is None:
        return Classification(
            domain=domain,
            category=Category.UNKNOWN,
            confidence=0.0,
            metadata={
                "classifier": classifier_name,
                "usefulness": "NEUTRAL",
                "reason": "LLM returned None response",
            }
        )
    
    try:
        json_str = clean_llm_json(response)
        data = json.loads(json_str)
    except Exception as e:
        logger.warning(f"JSON parse failed: {e}. Raw: {response[:500]}")
        try:
            json_str = json_str[json_str.find("{"): json_str.rfind("}") + 1]
            data = json.loads(json_str)
        except Exception as e2:
            logger.error(f"Failed to parse LLM response: {e2}")
            return Classification(
                domain=domain,
                category=Category.UNKNOWN,
                confidence=0.0,
                metadata={
                    "classifier": classifier_name,
                    "usefulness": "NEUTRAL",
                    "reason": f"JSON parse failed: {e2}",
                }
            )
    
    # Validate category
    cat = str(data.get("category", "")).upper()
    if cat not in categories:
        logger.warning(f"Invalid category '{cat}' from LLM")
        cat = "UNKNOWN"
    
    # Map to Category enum
    category_map = {
        "EDUCATION": Category.EDUCATION,
        "ENTERTAINMENT": Category.ENTERTAINMENT,
        "SOCIAL_MEDIA": Category.SOCIAL_MEDIA,
        "GAMING": Category.GAMING,
        "NEWS": Category.NEWS,
        "SHOPPING": Category.SHOPPING,
        "PRODUCTIVITY": Category.PRODUCTIVITY,
        "ADULT": Category.ADULT,
        "MALICIOUS": Category.MALICIOUS,
        "UNKNOWN": Category.UNKNOWN,
    }
    category = category_map.get(cat, Category.UNKNOWN)
    
    # Validate usefulness
    usefulness = str(data.get("usefulness", "")).upper()
    if usefulness not in usefulness_values:
        usefulness = "NEUTRAL"
    
    # Parse confidence
    try:
        confidence = float(data.get("confidence", 0.7))
        confidence = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        confidence = 0.7
    
    return Classification(
        domain=domain,
        category=category,
        confidence=confidence,
        metadata={
            "classifier": classifier_name,
            "usefulness": usefulness,
            "reason": data.get("reason", ""),
        }
    )

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
