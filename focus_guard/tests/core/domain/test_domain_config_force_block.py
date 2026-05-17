"""Tests for guardian force-block overrides (FR-032 / US-A2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from focus_guard.core.domain.domain_config_manager import DomainConfigManager


@pytest.fixture
def mgr(tmp_path: Path) -> DomainConfigManager:
    config_path = tmp_path / "domain_config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "domain_categories": {"education": ["school.example.com"]},
                "always_allowed_domains": [],
                "always_allowed_categories": ["EDUCATION"],
                "force_blocked_domains": [],
                "blocked_categories": ["ENTERTAINMENT"],
                "system_whitelist": [],
                "per_domain_rules": {},
                "classification_budgets": {},
                "master_budget": {"max_total_distraction_seconds": 3600},
            }
        ),
        encoding="utf-8",
    )
    return DomainConfigManager(config_path=config_path)


def test_education_domain_allowed_by_category(mgr: DomainConfigManager) -> None:
    assert mgr.get_domain_status("school.example.com") == "allowed"
    assert mgr.get_domain_allow_reason("school.example.com") == "category"


def test_force_block_overrides_category_allow(mgr: DomainConfigManager) -> None:
    mgr.add_force_blocked_domain("school.example.com")
    assert mgr.get_domain_status("school.example.com") == "blocked"
    assert mgr.get_domain_allow_reason("school.example.com") is None


def test_remove_force_block_restores_category_allow(mgr: DomainConfigManager) -> None:
    mgr.add_force_blocked_domain("school.example.com")
    assert mgr.remove_force_blocked_domain("school.example.com")
    assert mgr.get_domain_status("school.example.com") == "allowed"
