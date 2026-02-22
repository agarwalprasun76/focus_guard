"""
Tests for Google Search classifier.

Tests both rule-based and LLM-based classification of Google searches,
with focus on PDF/book detection and educational vs entertainment distinction.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from focus_guard.core.domain.models import Domain, Category
from focus_guard.core.classification.classifiers.domains.google_rules import (
    RuleBasedGoogleClassifier,
    create_google_rules_classifier,
)
from focus_guard.core.classification.classifiers.domains.google import (
    GoogleClassifier,
    create_google_classifier,
)


class TestRuleBasedGoogleClassifier:
    """Tests for rule-based Google classifier."""
    
    @pytest.fixture
    def classifier(self):
        return RuleBasedGoogleClassifier()
    
    @pytest.mark.asyncio
    async def test_non_google_domain_returns_none(self, classifier):
        """Non-Google domains should return None."""
        domain = Domain("youtube.com")
        result = await classifier.classify(domain, {"url": "https://youtube.com"})
        assert result is None
    
    @pytest.mark.asyncio
    async def test_google_scholar_is_education(self, classifier):
        """Google Scholar searches should be classified as education."""
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://scholar.google.com/scholar?q=machine+learning",
            "title": "Google Scholar"
        })
        assert result is not None
        assert result.category == Category.EDUCATION
        assert result.metadata.get("result_type") == "scholar"
    
    @pytest.mark.asyncio
    async def test_educational_search_query(self, classifier):
        """Educational search queries should be classified correctly."""
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://www.google.com/search?q=python+tutorial+for+beginners",
            "title": "python tutorial for beginners - Google Search"
        })
        assert result is not None
        assert result.category == Category.EDUCATION
        assert "tutorial" in result.metadata.get("reason", "").lower()
    
    @pytest.mark.asyncio
    async def test_entertainment_search_query(self, classifier):
        """Entertainment search queries should be classified correctly."""
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://www.google.com/search?q=funny+cat+memes",
            "title": "funny cat memes - Google Search"
        })
        assert result is not None
        assert result.category == Category.ENTERTAINMENT
    
    @pytest.mark.asyncio
    async def test_gaming_search_query(self, classifier):
        """Gaming search queries should be classified correctly."""
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://www.google.com/search?q=fortnite+gameplay+tips",
            "title": "fortnite gameplay tips - Google Search"
        })
        assert result is not None
        assert result.category == Category.ENTERTAINMENT  # Gaming keywords map to entertainment
    
    @pytest.mark.asyncio
    async def test_shopping_search(self, classifier):
        """Shopping searches should be classified correctly."""
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://www.google.com/search?q=best+laptop+2024&tbm=shop",
            "title": "best laptop 2024 - Google Shopping"
        })
        assert result is not None
        assert result.category == Category.SHOPPING
    
    @pytest.mark.asyncio
    async def test_pdf_educational_content(self, classifier):
        """Educational PDF links should be classified as education."""
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://www.google.com/search?q=calculus+textbook+pdf",
            "title": "[PDF] Calculus Textbook - Free Download"
        })
        assert result is not None
        assert result.category == Category.EDUCATION
        assert result.metadata.get("is_pdf") == True
    
    @pytest.mark.asyncio
    async def test_pdf_fiction_novel(self, classifier):
        """Fiction novel PDF searches should be classified as entertainment."""
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://www.google.com/search?q=harry+potter+novel+pdf+free",
            "title": "harry potter novel pdf free - Google Search"
        })
        assert result is not None
        assert result.category == Category.ENTERTAINMENT
        assert result.metadata.get("usefulness") == "DISTRACTION"
    
    @pytest.mark.asyncio
    async def test_google_docs_is_productivity(self, classifier):
        """Google Docs should be classified as productivity."""
        domain = Domain("docs.google.com")
        result = await classifier.classify(domain, {
            "url": "https://docs.google.com/document/d/abc123",
            "title": "My Document - Google Docs"
        })
        assert result is not None
        assert result.category == Category.PRODUCTIVITY
    
    @pytest.mark.asyncio
    async def test_google_drive_is_productivity(self, classifier):
        """Google Drive should be classified as productivity."""
        domain = Domain("drive.google.com")
        result = await classifier.classify(domain, {
            "url": "https://drive.google.com/drive/my-drive",
            "title": "My Drive - Google Drive"
        })
        assert result is not None
        assert result.category == Category.PRODUCTIVITY
    
    @pytest.mark.asyncio
    async def test_image_search_is_entertainment(self, classifier):
        """Image searches default to entertainment."""
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://www.google.com/search?q=cute+puppies&tbm=isch",
            "title": "cute puppies - Google Images"
        })
        assert result is not None
        assert result.category == Category.ENTERTAINMENT


class TestGoogleClassifier:
    """Tests for composite Google classifier."""
    
    @pytest.mark.asyncio
    async def test_classifier_creation(self):
        """Test that classifier can be created."""
        classifier = create_google_classifier(use_llm=False)
        assert classifier is not None
        assert classifier.name == "google_composite"
    
    @pytest.mark.asyncio
    async def test_rules_only_mode(self):
        """Test rules-only mode works."""
        classifier = GoogleClassifier.create_rules_only()
        
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://www.google.com/search?q=python+tutorial",
            "title": "python tutorial - Google Search"
        })
        
        assert result is not None
        assert result.category == Category.EDUCATION
    
    @pytest.mark.asyncio
    async def test_non_google_domain_returns_none(self):
        """Non-Google domains should return None."""
        classifier = create_google_classifier(use_llm=False)
        
        domain = Domain("facebook.com")
        result = await classifier.classify(domain, {
            "url": "https://facebook.com"
        })
        
        assert result is None


class TestGooglePDFClassification:
    """Specific tests for PDF/book classification."""
    
    @pytest.fixture
    def classifier(self):
        return RuleBasedGoogleClassifier()
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_category,description", [
        ("calculus textbook pdf", Category.EDUCATION, "Academic textbook"),
        ("physics lecture notes pdf", Category.EDUCATION, "Lecture notes"),
        ("research paper machine learning pdf", Category.EDUCATION, "Research paper"),
        ("harry potter pdf free download", Category.ENTERTAINMENT, "Fiction novel"),
        ("twilight novel pdf", Category.ENTERTAINMENT, "Romance novel"),
        ("manga one piece pdf", Category.ENTERTAINMENT, "Manga/comic"),
        ("python programming guide pdf", Category.EDUCATION, "Programming guide"),
        ("fantasy novel pdf free", Category.ENTERTAINMENT, "Fantasy fiction"),
    ])
    async def test_pdf_classification(self, classifier, query, expected_category, description):
        """Test various PDF search classifications."""
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": f"https://www.google.com/search?q={query.replace(' ', '+')}",
            "title": f"{query} - Google Search"
        })
        
        assert result is not None, f"Failed for: {description}"
        assert result.category == expected_category, f"Wrong category for {description}: expected {expected_category}, got {result.category}"


# Integration test with real LLM (marked to skip by default)
@pytest.mark.skip(reason="Requires API key and makes real API calls")
class TestGoogleLLMIntegration:
    """Integration tests with real LLM."""
    
    @pytest.mark.asyncio
    async def test_llm_classification(self):
        """Test LLM-based classification."""
        classifier = create_google_classifier(use_llm=True)
        
        domain = Domain("google.com")
        result = await classifier.classify(domain, {
            "url": "https://www.google.com/search?q=harry+potter+pdf+free+download",
            "title": "harry potter pdf free download - Google Search"
        })
        
        assert result is not None
        # LLM should recognize this as entertainment/fiction
        assert result.category == Category.ENTERTAINMENT
