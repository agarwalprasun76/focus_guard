"""
Local LLM client implementation for classification."""

import logging
from typing import Optional, Dict, Any

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

from .base_llm import LLMClient

logger = logging.getLogger(__name__)

class LocalLLMClient(LLMClient):
    """Local LLM client for classification."""
    
    def __init__(
        self,
        model_name: str = "mistralai/Mistral-7B-Instruct-v0.1",
        max_length: int = 512,
        temperature: float = 0.7,
        load_in_8bit: bool = False,
        load_in_4bit: bool = True,
        device_map: str = "auto",
        **kwargs
    ):
        """Initialize the local LLM client.
        
        Args:
            model_name: Name or path of the model to load.
            max_length: Maximum length of generated text.
            temperature: Sampling temperature.
            load_in_8bit: Whether to load the model in 8-bit precision.
            load_in_4bit: Whether to load the model in 4-bit precision.
            device_map: Device to load the model on ('auto', 'cpu', 'cuda', etc.).
            **kwargs: Additional arguments to pass to the model and tokenizer.
        """
        self.model_name = model_name
        self.max_length = max_length
        self.temperature = temperature
        
        # Configure model loading kwargs
        model_kwargs = {
            "device_map": device_map,
            "trust_remote_code": kwargs.get("trust_remote_code", True),
        }
        
        # Add quantization config if needed
        if load_in_8bit or load_in_4bit:
            try:
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=load_in_8bit,
                    load_in_4bit=load_in_4bit,
                    **kwargs.get("quantization_config", {})
                )
                model_kwargs["quantization_config"] = quantization_config
            except ImportError:
                logger.warning(
                    "BitsAndBytes not installed. Install with: pip install bitsandbytes"
                )
        
        # Load model and tokenizer
        logger.info(f"Loading model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, **kwargs)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            **model_kwargs
        )
        
        # Configure tokenizer
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "left"
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using the local LLM.
        
        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.
            **kwargs: Additional generation parameters.
            
        Returns:
            The generated text.
        """
        # Format the prompt with system message if provided
        if system_prompt:
            full_prompt = f"""<s>[INST] <<SYS>>
{system_prompt}
<</SYS>>

{prompt} [/INST]"""
        else:
            full_prompt = f"<s>[INST] {prompt} [/INST]"
        
        # Tokenize the input
        inputs = self.tokenizer(
            full_prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_token_type_ids=False
        ).to(self.model.device)
        
        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=kwargs.get("max_length", self.max_length),
                temperature=kwargs.get("temperature", self.temperature),
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        # Decode and clean up the response
        response = self.tokenizer.decode(
            outputs[0][len(inputs["input_ids"][0]):],
            skip_special_tokens=True
        ).strip()
        
        return response
