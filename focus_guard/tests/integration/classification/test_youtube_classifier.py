"""
YouTube LLM classifier integration: curated real URLs + optional metadata fetch.

Case list is **only** ``YOUTUBE_CURATED_CASES`` in
``classification_case_library.py`` (single source of truth; includes every URL
from the former script-style suite, plus Bach/classical, Python full course, and
the Minecraft shorts gameplay URL).

**Opt-in** (real OpenAI API; costs quota)::

    $env:FOCUS_GUARD_RUN_OPENAI_INTEGRATION=1
    python -m pytest focus_guard/tests/integration/classification/test_youtube_classifier.py -v
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pytest

from focus_guard.core.classification.classifiers.domains.youtube_llm import LLMBasedYouTubeClassifier
from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient
from focus_guard.core.domain.models import Domain
from focus_guard.core.utils.youtube_utils import extract_youtube_id
from focus_guard.tests.integration.classification.classification_case_library import YOUTUBE_CURATED_CASES
from focus_guard.tests.integration.classification.live_openai_config import (
    SKIP_OPENAI_LIVE,
    assert_openai_api_reachable,
    openai_live_configured,
)

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.asyncio, pytest.mark.openai_live]

_CLASS_FAMILY: dict[str, str] = {
    "ENTERTAINMENT": "ENTERTAINMENT",
    "GAMING": "ENTERTAINMENT",
    "SOCIAL_MEDIA": "ENTERTAINMENT",
    "EDUCATION": "EDUCATION",
    "PRODUCTIVITY": "EDUCATION",
    "NEWS": "INFORMATION",
    "SHOPPING": "CONSUMER",
    "ADULT": "RESTRICTED",
    "MALICIOUS": "RESTRICTED",
}


@pytest.fixture(scope="module", autouse=True)
def youtube_openai_preflight():
    if not openai_live_configured():
        return
    assert_openai_api_reachable()


@pytest.fixture(autouse=True)
def require_openai_opt_in():
    if not openai_live_configured():
        pytest.skip(SKIP_OPENAI_LIVE)


async def fetch_youtube_metadata(video_id: str) -> Optional[dict[str, Any]]:
    try:
        from focus_guard.core.utils.metadata_fetcher import metadata_fetcher

        metadata = metadata_fetcher.fetch_metadata_for_youtube(video_id)
        if metadata and "error" not in metadata:
            return metadata
        return None
    except Exception as exc:
        logger.warning("Failed to fetch metadata for %s: %s", video_id, exc)
        return None


def _category_name(classification) -> str:
    c = classification.category
    if hasattr(c, "name"):
        return str(c.name)
    return str(c).split(".")[-1].upper()


def _same_category_family(actual: str, expected: str) -> bool:
    return _CLASS_FAMILY.get(actual, actual) == _CLASS_FAMILY.get(expected, expected)


@pytest.mark.asyncio
async def test_youtube_llm_classifies_with_mock_context():
    """Smoke: LLM path with synthetic title/description (no metadata fetch)."""
    llm_client = OpenAIClient(model="gpt-4o-mini")
    classifier = LLMBasedYouTubeClassifier(llm_client=llm_client)
    domain = Domain("youtube.com")
    context = {
        "title": "Python Tutorial for Beginners",
        "channel_title": "Programming Academy",
        "description": "Learn Python programming from scratch",
    }
    result = await classifier.classify(domain, context)
    assert result is not None
    assert result.confidence >= 0.0


@pytest.mark.parametrize("case", YOUTUBE_CURATED_CASES, ids=[c["name"] for c in YOUTUBE_CURATED_CASES])
@pytest.mark.asyncio
async def test_youtube_llm_curated_real_urls_with_metadata(case):
    """For each curated URL: fetch metadata when possible, classify with LLM; expect category."""
    video_id = extract_youtube_id(case["url"])
    assert video_id, f"Could not extract video id from {case['url']}"

    metadata = await fetch_youtube_metadata(video_id)
    if metadata:
        ctx: dict[str, Any] = {
            "url": case["url"],
            "video_id": video_id,
            **metadata,
        }
    else:
        ctx = {
            "url": case["url"],
            "video_id": video_id,
            "title": case.get("description") or case["title"],
        }

    llm_client = OpenAIClient(model="gpt-4o-mini")
    classifier = LLMBasedYouTubeClassifier(llm_client=llm_client)
    classification = await classifier.classify(Domain("youtube.com"), ctx)

    assert classification is not None
    actual_cat = _category_name(classification)
    expected_cat = case["expected_category"]
    assert actual_cat == expected_cat or _same_category_family(actual_cat, expected_cat), (
        f"{case['name']}: expected category/family {expected_cat}, got {actual_cat}; "
        f"reason={classification.metadata.get('reason')!r}"
    )

    eu = case.get("expected_usefulness")
    if eu:
        assert classification.metadata.get("usefulness") == eu, (
            f"{case['name']}: expected usefulness {eu!r}, got "
            f"{classification.metadata.get('usefulness')!r}"
        )
