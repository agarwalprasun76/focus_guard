"""
OpenAI client implementation for LLM classification."""

import os
import logging
import asyncio
import time
from typing import Optional, Dict, Any

import openai
from openai import OpenAI

from .base_llm import LLMClient

logger = logging.getLogger(__name__)

class OpenAIClient(LLMClient):
    """OpenAI client for LLM classification."""
    
    # Class-level rate limiting (optimized for better performance)
    _last_request_time = 0
    _min_request_interval = 0.01  # Reduced from 60ms to 10ms for better performance
    _consecutive_rate_limits = 0  # Track consecutive rate limit hits
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        client=None,  # Added for testing
        **kwargs
    ):
        """Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key. If None, will use OPENAI_API_KEY env var.
            model: The model to use (e.g., "gpt-5-nano").
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature.
            client: Optional pre-configured client for testing.
            **kwargs: Additional arguments to pass to the OpenAI client.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._validate_api_key(self.api_key):
            raise ValueError(
                "OpenAI API key is required. Either pass it directly or set the "
                "OPENAI_API_KEY environment variable."
            )
        
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        # Use the provided client if available (for testing), otherwise create a new one
        self.client = client if client is not None else OpenAI(api_key=self.api_key, **kwargs)
        
        # Models that use max_completion_tokens instead of max_tokens
        self._uses_completion_tokens = self._model_uses_completion_tokens(model)
        
    def _model_uses_completion_tokens(self, model: str) -> bool:
        """Check if the model uses max_completion_tokens instead of max_tokens.
        
        Args:
            model: The model name.
            
        Returns:
            True if the model uses max_completion_tokens, False otherwise.
        """
        # Models that use the new parameter format
        completion_token_models = [
            "gpt-5-nano",
            "gpt-4o",
            "gpt-4o-mini",
            "o1-preview",
            "o1-mini"
        ]
        return any(model.startswith(prefix) for prefix in completion_token_models)
    
    def _model_supports_temperature(self, model: str) -> bool:
        """Check if the model supports custom temperature values.
        
        Args:
            model: The model name.
            
        Returns:
            True if the model supports custom temperature, False otherwise.
        """
        # Models that don't support custom temperature (only default value of 1)
        no_temperature_models = [
            "gpt-5-nano",
            "o1-preview",
            "o1-mini",
            "text-davinci-003",
            "text-davinci-002",
            "text-curie-001",
            "text-babbage-001",
            "text-ada-001"
        ]
        return not any(model.startswith(prefix) for prefix in no_temperature_models)
    
    def _validate_api_key(self, api_key):
        """Validate the API key.
        
        Args:
            api_key: The API key to validate.
            
        Returns:
            True if the API key is valid, False otherwise.
        """
        return bool(api_key)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using the OpenAI API.
        
        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.
            **kwargs: Additional arguments to pass to the API.
            
        Returns:
            The generated text.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare API parameters
        model_name = kwargs.get("model", self.model)
        api_params = {
            "model": model_name,
            "messages": messages,
        }
        
        # Add temperature only if the model supports it
        if self._model_supports_temperature(model_name):
            api_params["temperature"] = kwargs.get("temperature", self.temperature)
        
        # Use the correct token parameter based on the model
        max_tokens_value = kwargs.get("max_tokens", self.max_tokens)
        if self._uses_completion_tokens:
            api_params["max_completion_tokens"] = max_tokens_value
        else:
            api_params["max_tokens"] = max_tokens_value
        
        try:
            # Rate limiting: ensure minimum interval between requests
            current_time = time.time()
            time_since_last = current_time - OpenAIClient._last_request_time
            if time_since_last < self._min_request_interval:
                sleep_time = self._min_request_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
                await asyncio.sleep(sleep_time)
            
            OpenAIClient._last_request_time = time.time()
            
            logger.debug(f"Making OpenAI API call with params: {api_params}")
            response = self.client.chat.completions.create(**api_params)
            logger.debug(f"OpenAI API response: {response}")
            
            if not response.choices:
                logger.error("OpenAI API returned no choices")
                return None
                
            choice = response.choices[0]
            if not hasattr(choice, 'message'):
                logger.error(f"OpenAI API choice has no message: {choice}")
                return None
                
            content = choice.message.content
            if content is None:
                logger.warning(f"OpenAI API returned None content. Full response: {response}")
                logger.warning(f"Choice: {choice}")
                logger.warning(f"Message: {choice.message}")
            else:
                logger.debug(f"OpenAI API returned content: {content[:200]}...")
            return content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
