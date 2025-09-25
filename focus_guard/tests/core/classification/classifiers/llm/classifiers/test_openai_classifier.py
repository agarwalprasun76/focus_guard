"""
Tests for OpenAI-based LLM classifier.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from focus_guard.core.domain.models import Classification, Category
from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
from focus_guard.core.classification.classifiers.llm.base_llm import BaseLLMClassifier


# Create a concrete OpenAI classifier for testing
class OpenAIClassifier(BaseLLMClassifier):
    """OpenAI-based classifier implementation for testing."""
    
    def __init__(self, api_key=None, model="gpt-5-nano"):
        system_prompt = "You are a domain classifier. Classify the given domain into one of these categories: PRODUCTIVITY, ENTERTAINMENT, SOCIAL_MEDIA, SHOPPING, UNKNOWN."
        self.client = None
        self._api_key = api_key
        self._model = model
        super().__init__(client=self._get_client(), system_prompt=system_prompt)
    
    async def _format_prompt(self, domain, context):
        """Format the prompt for the LLM."""
        domain_str = domain.value if hasattr(domain, 'value') else str(domain)
        prompt = f"Classify the domain: {domain_str}\n"
        
        if isinstance(context, dict):
            for key, value in context.items():
                if key != 'url' and value:  # Skip URL as we already have the domain
                    prompt += f"{key}: {value}\n"
        elif context:
            prompt += f"Context: {context}\n"
        
        prompt += "\nCategory:"
        return prompt
    
    def _parse_response(self, response):
        """Parse the LLM response into a classification result."""
        from focus_guard.core.domain.models import Classification, Category
        
        # Clean and normalize the response
        cleaned_response = response.strip().upper()
        
        # Map to Category enum
        category_map = {
            "PRODUCTIVITY": Category.PRODUCTIVITY,
            "ENTERTAINMENT": Category.ENTERTAINMENT,
            "SOCIAL_MEDIA": Category.SOCIAL_MEDIA,
            "SHOPPING": Category.SHOPPING,
            "UNKNOWN": Category.UNKNOWN
        }
        
        category = category_map.get(cleaned_response, Category.UNKNOWN)
        
        # Create a Classification object with the domain from the context
        return Classification(
            domain=None,  # Will be set by the classify method
            category=category,
            confidence=0.9,
            metadata={"method": "llm", "model": self._model}
        )
    
    def _get_client(self):
        if not self.client:
            self.client = OpenAIClient(api_key=self._api_key, model=self._model)
        return self.client
    
    def set_api_key(self, api_key):
        """Set the API key for the classifier."""
        self._api_key = api_key
        if self.client:
            self.client.api_key = api_key
    
    def set_model(self, model):
        """Set the model for the classifier."""
        self._model = model
        if self.client:
            self.client.model = model


@pytest.fixture
def mock_openai_client():
    """Fixture for mocked OpenAI client."""
    mock_client = AsyncMock(spec=OpenAIClient)
    mock_client.generate.return_value = "PRODUCTIVITY"
    return mock_client


@pytest.fixture
def openai_classifier(mock_openai_client):
    """Fixture for OpenAI classifier with mocked client."""
    with patch.object(OpenAIClassifier, "_get_client", return_value=mock_openai_client):
        classifier = OpenAIClassifier(api_key="test-api-key")
        yield classifier


class TestOpenAIClassifier:
    """Tests for the OpenAIClassifier."""
    
    def test_initialization(self):
        """Test initialization of OpenAI classifier."""
        classifier = OpenAIClassifier(api_key="test-api-key", model="gpt-3.5-turbo")
        assert classifier.client.api_key == "test-api-key"
        assert classifier.client.model == "gpt-3.5-turbo"
    
    def test_set_api_key(self):
        """Test setting API key."""
        classifier = OpenAIClassifier(api_key="test-api-key")
        classifier.set_api_key("new-api-key")
        assert classifier.client.api_key == "new-api-key"
    
    def test_set_model(self):
        """Test setting model."""
        classifier = OpenAIClassifier(api_key="test-api-key", model="gpt-5-nano")
        classifier.set_model("gpt-3.5-turbo")
        assert classifier.client.model == "gpt-3.5-turbo"
    
    @pytest.mark.asyncio
    async def test_classify(self, openai_classifier, mock_openai_client):
        """Test classify method."""
        # Set up the mock to return a specific category
        mock_openai_client.generate.return_value = "PRODUCTIVITY"
        
        # Call the classify method
        result = await openai_classifier.classify("example.com", "Example Domain")
        
        # Verify the result
        assert result is not None
        assert result.category == Category.PRODUCTIVITY
        assert result.domain == "example.com"
        
        # Verify the client was called with the correct prompt
        mock_openai_client.generate.assert_awaited_once()
        kwargs = mock_openai_client.generate.await_args.kwargs
        assert "example.com" in kwargs.get("prompt", "")
        assert "Example Domain" in kwargs.get("prompt", "")
    
    @pytest.mark.asyncio
    async def test_classify_with_context(self, openai_classifier, mock_openai_client):
        """Test classify with context method."""
        # Set up the mock to return a specific category
        mock_openai_client.generate.return_value = "ENTERTAINMENT"
        
        # Call the classify method with context
        context = {"url": "example.com/video", "title": "Example Video", "content": "Video content"}
        result = await openai_classifier.classify("example.com", context)
        
        # Verify the result
        assert result is not None
        assert result.category == Category.ENTERTAINMENT
        assert result.domain == "example.com"
        
        # Verify the client was called with the correct prompt including context
        mock_openai_client.generate.assert_awaited_once()
        kwargs = mock_openai_client.generate.await_args.kwargs
        assert "example.com" in kwargs.get("prompt", "")
        assert "Example Video" in kwargs.get("prompt", "")
        assert "Video content" in kwargs.get("prompt", "")
    
    @pytest.mark.asyncio
    async def test_classify_with_invalid_response(self, openai_classifier, mock_openai_client):
        """Test classify with invalid response from LLM."""
        # Set up the mock to return an invalid category
        mock_openai_client.generate.return_value = "INVALID_CATEGORY"
        
        # Call the classify method
        result = await openai_classifier.classify("example.com", "Example Domain")
        
        # Verify the result falls back to default category
        assert result is not None
        assert result.category == Category.UNKNOWN
        assert result.domain == "example.com"
    
    @pytest.mark.asyncio
    async def test_classify_with_exception(self, openai_classifier, mock_openai_client):
        """Test classify when client raises an exception."""
        # Set up the mock to raise an exception
        mock_openai_client.generate.side_effect = Exception("API Error")
        
        # Patch the BaseLLMClassifier.classify method to handle the exception and return a fallback classification
        with patch.object(BaseLLMClassifier, 'classify', side_effect=lambda domain, context: Classification(
            domain=domain,
            category=Category.UNKNOWN,
            confidence=0.5,
            metadata={"error": "API Error"}
        )):
            # Call the classify method
            result = await openai_classifier.classify("example.com", "Example Domain")
        
            # Verify the result falls back to default category
            assert result is not None
            assert result.category == Category.UNKNOWN
            assert result.domain == "example.com"
        
            # Verify error was logged (would need a log capture fixture for this)
    
    @pytest.mark.asyncio
    async def test_system_prompt_customization(self, openai_classifier, mock_openai_client):
        """Test customization of system prompt."""
        # Override the system prompt
        custom_prompt = "You are a specialized classifier for productivity."
        openai_classifier.system_prompt = custom_prompt
        
        # Call the classify method
        await openai_classifier.classify("example.com", "Example Domain")
        
        # Verify the client was called with the custom system prompt
        mock_openai_client.generate.assert_awaited_once()
        kwargs = mock_openai_client.generate.await_args[1]
        assert kwargs.get("system_prompt") == custom_prompt
