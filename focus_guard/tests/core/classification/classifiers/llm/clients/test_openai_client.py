"""
Tests for OpenAI client implementation.
"""
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from openai import OpenAI
from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
from focus_guard.core.classification.classifiers.llm.base_llm import LLMClient


class TestOpenAIClient:
    """Test the OpenAIClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Set a dummy API key for testing
        os.environ["OPENAI_API_KEY"] = "test-api-key"
    
    def teardown_method(self):
        """Tear down test fixtures."""
        # Clean up environment variables
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
    
    @pytest.mark.asyncio
    async def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
            client = OpenAIClient(api_key="test-api-key")
            assert client.api_key == "test-api-key"
            assert client.model == "gpt-4o-mini"
            assert client.max_tokens == 4096
            assert client.temperature == 0.3
    
    @pytest.mark.asyncio
    async def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
            client = OpenAIClient()
            assert client.api_key == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
            client = OpenAIClient(
                api_key="test-api-key",
                model="gpt-3.5-turbo",
                max_tokens=256,
                temperature=0.7
            )
            assert client.model == "gpt-3.5-turbo"
            assert client.max_tokens == 256
            assert client.temperature == 0.7
    
    @pytest.mark.asyncio
    async def test_init_without_api_key(self):
        """Test initialization without API key."""
        # Remove the environment variable
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        with patch.object(OpenAIClient, "_validate_api_key", return_value=False):
            with pytest.raises(ValueError):
                OpenAIClient()
    
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self):
        """Test generate method with system prompt."""
        # Create a mock response
        mock_message = MagicMock()
        mock_message.content = "Generated text"
        
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        
        # Create a mock OpenAI client with synchronous mock
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create the OpenAIClient with the mock client injected
        with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
            client = OpenAIClient(api_key="test-api-key", client=mock_client)
            
            # Call the generate method with system prompt
            result = await client.generate(
                prompt="Test prompt",
                system_prompt="You are a helpful assistant"
            )
            
            # Check that the result is correct
            assert result == "Generated text"
            
            # Check that the OpenAI client was called with the correct arguments
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args[1]
            assert call_args["model"] == "gpt-4o-mini"
            assert call_args["max_completion_tokens"] == 4096
            # gpt-4o-mini supports temperature
            assert call_args.get("temperature") == 0.3 or "temperature" not in call_args
            assert len(call_args["messages"]) == 2
            assert call_args["messages"][0]["role"] == "system"
            assert call_args["messages"][0]["content"] == "You are a helpful assistant"
            assert call_args["messages"][1]["role"] == "user"
            assert call_args["messages"][1]["content"] == "Test prompt"
    
    @pytest.mark.asyncio
    async def test_generate_without_system_prompt(self):
        """Test generate method without system prompt."""
        # Create a mock OpenAI client
        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        
        # Create a mock response
        mock_message = MagicMock()
        mock_message.content = "Generated text"
        
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        
        # Set up the mock create method (synchronous)
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create the OpenAIClient with the mock client injected
        with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
            client = OpenAIClient(api_key="test-api-key", client=mock_client)
            
            # Call the generate method without system prompt
            result = await client.generate(prompt="Test prompt")
            
            # Check that the result is correct
            assert result == "Generated text"
            
            # Check that the OpenAI client was called with the correct arguments
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args[1]
            assert len(call_args["messages"]) == 1
            assert call_args["messages"][0]["role"] == "user"
            assert call_args["messages"][0]["content"] == "Test prompt"
    
    @pytest.mark.asyncio
    async def test_generate_with_custom_params(self):
        """Test generate method with custom parameters."""
        # Create a mock OpenAI client
        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        
        # Create a mock response
        mock_message = MagicMock()
        mock_message.content = "Generated text"
        
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        
        # Set up the mock create method (synchronous)
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create the OpenAIClient with the mock client injected
        with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
            client = OpenAIClient(api_key="test-api-key", client=mock_client)
            
            # Call the generate method with custom parameters
            result = await client.generate(
                prompt="Test prompt",
                model="gpt-3.5-turbo",
                max_tokens=256,
                temperature=0.7
            )
            
            # Check that the result is correct
            assert result == "Generated text"
            
            # Check that the OpenAI client was called with the correct arguments
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args[1]
            assert call_args["model"] == "gpt-3.5-turbo"
            assert call_args["max_completion_tokens"] == 256  # OpenAI client uses max_completion_tokens for all models
            assert call_args["temperature"] == 0.7
    
    @pytest.mark.asyncio
    async def test_generate_handles_api_error(self):
        """Test that generate method handles API errors."""
        # Create a mock OpenAI client
        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        
        # Set up the mock create method to raise an exception (synchronous)
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Create the OpenAIClient with the mock client injected
        with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
            client = OpenAIClient(api_key="test-api-key", client=mock_client)
            
            # The generate method should return None when there's an error
            result = await client.generate(prompt="Test prompt")
            assert result is None
            
            # Check that the OpenAI client was called
            mock_client.chat.completions.create.assert_called_once()
    
    def test_protocol_compliance(self):
        """Test that OpenAIClient complies with LLMClient protocol."""
        # Create a mock OpenAI client
        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        
        # Create the OpenAIClient with the mock client injected
        with patch.object(OpenAIClient, "_validate_api_key", return_value=True):
            client = OpenAIClient(api_key="test-api-key", client=mock_client)
            
            # Check that the client implements the LLMClient protocol
            assert hasattr(client, 'generate')
            assert callable(getattr(client, 'generate', None))
            assert isinstance(client, LLMClient)
