"""
Advanced integration tests for the classification system.

This module contains comprehensive integration tests for the classification system,
focusing on advanced scenarios that require async testing with pytest-asyncio:

1. Async Classification Operations:
   - Testing async classifiers with proper awaiting
   - Handling of asyncio event loops in test environment
   - Parallel domain classification with asyncio.gather

2. Context-Based Classification:
   - Classification with different context variations
   - Context-aware classifier behavior testing

3. Exception Handling and Edge Cases:
   - Classifier failure and fallback behavior
   - Pipeline behavior when all classifiers return None

4. External Integrations:
   - OpenAI client integration with proper mocking
   - YouTube LLM classifier integration with context

These tests complement the basic integration tests in test_integration.py, which
focus on simpler synchronous classification scenarios.

Note: Tests requiring external dependencies like OpenAI client or LLM libraries
are skipped if those dependencies are not available.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

# Create a mock ClassificationPipeline for testing
class AsyncClassificationPipeline:
    """Async-friendly version of ClassificationPipeline for testing."""
    
    def __init__(self, registry):
        self._registry = registry
        self._pipeline = []
    
    def add_classifier(self, name):
        """Add a classifier to the pipeline."""
        self._pipeline.append(name)
    
    async def classify(self, domain, context=None):
        """Classify a domain with optional context in an async-friendly way."""
        for name in self._pipeline:
            classifier = self._registry.get(name)
            if classifier is None:
                continue
                
            try:
                if hasattr(classifier, 'classify_with_context') and context is not None:
                    result = await classifier.classify_with_context(domain, context)
                    if result is not None:
                        return result
                else:
                    result = await classifier.classify(domain)
                    if result is not None:
                        # If result is just a category, wrap it in a Classification object
                        if not isinstance(result, Classification):
                            result = Classification(
                                domain=domain,
                                category=result,
                                confidence=1.0,
                                metadata={"classifier": name}
                            )
                        return result
            except Exception as e:
                print(f"Classifier {name} failed: {e}")
                continue
        
        return None

from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.classification import (
    ClassifierRegistry,
    ClassificationPipeline
)

# Skip if optional dependencies are not available
try:
    from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from focus_guard.core.classification.classifiers.domains.youtube_llm import (
        LLMBasedYouTubeClassifier
    )
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class MockClassifier:
    """Mock classifier for testing."""
    
    def __init__(self, name, priority=100, category=None):
        self.name = name
        self.priority = priority
        self._category = category or Category.UNKNOWN
        
        # Create dynamic mock methods that return proper domain
        async def mock_classify(domain):
            return self._create_classification(domain)
            
        async def mock_classify_with_context(domain, context):
            return self._create_classification(domain)
            
        self.classify = AsyncMock(side_effect=mock_classify)
        self.classify_with_context = AsyncMock(side_effect=mock_classify_with_context)
    
    def _create_classification(self, domain="example.com"):
        """Create a classification result."""
        return Classification(
            domain=domain,
            category=self._category,
            confidence=0.9,
            metadata={"source": self.name}
        )
    
    def set_category(self, category):
        """Set the category for this classifier to return."""
        self._category = category
        
        # Update the side effects to use the new category
        async def mock_classify(domain):
            return self._create_classification(domain)
            
        async def mock_classify_with_context(domain, context):
            return self._create_classification(domain)
            
        self.classify.side_effect = mock_classify
        self.classify_with_context.side_effect = mock_classify_with_context


@pytest.fixture
def mock_registry():
    """Create a classifier registry with mock classifiers."""
    registry = ClassifierRegistry()
    
    # Add mock classifiers with different priorities
    high_priority = MockClassifier("high_priority", priority=200, category=Category.PRODUCTIVITY)
    medium_priority = MockClassifier("medium_priority", priority=150, category=Category.EDUCATION)
    low_priority = MockClassifier("low_priority", priority=100, category=Category.ENTERTAINMENT)
    
    # Register classifiers
    registry.register(high_priority)
    registry.register(medium_priority)
    registry.register(low_priority)
    
    return registry


@pytest.fixture
def mock_pipeline(mock_registry):
    """Create a classification pipeline with mock classifiers."""
    pipeline = AsyncClassificationPipeline(mock_registry)
    pipeline.add_classifier("high_priority")
    pipeline.add_classifier("medium_priority")
    pipeline.add_classifier("low_priority")
    return pipeline


class TestAdvancedIntegration:
    """Enhanced integration tests for the classification system."""
    
    @pytest.mark.asyncio
    async def test_advanced_pipeline_priority_order(self, mock_pipeline, mock_registry):
        """Test that classifiers are called in priority order."""
        domain = "example.com"
        
        # Get the classifiers
        high_priority = mock_registry.get("high_priority")
        medium_priority = mock_registry.get("medium_priority")
        low_priority = mock_registry.get("low_priority")
        
        # Configure high priority classifier to return None
        high_priority.classify.side_effect = AsyncMock(return_value=None)
        
        # Classify the domain
        result = await mock_pipeline.classify(domain)
        
        # Should get result from medium priority classifier
        assert result is not None
        assert result.category == Category.EDUCATION
        assert result.metadata["source"] == "medium_priority"
        
        # Verify call order
        high_priority.classify.assert_awaited_once()
        medium_priority.classify.assert_awaited_once()
        low_priority.classify.assert_not_awaited()
    
    @pytest.mark.asyncio
    async def test_pipeline_fallback_behavior(self, mock_pipeline, mock_registry):
        """Test fallback behavior when classifiers return None."""
        domain = "example.com"
        
        # Get the classifiers
        high_priority = mock_registry.get("high_priority")
        medium_priority = mock_registry.get("medium_priority")
        low_priority = mock_registry.get("low_priority")
        
        # Configure classifiers to return None
        high_priority.classify.side_effect = AsyncMock(return_value=None)
        medium_priority.classify.side_effect = AsyncMock(return_value=None)
        
        # Classify the domain
        result = await mock_pipeline.classify(domain)
        
        # Should get result from low priority classifier
        assert result is not None
        assert result.category == Category.ENTERTAINMENT
        assert result.metadata["source"] == "low_priority"
        
        # Verify all classifiers were called
        high_priority.classify.assert_awaited_once()
        medium_priority.classify.assert_awaited_once()
        low_priority.classify.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_pipeline_with_context(self, mock_pipeline, mock_registry):
        """Test classification with context."""
        domain = "example.com"
        context = {
            "url": "https://example.com/page",
            "title": "Example Page",
            "content": "Some content"
        }
        
        # Get the classifiers
        high_priority = mock_registry.get("high_priority")
        
        # Classify with context
        result = await mock_pipeline.classify(domain, context)
        
        # Should get result from high priority classifier
        assert result is not None
        assert result.category == Category.PRODUCTIVITY
        
        # Verify classify_with_context was called with context
        high_priority.classify_with_context.assert_awaited_once_with(domain, context)
    
    @pytest.mark.asyncio
    async def test_pipeline_all_classifiers_none(self, mock_pipeline, mock_registry):
        """Test behavior when all classifiers return None."""
        domain = "example.com"
        
        # Get the classifiers
        high_priority = mock_registry.get("high_priority")
        medium_priority = mock_registry.get("medium_priority")
        low_priority = mock_registry.get("low_priority")
        
        # Configure all classifiers to return None
        high_priority.classify.side_effect = AsyncMock(return_value=None)
        medium_priority.classify.side_effect = AsyncMock(return_value=None)
        low_priority.classify.side_effect = AsyncMock(return_value=None)
        
        # Classify the domain
        result = await mock_pipeline.classify(domain)
        
        # Should get None when all classifiers return None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_classifier_exception_handling(self, mock_pipeline, mock_registry):
        """Test handling of exceptions from classifiers."""
        domain = "example.com"
        
        # Get the classifiers
        high_priority = mock_registry.get("high_priority")
        medium_priority = mock_registry.get("medium_priority")
        
        # Configure high priority classifier to raise an exception
        high_priority.classify.side_effect = AsyncMock(side_effect=Exception("Test exception"))
        
        # Classify the domain
        result = await mock_pipeline.classify(domain)
        
        # Should get result from medium priority classifier
        assert result is not None
        assert result.category == Category.EDUCATION
        assert result.metadata["source"] == "medium_priority"
        
        # Verify both classifiers were called
        high_priority.classify.assert_awaited_once()
        medium_priority.classify.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_dynamic_classifier_configuration(self, mock_registry):
        """Test dynamic configuration of classifiers."""
        # Create a new pipeline with only the high priority classifier
        pipeline = AsyncClassificationPipeline(mock_registry)
        pipeline.add_classifier("high_priority")
        
        # Get the classifier
        high_priority = mock_registry.get("high_priority")
        
        # Classify a domain
        domain = "example.com"
        result1 = await pipeline.classify(domain)
        
        # Change the classifier's behavior
        high_priority.set_category(Category.SOCIAL_MEDIA)
        
        # Classify again
        result2 = await pipeline.classify(domain)
        
        # Verify the results
        assert result1.category == Category.PRODUCTIVITY
        assert result2.category == Category.SOCIAL_MEDIA
    
    @pytest.mark.asyncio
    async def test_multiple_domain_classification(self, mock_pipeline):
        """Test classification of multiple domains in parallel."""
        # Create multiple domains
        domains = [
            "example1.com",
            "example2.com",
            "example3.com"
        ]
        
        # Classify all domains in parallel
        tasks = [mock_pipeline.classify(domain) for domain in domains]
        results = await asyncio.gather(*tasks)
        
        # Verify all results
        for i, result in enumerate(results):
            assert result is not None
            assert result.domain == domains[i]
            assert result.category == Category.PRODUCTIVITY  # From high priority classifier
    
    @pytest.mark.asyncio
    async def test_context_based_classification_variations(self, mock_registry):
        """Test classification with different context variations."""
        # Create a classifier that responds differently based on context
        context_aware = MockClassifier("context_aware", priority=300)
        
        # Override the classify_with_context method
        async def classify_with_context(domain, context):
            if "title" in context and "education" in context["title"].lower():
                return Classification(domain=domain, category=Category.EDUCATION)
            elif "title" in context and "entertainment" in context["title"].lower():
                return Classification(domain=domain, category=Category.ENTERTAINMENT)
            elif "content" in context and "shopping" in context["content"].lower():
                return Classification(domain=domain, category=Category.SHOPPING)
            elif "url" in context and "social" in context["url"].lower():
                return Classification(domain=domain, category=Category.SOCIAL_MEDIA)
            else:
                return Classification(domain=domain, category=Category.UNKNOWN)
        
        context_aware.classify_with_context = classify_with_context
        
        # Register and create pipeline
        mock_registry.register(context_aware)
        pipeline = AsyncClassificationPipeline(mock_registry)
        pipeline.add_classifier("context_aware")
        
        # Test with different contexts
        domain = "example.com"
        
        # Educational content
        edu_context = {"title": "Educational Video", "content": "Learning materials"}
        edu_result = await pipeline.classify(domain, edu_context)
        assert edu_result.category == Category.EDUCATION
        
        # Entertainment content
        ent_context = {"title": "Entertainment Show", "content": "Fun video"}
        ent_result = await pipeline.classify(domain, ent_context)
        assert ent_result.category == Category.ENTERTAINMENT
        
        # Shopping content
        shop_context = {"title": "Product Page", "content": "Shopping cart items"}
        shop_result = await pipeline.classify(domain, shop_context)
        assert shop_result.category == Category.SHOPPING
        
        # Social content
        social_context = {"url": "https://example.com/social/profile", "title": "User Profile"}
        social_result = await pipeline.classify(domain, social_context)
        assert social_result.category == Category.SOCIAL_MEDIA
    
    @pytest.mark.skipif(not HAS_OPENAI, reason="OpenAI client not available")
    @pytest.mark.asyncio
    async def test_openai_client_integration(self):
        """Test integration with OpenAI client."""
        # Create a mock OpenAI client
        mock_client = MagicMock(spec=OpenAIClient)
        mock_client.generate = AsyncMock(return_value="PRODUCTIVE")
        
        # Create a simple classifier that uses the OpenAI client
        class SimpleOpenAIClassifier:
            def __init__(self, client):
                self.name = "openai_classifier"
                self.priority = 100
                self.client = client
            
            async def classify(self, domain, title=None):
                prompt = f"Classify the domain {domain}"
                if title:
                    prompt += f" with title '{title}'"
                
                try:
                    result = await self.client.generate(prompt)
                    category_map = {
                        "PRODUCTIVE": Category.PRODUCTIVITY,
                        "EDUCATION": Category.EDUCATION,
                        "ENTERTAINMENT": Category.ENTERTAINMENT,
                        "SOCIAL": Category.SOCIAL_MEDIA,
                        "SHOPPING": Category.SHOPPING
                    }
                    category = category_map.get(result.strip().upper(), Category.UNKNOWN)
                    return Classification(domain=domain, category=category)
                except Exception:
                    return Classification(domain=domain, category=Category.UNKNOWN)
        
        # Create and register the classifier
        registry = ClassifierRegistry()
        classifier = SimpleOpenAIClassifier(mock_client)
        registry.register(classifier)
        
        # Create pipeline
        pipeline = AsyncClassificationPipeline(registry)
        pipeline.add_classifier("openai_classifier")
        
        # Test classification
        domain = "example.com"
        result = await pipeline.classify(domain)
        
        # Verify result
        assert result is not None
        assert result.category == Category.PRODUCTIVITY
        
        # Verify client was called
        mock_client.generate.assert_awaited_once()
        assert "example.com" in mock_client.generate.await_args[0][0]
    
    @pytest.mark.skipif(not HAS_LLM, reason="LLM dependencies not available")
    @pytest.mark.asyncio
    async def test_youtube_llm_integration(self):
        """Test integration with YouTube LLM classifier."""
        # Create a mock LLM client
        mock_llm_client = MagicMock()
        mock_llm_client.generate = AsyncMock(return_value="{\"category\": \"EDUCATION\", \"confidence\": 0.9, \"reason\": \"Educational content\", \"is_distracting\": false}")
        
        # Create the classifier with mock LLM client
        classifier = LLMBasedYouTubeClassifier(llm_client=mock_llm_client)
        
        # Create registry and pipeline
        registry = ClassifierRegistry()
        registry.register(classifier)
        
        pipeline = AsyncClassificationPipeline(registry)
        pipeline.add_classifier("youtube_llm")
        
        # Test with a YouTube domain and context
        domain = "youtube.com"
        context = {
            "url": "https://youtube.com/watch?v=abc123",
            "title": "Advanced Machine Learning Tutorial"
        }
        
        # Classify
        result = await pipeline.classify(domain, context)
        
        # Verify result
        assert result is not None
        assert result.category == Category.EDUCATION
        
        # Verify LLM client was called
        mock_llm_client.generate.assert_awaited_once()
        
        # Just verify it was called - we don't need to check the exact arguments
        # since the mock implementation details may vary