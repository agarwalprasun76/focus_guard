"""Tests for persistent classification cache (4.2)."""

import pytest

from focus_guard.core.browser_v2.tab_server.classification_cache_persistent import (
    PersistentClassificationCache,
    get_persistent_classification_cache,
)
from focus_guard.core.browser_v2.tab_server.classification_service import (
    ClassificationResult,
    ContentUsefulness,
)


class TestPersistentClassificationCache:
    def test_set_get_roundtrip(self, tmp_path):
        cache = PersistentClassificationCache(db_path=tmp_path / "cc.db", ttl_seconds=60.0)
        d = {
            "domain": "example.com",
            "url": "https://example.com/v",
            "category": "EDUCATION",
            "usefulness": "educational",
            "confidence": 0.9,
            "reason": "test",
            "classifier_used": "llm",
            "is_distracting": False,
            "content_type": "video",
            "metadata": {},
            "classification_time_ms": 10.0,
        }
        cache.set("key1", d)
        out = cache.get("key1")
        assert out is not None
        assert out["category"] == "EDUCATION"
        assert out["confidence"] == 0.9

    def test_get_miss(self, tmp_path):
        cache = PersistentClassificationCache(db_path=tmp_path / "cc.db")
        assert cache.get("nonexistent") is None

    def test_invalidate_all(self, tmp_path):
        cache = PersistentClassificationCache(db_path=tmp_path / "cc.db")
        cache.set("k", {"domain": "x", "url": "u", "category": "E", "usefulness": "neutral", "confidence": 0.5, "reason": "", "classifier_used": "", "is_distracting": False, "content_type": "", "metadata": {}, "classification_time_ms": 0})
        assert cache.get("k") is not None
        cache.invalidate_all()
        assert cache.get("k") is None


class TestClassificationResultFromDict:
    def test_roundtrip(self):
        r = ClassificationResult(
            domain="youtube.com",
            url="https://youtube.com/watch?v=1",
            category="EDUCATION",
            usefulness=ContentUsefulness.EDUCATIONAL,
            confidence=0.85,
            reason="Educational",
            classifier_used="llm",
            is_distracting=False,
            content_type="video",
            metadata={"a": 1},
            classification_time_ms=50.0,
        )
        d = r.to_dict()
        r2 = ClassificationResult.from_dict(d)
        assert r2.domain == r.domain
        assert r2.category == r.category
        assert r2.usefulness == ContentUsefulness.EDUCATIONAL
        assert r2.confidence == r.confidence
        assert r2.classification_time_ms == r.classification_time_ms
