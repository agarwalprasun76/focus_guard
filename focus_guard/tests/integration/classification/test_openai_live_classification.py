"""
**Opt-in** live OpenAI classification tests (real API, costs money, non-deterministic).

Use alongside deterministic tests:

- Pipeline / enforcement contract (mocked classifier):
  ``focus_guard/tests/integration/tab_server/test_classification_enforcement_matrix.py``
- Service composites with injected mock LLM:
  ``focus_guard/tests/integration/classification/test_fr021_classification_service_matrix.py``

This module exercises ``ClassificationService.classify_async`` with **real**
Google + YouTube classifiers (rules + LLM as configured) so you can validate
end-user intelligence when keys are valid.

**Run (PowerShell)::

    $env:FOCUS_GUARD_RUN_OPENAI_INTEGRATION=1
    python -m pytest focus_guard/tests/integration/classification/test_openai_live_classification.py -v

Requires ``OPENAI_API_KEY`` or ``openai_api_key`` in
``%ProgramData%\\FocusGuard\\api_token.json`` (same resolution as ``OpenAIClient``).
If the key is invalid (401), the module **skips** after one preflight call so you
get a clear message instead of many red failures.

Assertions are **soft** because model output varies; rule-based fallbacks use
slightly different signals than the LLM (e.g. ``is_distracting`` on YouTube rules).
"""

from __future__ import annotations

import time
from typing import FrozenSet

import pytest

from focus_guard.core.browser_v2.tab_server.classification_service import ClassificationService
from focus_guard.tests.integration.classification.classification_case_library import (
    GOOGLE_CURATED_CASES,
    YOUTUBE_CURATED_CASES,
)
from focus_guard.tests.integration.classification.live_openai_config import (
    SKIP_OPENAI_LIVE,
    assert_openai_api_reachable,
    openai_live_configured,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.openai_live]


@pytest.fixture(scope="module", autouse=True)
def openai_live_api_preflight():
    """One cheap completion; skip whole module if the API key does not work."""
    if not openai_live_configured():
        return
    assert_openai_api_reachable()


@pytest.fixture(autouse=True)
def require_openai_live_and_credentials():
    """Skip each test unless opt-in env and OpenAI credentials are present."""
    if not openai_live_configured():
        pytest.skip(SKIP_OPENAI_LIVE)


@pytest.fixture(autouse=True)
def _clear_classification_memory_cache():
    """Avoid cross-test pollution of in-memory classification cache."""
    ClassificationService._cache.clear()
    ClassificationService._cache_timestamps.clear()
    yield
    ClassificationService._cache.clear()
    ClassificationService._cache_timestamps.clear()


@pytest.fixture
def classification_service() -> ClassificationService:
    return ClassificationService(prefer_llm=True, llm_timeout=60.0)


_PRODUCTIVE_BUCKET: FrozenSet[str] = frozenset({"EDUCATION", "PRODUCTIVITY", "NEWS"})
_DISTRACTION_BUCKET: FrozenSet[str] = frozenset(
    {"ENTERTAINMENT", "GAMING", "SOCIAL_MEDIA", "ADULT", "SHOPPING", "NEWS"}
)


def _url_with_nonce(url: str) -> str:
    nonce = time.time_ns()
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}live={nonce}"


@pytest.mark.parametrize("case", GOOGLE_CURATED_CASES, ids=[c["name"] for c in GOOGLE_CURATED_CASES])
async def test_live_google_curated_cases(classification_service: ClassificationService, case):
    """Run curated Google probes through live classifier stack (LLM + rules)."""
    url = _url_with_nonce(case["url"])
    ctx = {"url": url, "title": case["title"], "tab_id": 1}
    r = await classification_service.classify_async(case["domain"], url, ctx)
    assert r is not None
    assert r.confidence >= 0.0

    if case["expected_category"] in {"EDUCATION", "PRODUCTIVITY"}:
        assert r.category in _PRODUCTIVE_BUCKET, (
            f"{case['name']}: expected productive bucket; got {r.category!r} "
            f"reason={r.reason!r} classifier={r.classifier_used!r}"
        )
    else:
        assert r.category in _DISTRACTION_BUCKET, (
            f"{case['name']}: expected distraction/consumer bucket; got {r.category!r} "
            f"reason={r.reason!r} classifier={r.classifier_used!r}"
        )


@pytest.mark.parametrize("case", YOUTUBE_CURATED_CASES, ids=[c["name"] for c in YOUTUBE_CURATED_CASES])
async def test_live_youtube_curated_cases(classification_service: ClassificationService, case):
    """Run curated YouTube probes through live classifier stack (LLM + rules)."""
    url = _url_with_nonce(case["url"])
    ctx = {"url": url, "title": case["title"], "channel_title": "Curated Probe", "tab_id": 2}
    r = await classification_service.classify_async(case["domain"], url, ctx)
    assert r is not None

    if case["expected_category"] == "EDUCATION":
        assert r.is_distracting is False or r.category in _PRODUCTIVE_BUCKET, (
            f"{case['name']}: expected non-distracting/prod; got category={r.category!r} "
            f"is_distracting={r.is_distracting!r} reason={r.reason!r} classifier={r.classifier_used!r}"
        )
    else:
        assert r.category in _DISTRACTION_BUCKET or r.is_distracting is True, (
            f"{case['name']}: expected distraction-oriented result; got category={r.category!r} "
            f"is_distracting={r.is_distracting!r} reason={r.reason!r} classifier={r.classifier_used!r}"
        )
