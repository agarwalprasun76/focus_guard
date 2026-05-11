"""FR-021: ClassificationService matrix for Google + YouTube with mocked LLM.

Trace (extension → tab server → classifiers):

- Extension calls ``GET /api/should_block?url=...&domain=...&title=...&tabId=...&referrer=...``
  (see ``server._handle_should_block``).
- ``TabServerContext.check_blocking`` builds a classify context with at least
  ``url``, ``title``, ``tab_id``, and file-sharing / search fields when applicable
  (see ``blocking_steps``).
- ``ClassificationService.classify_async`` routes ``youtube.com`` / ``youtu.be``
  to ``_classify_youtube`` and ``google.com`` / ``google.co`` to ``_classify_google``,
  passing the context dict through to composite domain classifiers.

These tests pin composite + mock-LLM behavior without network or real OpenAI keys.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from focus_guard.core.browser_v2.tab_server.classification_service import ClassificationService
from focus_guard.core.classification.classifiers.domains.google import GoogleClassifier
from focus_guard.core.classification.classifiers.domains.google_llm import LLMBasedGoogleClassifier
from focus_guard.core.classification.classifiers.domains.google_rules import create_google_rules_classifier
from focus_guard.core.classification.classifiers.domains.youtube_base import YouTubeClassifier
from focus_guard.core.classification.classifiers.domains.youtube_llm import LLMBasedYouTubeClassifier
from focus_guard.core.classification.classifiers.domains.youtube_rules import RuleBasedYouTubeClassifier


@pytest.fixture(autouse=True)
def clear_classification_service_memory_cache() -> None:
    ClassificationService._cache.clear()
    ClassificationService._cache_timestamps.clear()
    yield
    ClassificationService._cache.clear()
    ClassificationService._cache_timestamps.clear()


def _google_llm_json(**overrides: object) -> str:
    base = {
        "category": "EDUCATION",
        "usefulness": "EDUCATIONAL",
        "confidence": 0.92,
        "reason": "Academic search",
        "is_pdf": False,
        "content_type": "search",
    }
    base.update(overrides)
    return json.dumps(base)


def _youtube_llm_json(**overrides: object) -> str:
    base = {
        "category": "EDUCATION",
        "usefulness": "EDUCATIONAL",
        "confidence": 0.88,
        "reason": "Tutorial video",
        "is_distracting": False,
        "content_type": "video",
    }
    base.update(overrides)
    return json.dumps(base)


@pytest.mark.asyncio
async def test_google_rich_context_uses_llm_classifier(monkeypatch) -> None:
    """title + q= in URL → mock LLM returns EDUCATION; classifier_used is google_llm."""
    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(
        return_value=_google_llm_json(),
    )
    composite = GoogleClassifier(
        classifiers=[
            LLMBasedGoogleClassifier(llm_client=mock_client),
            create_google_rules_classifier(),
        ],
    )
    svc = ClassificationService(prefer_llm=True)
    monkeypatch.setattr(svc, "_get_google_classifier", lambda: composite)

    url = "https://www.google.com/search?q=pytest+fixture+tutorial&fr021=llm1"
    ctx = {
        "url": url,
        "title": "pytest fixture tutorial - Google Search",
        "tab_id": 42,
    }
    result = await svc.classify_async("www.google.com", url, ctx)

    assert result.category == "EDUCATION"
    assert result.classifier_used == "google_llm"
    mock_client.generate.assert_awaited()
    call_kw = mock_client.generate.await_args
    assert call_kw is not None
    prompt = call_kw.kwargs.get("prompt") or (call_kw[1] or {}).get("prompt")
    assert "pytest" in (prompt or "").lower() or "tutorial" in (prompt or "").lower()


@pytest.mark.asyncio
async def test_google_llm_none_falls_back_to_rules(monkeypatch) -> None:
    """LLM returns None → composite uses google_rules for a known educational query."""
    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(return_value=None)
    composite = GoogleClassifier(
        classifiers=[
            LLMBasedGoogleClassifier(llm_client=mock_client),
            create_google_rules_classifier(),
        ],
    )
    svc = ClassificationService(prefer_llm=True)
    monkeypatch.setattr(svc, "_get_google_classifier", lambda: composite)

    url = "https://www.google.com/search?q=calculus+tutorial+homework&fr021=rules1"
    result = await svc.classify_async("www.google.com", url, {"url": url})

    assert result.classifier_used == "google_rules"
    assert result.category in ("EDUCATION", "UNKNOWN", "PRODUCTIVITY", "NEWS")


@pytest.mark.asyncio
async def test_youtube_llm_success_metadata(monkeypatch) -> None:
    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(return_value=_youtube_llm_json())
    composite = YouTubeClassifier(
        classifiers=[
            LLMBasedYouTubeClassifier(llm_client=mock_client),
            RuleBasedYouTubeClassifier(),
        ],
    )
    svc = ClassificationService(prefer_llm=True)
    monkeypatch.setattr(svc, "_get_youtube_classifier", lambda: composite)

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&fr021=yt1"
    ctx = {
        "url": url,
        "title": "Intro to linear algebra — full course",
        "channel_title": "Math Channel",
        "tab_id": 7,
    }
    result = await svc.classify_async("www.youtube.com", url, ctx)

    assert result.category == "EDUCATION"
    assert result.metadata.get("method") == "llm"
    mock_client.generate.assert_awaited()


@pytest.mark.asyncio
async def test_youtube_llm_none_uses_rule_classifier(monkeypatch) -> None:
    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(return_value=None)
    composite = YouTubeClassifier(
        classifiers=[
            LLMBasedYouTubeClassifier(llm_client=mock_client),
            RuleBasedYouTubeClassifier(),
        ],
    )
    svc = ClassificationService(prefer_llm=True)
    monkeypatch.setattr(svc, "_get_youtube_classifier", lambda: composite)

    url = "https://www.youtube.com/watch?v=abcd12345678&fr021=yt2"
    ctx = {"url": url, "title": "Fortnite season highlights gameplay"}
    result = await svc.classify_async("www.youtube.com", url, ctx)

    assert result.classifier_used == "youtube_rule_based"
