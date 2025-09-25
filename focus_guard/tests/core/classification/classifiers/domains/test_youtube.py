"""
Tests for YouTube domain classifiers.
"""
import json
import os
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.classification.classifiers.domains.youtube import (
    YouTubeClassifier,
    create_youtube_classifier,
    default_classifier
)
from focus_guard.core.classification.classifiers.domains.youtube_base import (
    YouTubeClassifier as BaseYouTubeClassifier
)
from focus_guard.core.classification.classifiers.domains.youtube_rules import (
    RuleBasedYouTubeClassifier
)

# Skip if optional dependencies are not available
try:
    from focus_guard.core.classification.classifiers.domains.youtube_llm import (
        LLMBasedYouTubeClassifier
    )
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class TestYouTubeClassifier:
    """Tests for the YouTubeClassifier composite class."""
    
    @pytest.fixture
    def mock_rule_classifier(self):
        """Create a mock rule-based classifier."""
        classifier = MagicMock(spec=RuleBasedYouTubeClassifier)
        classifier.name = "mock_rule_classifier"
        classifier.classify.return_value = Category.ENTERTAINMENT
        return classifier
    
    @pytest.fixture
    def mock_llm_classifier(self):
        """Create a mock LLM-based classifier."""
        if not HAS_LLM:
            pytest.skip("LLM dependencies not available")
            
        classifier = MagicMock(spec=LLMBasedYouTubeClassifier)
        classifier.name = "mock_llm_classifier"
        classifier.classify.return_value = Category.EDUCATION
        return classifier
    
    def test_initialization(self, mock_rule_classifier):
        """Test that the classifier initializes with the provided classifiers."""
        classifier = YouTubeClassifier([mock_rule_classifier])
        assert len(classifier.classifiers) == 1
        assert classifier.classifiers[0] == mock_rule_classifier
    
    @pytest.mark.asyncio
    async def test_classify_uses_first_available_classifier(self, mock_rule_classifier):
        """Test that classify() uses the first classifier that returns a result."""
        classifier = YouTubeClassifier([mock_rule_classifier])
        domain = Domain("youtube.com")
        
        # First classifier returns a result
        expected = Classification(domain, Category.EDUCATION)
        mock_rule_classifier.classify.return_value = expected
        
        result = await classifier.classify(domain)
        assert result == expected
        mock_rule_classifier.classify.assert_called_once_with(domain, {})
        
        # Should return the result from the first classifier
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_classify_returns_none_if_no_classifiers(self):
        """Test that classify() returns None if no classifiers are available."""
        classifier = YouTubeClassifier([])
        result = await classifier.classify(Domain("youtube.com"))
        assert result is None
    
    @pytest.mark.skipif(not HAS_LLM, reason="LLM dependencies not available")
    def test_create_default_includes_llm_if_available(self, mock_rule_classifier, mock_llm_classifier):
        """Test that create_default() includes LLM classifier if available."""
        with patch('focus_guard.core.classification.classifiers.domains.youtube_rules.RuleBasedYouTubeClassifier',
                  return_value=mock_rule_classifier), \
             patch('focus_guard.core.classification.classifiers.domains.youtube_llm.LLMBasedYouTubeClassifier',
                  return_value=mock_llm_classifier), \
             patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            
            classifier = YouTubeClassifier.create_default()
            assert len(classifier.classifiers) == 2
            assert any(isinstance(c, type(mock_rule_classifier)) for c in classifier.classifiers)
            assert any(isinstance(c, type(mock_llm_classifier)) for c in classifier.classifiers)


class TestRuleBasedYouTubeClassifier:
    """Tests for the RuleBasedYouTubeClassifier class."""
    
    @pytest.fixture
    def classifier(self):
        """Create a test instance of RuleBasedYouTubeClassifier."""
        return RuleBasedYouTubeClassifier()
    
    @pytest.mark.parametrize("url,title,expected_category", [
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", "Funny cat video compilation", Category.ENTERTAINMENT),  # Entertainment content
        ("https://youtube.com/watch?v=12345&t=30s", "Epic gaming moments", Category.GAMING),    # Gaming content
        ("https://youtu.be/dQw4w9WgXcQ", "Amazing dance moves", Category.ENTERTAINMENT),               # Short URL
        ("https://youtube.com/playlist?list=PL12345", "Comedy playlist", Category.ENTERTAINMENT),  # Playlist
        ("https://youtube.com/channel/UC12345", "", Category.UNKNOWN),        # Channel - browsing page
        ("https://youtube.com/shorts/abc123", "Viral TikTok dance", Category.ENTERTAINMENT),          # Shorts
        ("https://youtube.com/live/xyz789", "Music video compilation", Category.ENTERTAINMENT),            # Live stream with entertainment content
        ("https://youtube.com/user/username", "", Category.UNKNOWN),          # User page - browsing page
    ])
    def test_youtube_domains(self, classifier, url, title, expected_category):
        """Test that YouTube domains are correctly identified."""
        domain = Domain("youtube.com")  # Domain is the same, we're testing URL handling
        context = {"url": url, "title": title}
        
        result = classifier.classify_with_context(domain, context)
        assert result is not None
        assert result.category == expected_category
    
    @pytest.mark.parametrize("title,expected_category", [
        ("How to code in Python tutorial", Category.EDUCATION),
        ("Learn React in 1 hour - Full Beginner's Tutorial", Category.EDUCATION),
        ("University Lecture on Physics", Category.EDUCATION),
        ("Tutorial: How to Code", Category.EDUCATION),
        ("Minecraft Let's Play Ep. 1", Category.GAMING),
        ("Fortnite Season 5 Gameplay", Category.GAMING),
        ("iPhone 13 Unboxing and Review", Category.SHOPPING),
        ("Top 10 Best Laptops 2023", Category.SHOPPING),
        ("Breaking News: Major Event Happening Now", Category.NEWS),
        ("Today's Headlines - August 4, 2023", Category.NEWS),
        ("Funny Cat Videos", Category.ENTERTAINMENT),
        ("Movie Trailer: Avengers", Category.ENTERTAINMENT),
        ("Music Video - New Song", Category.ENTERTAINMENT),
        ("Productivity Tips and Tricks", Category.PRODUCTIVITY),
        ("Time Management Strategies", Category.PRODUCTIVITY),
        ("Work From Home Effectively", Category.PRODUCTIVITY),
        ("Free Robux Generator 2023 (Working)", Category.ENTERTAINMENT),  # Falls back to ENTERTAINMENT
    ])
    def test_content_classification(self, classifier, title, expected_category):
        """Test that content is classified based on title keywords."""
        domain = Domain("youtube.com")
        context = {
            "url": "https://youtube.com/watch?v=test123",
            "title": title,
            "description": ""  # Empty description for testing
        }
        
        result = classifier.classify_with_context(domain, context)
        if expected_category is None:
            assert result is None
        else:
            assert result is not None
            assert result.category == expected_category
    
    @pytest.mark.asyncio
    async def test_non_youtube_domain(self, classifier):
        """Test that non-YouTube domains return None."""
        domain = Domain("example.com")
        result = await classifier.classify(domain)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_classify_with_missing_context(self, classifier):
        """Test classify with missing context."""
        domain = Domain("youtube.com")
        
        # No context provided - YouTube classifier returns browsing allowlist
        result = await classifier.classify(domain)
        assert result is not None
        assert result.category == Category.UNKNOWN
        assert 'youtube_browsing_allow' in result.metadata['rules_applied']
        
        # Empty context - also returns browsing allowlist
        result = await classifier.classify(domain, {})
        assert result is not None
        assert result.category == Category.UNKNOWN
        assert 'youtube_browsing_allow' in result.metadata['rules_applied']
        
        # Context without URL - still returns browsing allowlist
        result = await classifier.classify(domain, {"title": "Test Video"})
        assert result is not None
        assert result.category == Category.UNKNOWN
        assert 'youtube_browsing_allow' in result.metadata['rules_applied']
    
    @pytest.mark.asyncio
    async def test_classify_with_channel_context(self, classifier):
        """Test classification with channel information in context."""
        domain = Domain("youtube.com")
        
        # Educational channel
        context = {
            "url": "https://youtube.com/watch?v=abc123",
            "title": "Video Title",
            "channel": "MIT OpenCourseWare"
        }
        result = await classifier.classify(domain, context)
        assert result is not None
        assert result.category == Category.EDUCATION
        
        # Entertainment channel
        context = {
            "url": "https://youtube.com/watch?v=abc123",
            "title": "Video Title",
            "channel": "Netflix"
        }
        result = await classifier.classify(domain, context)
        assert result is not None
        assert result.category == Category.ENTERTAINMENT
    
    @pytest.mark.asyncio
    async def test_metadata_in_classification_result(self, classifier):
        """Test that metadata is included in classification result."""
        domain = Domain("youtube.com")
        context = {
            "url": "https://youtube.com/watch?v=abc123",
            "title": "Learn Python Programming"
        }
        
        result = await classifier.classify(domain, context)
        
        assert result is not None
        assert result.metadata is not None
        assert "rules_applied" in result.metadata
        assert "method" in result.metadata
    
    @pytest.mark.asyncio
    async def test_custom_rules_registration(self):
        """Test registration of custom rules."""
        # Create a classifier with custom rules
        async def custom_rule(context):
            return Category.SOCIAL_MEDIA if "social" in context.get("title", "").lower() else None
        
        classifier = RuleBasedYouTubeClassifier()
        classifier.register_rule("social_rule", custom_rule, 150)
        
        # Test the custom rule
        domain = Domain("youtube.com")
        context = {
            "url": "https://youtube.com/watch?v=abc123",
            "title": "Social Media Tips"
        }
        
        result = await classifier.classify(domain, context)
        
        assert result is not None
        assert result.category == Category.SOCIAL_MEDIA
        assert result.metadata["rule"] == "social_rule"


# Only run LLM tests if dependencies are available
if HAS_LLM:
    class TestLLMBasedYouTubeClassifier:
        """Tests for the LLMBasedYouTubeClassifier class."""
        
        @pytest.fixture
        def classifier(self):
            """Create a test instance of LLMBasedYouTubeClassifier."""
            from focus_guard.core.classification.classifiers.domains.youtube_llm import LLMBasedYouTubeClassifier
            mock_llm_client = MagicMock()
            return LLMBasedYouTubeClassifier(llm_client=mock_llm_client)
        
        @pytest.mark.asyncio
        async def test_classify_uses_llm(self, classifier):
            """Test that classify() uses the LLM for classification."""
            domain = Domain("youtube.com")
            context = {
                "url": "https://youtube.com/watch?v=test123",
                "title": "Test Video",
                "description": "This is a test video description"
            }
    
            # Create a mock LLM response
            mock_llm_response = json.dumps({
                "category": "EDUCATION",
                "confidence": 0.9,
                "reason": "The content appears to be educational",
                "is_distracting": False,
                "content_type": "video"
            })
            
            # Create an async mock for the generate method
            async def mock_generate(prompt, system_prompt=None, **kwargs):
                return mock_llm_response
            
            # Patch the LLM client's generate method
            with patch.object(classifier.llm_client, 'generate', new=mock_generate):
                # Call the method under test
                result = await classifier.classify(domain, context)
                
                # Verify the result
                assert result is not None
                assert result.category == Category.EDUCATION
                assert result.confidence == 0.9
                assert result.metadata["reason"] == "The content appears to be educational"
                assert result.metadata["is_distracting"] is False
                assert result.metadata["content_type"] == "video"


class TestModuleFunctions:
    """Tests for module-level functions in youtube.py."""
    
    def test_create_youtube_classifier_defaults(self):
        """Test create_youtube_classifier with default arguments."""
        # Skip this test if LLM dependencies are not available
        if not HAS_LLM:
            pytest.skip("LLM dependencies not available")
            
        # Import the real LLMBasedYouTubeClassifier for isinstance check
        from focus_guard.core.classification.classifiers.domains.youtube_llm import LLMBasedYouTubeClassifier
        
        # Create a mock LLM client
        mock_llm_instance = MagicMock()
        
        # Create the classifier with explicit parameters
        classifier = create_youtube_classifier(
            use_llm=True,
            use_rules=True,
            llm_client=mock_llm_instance
        )
        
        assert isinstance(classifier, YouTubeClassifier)
        
        # Should have both rule-based and LLM classifiers
        rule_based = [c for c in classifier.classifiers 
                     if isinstance(c, RuleBasedYouTubeClassifier)]
        llm_based = [c for c in classifier.classifiers 
                    if isinstance(c, LLMBasedYouTubeClassifier)]
        
        assert len(rule_based) > 0, "Should have at least the rule-based classifier"
        assert len(llm_based) > 0, "Should have the LLM classifier when llm_client is provided"
        
        # Test with use_llm=False
        classifier = create_youtube_classifier(use_llm=False, use_rules=True)
        rule_based = [c for c in classifier.classifiers 
                     if isinstance(c, RuleBasedYouTubeClassifier)]
        llm_based = [c for c in classifier.classifiers 
                    if isinstance(c, LLMBasedYouTubeClassifier)]
        
        assert len(rule_based) > 0, "Should have the rule-based classifier"
        assert len(llm_based) == 0, "Should not have LLM classifier when use_llm=False"
    
    def test_create_youtube_classifier_rules_only(self):
        """Test create_youtube_classifier with only rules."""
        classifier = create_youtube_classifier(use_llm=False, use_rules=True)
        assert isinstance(classifier, YouTubeClassifier)
        assert all(isinstance(c, RuleBasedYouTubeClassifier)
                  for c in classifier.classifiers)
    
    def test_default_classifier_instance(self):
        """Test that default_classifier is a valid instance."""
        assert isinstance(default_classifier, YouTubeClassifier)
