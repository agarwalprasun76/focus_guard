"""Tests for classification integration with override system.

Tests the new classification-aware budget system and screenshot service.
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from focus_guard.core.browser_v2.tab_server.domain_usage_tracker import (
    DomainUsageTracker,
    DomainRuleConfig,
    ClassificationBudget,
    DEFAULT_CLASSIFICATION_BUDGETS,
    reset_domain_usage_tracker,
)
from focus_guard.core.browser_v2.tab_server.classification_service import (
    ClassificationService,
    ClassificationResult,
    ContentUsefulness,
    get_classification_service,
    reset_classification_service,
)
from focus_guard.core.browser_v2.tab_server.classification_blocker import ClassificationBlocker
from focus_guard.core.domain.models import Classification, Domain, Category


class TestClassificationBudgets:
    """Test classification-aware budget system."""
    
    def setup_method(self):
        """Reset singletons before each test."""
        reset_domain_usage_tracker()
    
    def test_default_budgets_exist(self):
        """Verify default classification budgets are defined."""
        assert "EDUCATION:EDUCATIONAL" in DEFAULT_CLASSIFICATION_BUDGETS
        assert "ENTERTAINMENT:DISTRACTION" in DEFAULT_CLASSIFICATION_BUDGETS
        assert "GAMING:DISTRACTION" in DEFAULT_CLASSIFICATION_BUDGETS
        
        # Check educational budget is generous
        edu_budget = DEFAULT_CLASSIFICATION_BUDGETS["EDUCATION:EDUCATIONAL"]
        assert edu_budget.max_cumulative_time_seconds == 3600  # 60 min
        assert edu_budget.require_screenshot is False
        
        # Check distraction budget is strict
        dist_budget = DEFAULT_CLASSIFICATION_BUDGETS["ENTERTAINMENT:DISTRACTION"]
        assert dist_budget.max_cumulative_time_seconds == 600  # 10 min
        assert dist_budget.require_screenshot is True
        assert dist_budget.notify_parent is True
    
    def test_rule_config_get_budget_for_classification(self):
        """Test getting budget based on classification."""
        rule = DomainRuleConfig(domain="youtube.com")
        
        # Educational content should get generous budget
        edu_budget = rule.get_budget_for_classification("EDUCATION", "EDUCATIONAL")
        assert edu_budget.max_cumulative_time_seconds == 3600
        assert edu_budget.penalty_per_extra_override_seconds == 0
        
        # Distracting content should get strict budget
        dist_budget = rule.get_budget_for_classification("ENTERTAINMENT", "DISTRACTION")
        assert dist_budget.max_cumulative_time_seconds == 600
        assert dist_budget.require_screenshot is True
        
        # Unknown content should fall back to domain defaults
        unknown_budget = rule.get_budget_for_classification("UNKNOWN", "UNKNOWN")
        assert unknown_budget.max_cumulative_time_seconds == rule.max_cumulative_time_seconds
    
    def test_tracker_check_with_classification(self):
        """Test DomainUsageTracker.check_can_override_with_classification."""
        tracker = DomainUsageTracker()
        
        # Educational content should have generous limits
        result = tracker.check_can_override_with_classification(
            domain="youtube.com",
            category="EDUCATION",
            usefulness="EDUCATIONAL",
        )
        assert result["can_override"] is True
        assert result["time_budget"] == 3600  # 60 min
        assert result["require_screenshot"] is False
        
        # Distracting content should have strict limits
        result = tracker.check_can_override_with_classification(
            domain="youtube.com",
            category="ENTERTAINMENT",
            usefulness="DISTRACTION",
        )
        assert result["can_override"] is True
        assert result["time_budget"] == 600  # 10 min
        assert result["require_screenshot"] is True
        assert result["notify_parent"] is True
    
    def test_budget_exhaustion_with_classification(self):
        """Test that budget exhaustion respects classification."""
        tracker = DomainUsageTracker()
        
        # Simulate using 5 minutes on youtube
        tracker.start_session("youtube.com", "tab1", "override1")
        tracker._active_sessions["youtube.com"].active_seconds = 300  # 5 min
        
        # Educational content should still have budget (60 min total)
        result = tracker.check_can_override_with_classification(
            domain="youtube.com",
            category="EDUCATION",
            usefulness="EDUCATIONAL",
        )
        assert result["can_override"] is True
        assert result["remaining_time_seconds"] > 3000  # > 50 min remaining
        
        # Simulate using 10 minutes total
        tracker._active_sessions["youtube.com"].active_seconds = 600  # 10 min
        
        # Distracting content should be exhausted (10 min total)
        result = tracker.check_can_override_with_classification(
            domain="youtube.com",
            category="ENTERTAINMENT",
            usefulness="DISTRACTION",
        )
        assert result["can_override"] is False
        assert "exhausted" in result["reason"].lower()


class TestClassificationService:
    """Test the classification service."""
    
    def setup_method(self):
        """Reset singletons before each test."""
        reset_classification_service()
    
    def test_service_creation(self):
        """Test classification service can be created."""
        service = ClassificationService()
        assert service is not None
        assert service.prefer_llm is True
    
    def test_fallback_result(self):
        """Test fallback classification when classifiers unavailable."""
        service = ClassificationService()
        result = service._create_fallback_result(
            domain="example.com",
            url="https://example.com/page",
            context={},
        )
        
        assert result.domain == "example.com"
        assert result.category == "UNKNOWN"
        assert result.usefulness == ContentUsefulness.NEUTRAL
        assert result.classifier_used == "fallback"
        assert result.is_distracting is False
    
    def test_usefulness_inference(self):
        """Test inferring usefulness from category."""
        service = ClassificationService()
        
        assert service._infer_usefulness_from_category("EDUCATION") == ContentUsefulness.EDUCATIONAL
        assert service._infer_usefulness_from_category("ENTERTAINMENT") == ContentUsefulness.DISTRACTION
        assert service._infer_usefulness_from_category("GAMING") == ContentUsefulness.DISTRACTION
        assert service._infer_usefulness_from_category("PRODUCTIVITY") == ContentUsefulness.EDUCATIONAL
        assert service._infer_usefulness_from_category("UNKNOWN") == ContentUsefulness.NEUTRAL
    
    def test_cache_key_generation(self):
        """Test cache key generation for different domains."""
        service = ClassificationService()
        
        # YouTube with video_id
        key1 = service._get_cache_key(
            "youtube.com",
            "https://youtube.com/watch?v=abc123",
            {"video_id": "abc123"}
        )
        assert "youtube:video:abc123" == key1
        
        # YouTube without video_id
        key2 = service._get_cache_key(
            "youtube.com",
            "https://youtube.com/watch?v=xyz",
            {}
        )
        assert "youtube:url:" in key2
        
        # Non-YouTube domain
        key3 = service._get_cache_key(
            "reddit.com",
            "https://reddit.com/r/programming",
            {}
        )
        assert "domain:reddit.com" in key3
    
    @pytest.mark.asyncio
    async def test_classify_async_fallback(self):
        """Test async classification falls back gracefully."""
        service = ClassificationService()
        
        # This should fall back to fallback result since no classifiers loaded
        result = await service.classify_async(
            domain="unknown-domain.com",
            url="https://unknown-domain.com/page",
            context={"title": "Some Page"},
        )
        
        assert result is not None
        assert result.domain == "unknown-domain.com"
        # Should either be classified or fall back
        assert result.category in ["UNKNOWN", "EDUCATION", "ENTERTAINMENT", "PRODUCTIVITY"]

    @pytest.mark.asyncio
    async def test_generic_classification_preserves_classifier_provenance(self):
        """Generic path should expose which classifier actually produced the result."""
        service = ClassificationService()

        class _FakeGenericClassifier:
            async def classify(self, domain: Domain, context):
                return Classification(
                    domain=domain,
                    category=Category.EDUCATION,
                    confidence=0.68,
                    metadata={
                        "classifier": "generic_url_llm",
                        "reason": "LLM inferred educational context from metadata",
                    },
                )

        service._domain_classifier = _FakeGenericClassifier()

        result = await service.classify_async(
            domain="folger.edu",
            url="https://folger.edu/explore/shakespeares-works/macbeth/",
            context={"title": "Macbeth Study Guide"},
        )

        assert result is not None
        assert result.classifier_used == "generic_url_llm"
        assert "LLM inferred educational context" in result.reason


class TestClassificationResult:
    """Test ClassificationResult dataclass."""
    
    def test_budget_key(self):
        """Test budget key generation."""
        result = ClassificationResult(
            domain="youtube.com",
            url="https://youtube.com/watch?v=abc",
            category="EDUCATION",
            usefulness=ContentUsefulness.EDUCATIONAL,
            confidence=0.9,
            reason="Tutorial video",
            classifier_used="llm",
            is_distracting=False,
        )
        
        assert result.budget_key == "EDUCATION:EDUCATIONAL"
    
    def test_to_dict(self):
        """Test serialization to dict."""
        result = ClassificationResult(
            domain="youtube.com",
            url="https://youtube.com/watch?v=abc",
            category="ENTERTAINMENT",
            usefulness=ContentUsefulness.DISTRACTION,
            confidence=0.8,
            reason="Gaming video",
            classifier_used="rules",
            is_distracting=True,
            content_type="video",
        )
        
        d = result.to_dict()
        assert d["domain"] == "youtube.com"
        assert d["category"] == "ENTERTAINMENT"
        assert d["usefulness"] == "distraction"
        assert d["is_distracting"] is True
        assert d["classifier_used"] == "rules"


class TestBudgetStatusForClassification:
    """Test get_budget_status_for_classification method."""
    
    def setup_method(self):
        """Reset singletons before each test."""
        reset_domain_usage_tracker()
    
    def test_budget_status_returns_all_fields(self):
        """Test that budget status returns all expected fields."""
        reset_domain_usage_tracker()  # Extra reset to ensure clean state
        tracker = DomainUsageTracker()
        
        result = tracker.get_budget_status_for_classification(
            domain="test-domain-fields.com",  # Use unique domain
            category="ENTERTAINMENT",
            usefulness="DISTRACTION",
        )
        
        # Check all expected fields are present
        assert "time_used_seconds" in result
        assert "time_budget_seconds" in result
        assert "remaining_seconds" in result
        assert "time_used_formatted" in result
        assert "time_budget_formatted" in result
        assert "remaining_formatted" in result
        assert "percentage_used" in result
        assert "override_count" in result
        assert "max_overrides" in result
        assert "remaining_overrides" in result
        assert "classification" in result
        assert "budget_exhausted" in result
    
    def test_budget_status_for_educational_content(self):
        """Test budget status for educational content shows generous limits."""
        reset_domain_usage_tracker()  # Extra reset to ensure clean state
        tracker = DomainUsageTracker()
        
        result = tracker.get_budget_status_for_classification(
            domain="test-edu.com",  # Use unique domain
            category="EDUCATION",
            usefulness="EDUCATIONAL",
        )
        
        # Educational content should have 60 min budget
        assert result["time_budget_seconds"] == 3600
        assert result["remaining_seconds"] == 3600  # No usage yet
        assert result["percentage_used"] == 0.0
        assert result["budget_exhausted"] is False
    
    def test_budget_status_for_distracting_content(self):
        """Test budget status for distracting content shows strict limits."""
        reset_domain_usage_tracker()  # Extra reset to ensure clean state
        tracker = DomainUsageTracker()
        
        result = tracker.get_budget_status_for_classification(
            domain="test-distract.com",  # Use unique domain
            category="ENTERTAINMENT",
            usefulness="DISTRACTION",
        )
        
        # Distracting content should have 10 min budget
        assert result["time_budget_seconds"] == 600
        assert result["remaining_seconds"] == 600  # No usage yet
        assert result["percentage_used"] == 0.0
        assert result["budget_exhausted"] is False
    
    def test_budget_status_with_usage(self):
        """Test budget status reflects actual usage."""
        reset_domain_usage_tracker()  # Extra reset to ensure clean state
        tracker = DomainUsageTracker()
        
        # Simulate 5 minutes of usage on a unique domain
        tracker.start_session("test-usage.com", "tab1", "override1")
        tracker._active_sessions["test-usage.com"].active_seconds = 300  # 5 min
        
        result = tracker.get_budget_status_for_classification(
            domain="test-usage.com",
            category="ENTERTAINMENT",
            usefulness="DISTRACTION",
        )
        
        # Should show 5 min used of 10 min budget
        assert result["time_used_seconds"] == 300
        assert result["remaining_seconds"] == 300  # 5 min remaining
        assert result["percentage_used"] == 50.0
        assert result["budget_exhausted"] is False
    
    def test_budget_status_exhausted(self):
        """Test budget status shows exhausted when budget is used up."""
        reset_domain_usage_tracker()  # Extra reset to ensure clean state
        tracker = DomainUsageTracker()
        
        # Simulate 10 minutes of usage (full budget for distraction)
        tracker.start_session("test-exhausted.com", "tab1", "override1")
        tracker._active_sessions["test-exhausted.com"].active_seconds = 600  # 10 min
        
        result = tracker.get_budget_status_for_classification(
            domain="test-exhausted.com",
            category="ENTERTAINMENT",
            usefulness="DISTRACTION",
        )
        
        assert result["remaining_seconds"] == 0
        assert result["percentage_used"] == 100.0
        assert result["budget_exhausted"] is True


class TestBlockingDecisionToDict:
    """Test BlockingDecision.to_dict() method."""
    
    def test_basic_decision_to_dict(self):
        """Test basic blocking decision serialization."""
        from focus_guard.core.browser_v2.tab_server.blocking import BlockingDecision
        
        decision = BlockingDecision(
            should_block=True,
            reason="Category ENTERTAINMENT is blocked",
        )
        
        result = decision.to_dict()
        assert result["should_block"] is True
        assert result["reason"] == "Category ENTERTAINMENT is blocked"
        assert result["cached"] is False
    
    def test_decision_with_classification(self):
        """Test blocking decision with classification info."""
        from focus_guard.core.browser_v2.tab_server.blocking import BlockingDecision, BlockingRule
        
        decision = BlockingDecision(
            should_block=True,
            reason="Content classified as distracting",
            rule=BlockingRule(
                domain="youtube.com",
                reason="Content classified as distracting",
                category="ENTERTAINMENT",
            ),
            classification={
                "category": "ENTERTAINMENT",
                "usefulness": "DISTRACTION",
                "confidence": 0.9,
                "reason": "Gaming video detected",
                "classifier_used": "rules",
            },
        )
        
        result = decision.to_dict()
        assert result["should_block"] is True
        assert "classification" in result
        assert result["classification"]["category"] == "ENTERTAINMENT"
        assert result["classification"]["usefulness"] == "DISTRACTION"
        assert "rule" in result
        assert result["rule"]["category"] == "ENTERTAINMENT"
    
    def test_decision_with_budget_status(self):
        """Test blocking decision with budget status."""
        from focus_guard.core.browser_v2.tab_server.blocking import BlockingDecision
        
        decision = BlockingDecision(
            should_block=True,
            reason="Budget exhausted",
            classification={
                "category": "ENTERTAINMENT",
                "usefulness": "DISTRACTION",
            },
            budget_status={
                "time_used_seconds": 600,
                "time_budget_seconds": 600,
                "remaining_seconds": 0,
                "time_used_formatted": "10m 0s",
                "time_budget_formatted": "10m 0s",
                "remaining_formatted": "0s",
                "percentage_used": 100.0,
                "budget_exhausted": True,
            },
        )
        
        result = decision.to_dict()
        assert "budget_status" in result
        assert result["budget_status"]["time_used_formatted"] == "10m 0s"
        assert result["budget_status"]["budget_exhausted"] is True
    
    def test_non_blocking_decision_with_classification(self):
        """Test non-blocking decision still includes classification."""
        from focus_guard.core.browser_v2.tab_server.blocking import BlockingDecision
        
        decision = BlockingDecision(
            should_block=False,
            classification={
                "category": "EDUCATION",
                "usefulness": "EDUCATIONAL",
                "confidence": 0.95,
            },
            budget_status={
                "time_used_seconds": 300,
                "time_budget_seconds": 3600,
                "remaining_seconds": 3300,
            },
        )
        
        result = decision.to_dict()
        assert result["should_block"] is False
        assert "classification" in result
        assert result["classification"]["category"] == "EDUCATION"
        assert "budget_status" in result


class TestClassificationBlockerMetadataAndReasons:
    """Regression tests for classification blocker decision transparency and context wiring."""

    def test_check_blocking_includes_decision_source_and_basis(self):
        blocker = ClassificationBlocker(
            blocked_categories={"SOCIAL_MEDIA"},
            block_distracting=True,
            log_activity=False,
        )

        class _FakeService:
            async def classify_async(self, domain, url, context):
                return ClassificationResult(
                    domain=domain,
                    url=url,
                    category="SOCIAL_MEDIA",
                    usefulness=ContentUsefulness.DISTRACTION,
                    confidence=0.91,
                    reason="Detected social feed pattern",
                    classifier_used="generic_url_rules",
                    is_distracting=True,
                )

        blocker._classification_service = _FakeService()

        decision = blocker.check_blocking(
            url="https://example-social.com/feed",
            domain="example-social.com",
            title="My feed",
            tab_id=101,
        )

        assert decision.should_block is True
        assert decision.classification is not None
        assert decision.classification["decision_source"] == "rule"
        assert decision.classification["block_basis"] == "distracting_content"

    def test_check_blocking_forwards_search_context_and_tab_metadata(self):
        blocker = ClassificationBlocker(
            blocked_categories={"SOCIAL_MEDIA"},
            block_distracting=True,
            log_activity=False,
        )

        class _FakeService:
            captured_context = None

            async def classify_async(self, domain, url, context):
                self.captured_context = dict(context)
                return ClassificationResult(
                    domain=domain,
                    url=url,
                    category="EDUCATION",
                    usefulness=ContentUsefulness.EDUCATIONAL,
                    confidence=0.88,
                    reason="Educational reading page",
                    classifier_used="generic_url_llm",
                    is_distracting=False,
                )

        class _FakeTracker:
            def check_should_block_file_sharing(self, url, domain, title="", tab_id=None):
                return {
                    "should_block": False,
                    "search_context": {"query": "macbeth analysis", "tab_id": tab_id},
                    "matched_keywords": ["macbeth"],
                }

        fake_service = _FakeService()
        blocker._classification_service = fake_service

        with patch(
            "focus_guard.core.browser_v2.tab_server.search_context_tracker.get_search_context_tracker",
            return_value=_FakeTracker(),
        ):
            decision = blocker.check_blocking(
                url="https://folger.edu/explore/shakespeares-works/macbeth/",
                domain="folger.edu",
                title="Macbeth | Folger",
                tab_id=42,
            )

        assert decision.should_block is False
        assert decision.classification is not None
        assert decision.classification["decision_source"] == "llm"
        assert fake_service.captured_context is not None
        assert fake_service.captured_context["tab_id"] == 42
        assert fake_service.captured_context["search_context"]["query"] == "macbeth analysis"
        assert fake_service.captured_context["search_matched_keywords"] == ["macbeth"]

    def test_low_confidence_rule_result_escalates_to_llm(self):
        blocker = ClassificationBlocker(
            blocked_categories={"SOCIAL_MEDIA"},
            block_distracting=True,
            log_activity=False,
            low_confidence_threshold=0.6,
            escalate_uncertain_to_llm=True,
            uncertain_policy="allow",
        )

        class _EscalatingService:
            def __init__(self):
                self.calls = []

            async def classify_async(self, domain, url, context):
                self.calls.append(dict(context))
                if context.get("force_llm"):
                    return ClassificationResult(
                        domain=domain,
                        url=url,
                        category="EDUCATION",
                        usefulness=ContentUsefulness.EDUCATIONAL,
                        confidence=0.92,
                        reason="LLM detected educational context",
                        classifier_used="generic_url_llm",
                        is_distracting=False,
                    )
                return ClassificationResult(
                    domain=domain,
                    url=url,
                    category="SOCIAL_MEDIA",
                    usefulness=ContentUsefulness.DISTRACTION,
                    confidence=0.41,
                    reason="Low-confidence rules classification",
                    classifier_used="generic_url_rules",
                    is_distracting=True,
                )

        service = _EscalatingService()
        blocker._classification_service = service

        decision = blocker.check_blocking(
            url="https://folger.edu/explore/shakespeares-works/macbeth/",
            domain="folger.edu",
            title="Macbeth | Folger",
            tab_id=77,
        )

        assert decision.should_block is False
        assert decision.classification is not None
        assert decision.classification["decision_source"] == "llm"
        assert decision.classification["llm_escalation_attempted"] is True
        assert decision.classification["llm_escalation_applied"] is True
        assert any(call.get("force_llm") is True for call in service.calls)

    def test_low_confidence_allows_when_uncertain_policy_allow(self):
        blocker = ClassificationBlocker(
            blocked_categories={"SOCIAL_MEDIA"},
            block_distracting=True,
            log_activity=False,
            low_confidence_threshold=0.7,
            escalate_uncertain_to_llm=False,
            uncertain_policy="allow",
        )

        class _LowConfidenceService:
            async def classify_async(self, domain, url, context):
                return ClassificationResult(
                    domain=domain,
                    url=url,
                    category="SOCIAL_MEDIA",
                    usefulness=ContentUsefulness.DISTRACTION,
                    confidence=0.5,
                    reason="Ambiguous social/media signal",
                    classifier_used="generic_url_rules",
                    is_distracting=True,
                )

        blocker._classification_service = _LowConfidenceService()

        decision = blocker.check_blocking(
            url="https://ambiguous.example/social-learning",
            domain="ambiguous.example",
            title="Social learning discussion",
            tab_id=12,
        )

        assert decision.should_block is False
        assert decision.classification is not None
        assert decision.classification["is_uncertain"] is True
        assert decision.classification["uncertain_policy"] == "allow"
        assert decision.classification["block_basis"] == "uncertain_low_confidence_allow"


class TestOverrideManagerWithClassification:
    """Test OverrideManager with classification integration."""
    
    def setup_method(self):
        """Reset singletons before each test."""
        reset_domain_usage_tracker()
        reset_classification_service()
        from focus_guard.core.browser_v2.tab_server.override_manager import reset_override_manager
        reset_override_manager()
    
    def test_request_override_with_classification_educational(self):
        """Test override request for educational content gets generous budget."""
        from focus_guard.core.browser_v2.tab_server.override_manager import OverrideManager
        
        manager = OverrideManager()
        
        # Request override with educational context
        result = manager.request_override_with_classification(
            domain="youtube.com",
            url="https://youtube.com/watch?v=abc123",
            block_reason="blocked_domain",
            browser="chrome",
            context={
                "title": "Python Tutorial for Beginners",
                "channel": "Programming with Mosh",
            },
        )
        
        assert result["granted"] is True
        assert "classification" in result
        # Should have classification info
        classification = result["classification"]
        assert "category" in classification
        assert "usefulness" in classification
    
    def test_request_override_with_classification_distracting(self):
        """Test override request for distracting content gets strict budget."""
        from focus_guard.core.browser_v2.tab_server.override_manager import OverrideManager
        
        manager = OverrideManager()
        
        # First, simulate some usage to approach the limit
        tracker = DomainUsageTracker()
        tracker.start_session("youtube.com", "tab1", "override1")
        tracker._active_sessions["youtube.com"].active_seconds = 500  # 8+ min
        
        # Request override - should still work but with less remaining time
        result = manager.request_override_with_classification(
            domain="youtube.com",
            url="https://youtube.com/watch?v=gaming123",
            block_reason="blocked_domain",
            browser="chrome",
            context={
                "title": "Epic Gaming Montage",
                "channel": "GamerBros",
            },
        )
        
        # Should be granted (still under budget for most categories)
        assert result["granted"] is True
        assert "classification" in result
    
    def test_request_override_with_classification_returns_budget_info(self):
        """Test that classification-aware override returns budget information."""
        from focus_guard.core.browser_v2.tab_server.override_manager import OverrideManager
        
        manager = OverrideManager()
        
        result = manager.request_override_with_classification(
            domain="youtube.com",
            url="https://youtube.com/watch?v=test",
            block_reason="blocked_domain",
            browser="chrome",
            context={"title": "Test Video"},
        )
        
        assert result["granted"] is True
        # Should include budget info
        assert "remaining_time_seconds" in result
        assert "session_duration_seconds" in result
        assert "effective_time_used" in result
    
    def test_existing_override_returns_classification(self):
        """Test that accessing existing override still returns classification."""
        from focus_guard.core.browser_v2.tab_server.override_manager import OverrideManager
        
        manager = OverrideManager()
        
        # First request
        result1 = manager.request_override_with_classification(
            domain="youtube.com",
            url="https://youtube.com/watch?v=abc",
            block_reason="blocked_domain",
            browser="chrome",
            context={"title": "First Video"},
        )
        assert result1["granted"] is True
        
        # Second request for same domain - should return existing override
        result2 = manager.request_override_with_classification(
            domain="youtube.com",
            url="https://youtube.com/watch?v=xyz",
            block_reason="blocked_domain",
            browser="chrome",
            context={"title": "Second Video"},
        )
        
        assert result2["granted"] is True
        assert "classification" in result2
        # Should be the same override
        assert result2["override"]["id"] == result1["override"]["id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
