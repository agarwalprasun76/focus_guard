"""Curated integration matrix for Google + YouTube classification.

Runs ClassificationService with rules-only classifiers to provide deterministic
coverage over the curated case library used for integration probing.
"""

from __future__ import annotations

import pytest

from focus_guard.core.browser_v2.tab_server.classification_service import ClassificationService
from focus_guard.core.classification.classifiers.domains.google import GoogleClassifier
from focus_guard.core.classification.classifiers.domains.youtube_base import YouTubeClassifier
from focus_guard.core.classification.classifiers.domains.youtube_rules import RuleBasedYouTubeClassifier
from focus_guard.tests.integration.classification.classification_case_library import (
    GOOGLE_CURATED_CASES,
    YOUTUBE_CURATED_CASES,
)


@pytest.fixture(autouse=True)
def clear_classification_service_memory_cache() -> None:
    ClassificationService._cache.clear()
    ClassificationService._cache_timestamps.clear()
    yield
    ClassificationService._cache.clear()
    ClassificationService._cache_timestamps.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("case", GOOGLE_CURATED_CASES, ids=[c["name"] for c in GOOGLE_CURATED_CASES])
async def test_google_curated_matrix_rules_only(case, monkeypatch) -> None:
    svc = ClassificationService(prefer_llm=False)
    monkeypatch.setattr(svc, "_get_google_classifier", lambda: GoogleClassifier.create_default(use_llm=False))

    result = await svc.classify_async(
        case["domain"],
        case["url"],
        {"url": case["url"], "title": case["title"], "tab_id": 1},
    )

    assert result is not None
    assert result.category == case["expected_category"]
    assert result.classifier_used == "google_rules"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", YOUTUBE_CURATED_CASES, ids=[c["name"] for c in YOUTUBE_CURATED_CASES])
async def test_youtube_curated_matrix_rules_only(case, monkeypatch) -> None:
    svc = ClassificationService(prefer_llm=False)
    monkeypatch.setattr(
        svc,
        "_get_youtube_classifier",
        lambda: YouTubeClassifier(classifiers=[RuleBasedYouTubeClassifier()]),
    )

    result = await svc.classify_async(
        case["domain"],
        case["url"],
        {"url": case["url"], "title": case["title"], "tab_id": 2},
    )

    assert result is not None
    expect = case.get("rules_expected_category") or case["expected_category"]
    assert result.category == expect
    assert result.classifier_used == "youtube_rule_based"
