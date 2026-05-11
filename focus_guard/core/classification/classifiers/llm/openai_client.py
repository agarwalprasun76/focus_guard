"""
OpenAI client implementation for LLM classification."""

import os
import logging
import asyncio
import time
from typing import Optional, Dict, Any

import openai
from openai import OpenAI

from focus_guard.core.program_data_paths import read_openai_api_key_from_api_token_file

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
            api_key: OpenAI API key. If None, uses ``OPENAI_API_KEY`` if set, else
                optional ``openai_api_key`` in ``%ProgramData%\\FocusGuard\\api_token.json``
                (same file as the tab-server bearer token).
            model: The model to use (e.g., "gpt-5-nano").
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature.
            client: Optional pre-configured client for testing.
            **kwargs: Additional arguments to pass to the OpenAI client.
        """
        if api_key:
            self.api_key = api_key
            _key_source = "constructor_argument"
        elif os.getenv("OPENAI_API_KEY", "").strip():
            self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
            _key_source = "OPENAI_API_KEY_environment"
        else:
            self.api_key = read_openai_api_key_from_api_token_file()
            _key_source = "api_token.json" if self.api_key else "none"
        if not self._validate_api_key(self.api_key):
            raise ValueError(
                "OpenAI API key is required. Pass it directly, set OPENAI_API_KEY, "
                "or add openai_api_key to %ProgramData%\\FocusGuard\\api_token.json."
            )
        logger.info(
            "OpenAI client initialized; key source=%s (env overrides ProgramData file if both are set).",
            _key_source,
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
            err_s = str(e)
            logger.error("OpenAI API error: %s", e)
            if "401" in err_s or "invalid_api_key" in err_s or "Incorrect API key" in err_s:
                logger.warning(
                    "OpenAI returned 401 (invalid or revoked key). Set a valid OPENAI_API_KEY or "
                    "openai_api_key in %%ProgramData%%\\FocusGuard\\api_token.json. "
                    "Rule-based classifiers will still run where configured."
                )
            return None
