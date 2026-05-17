from __future__ import annotations

import pytest

from focus_guard.core.admin_gateway.services.settings_service import (
    SettingsService,
    SettingsServiceError,
)
from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerRequestError,
    TabServerUnavailableError,
)


class _FakeTabServerClient:
    def __init__(self, get_map=None, post_map=None, post_exc=None):
        self.get_map = get_map or {}
        self.post_map = post_map or {}
        self.post_exc = post_exc

    def get_json(self, path, params=None):
        value = self.get_map.get(path)
        if isinstance(value, Exception):
            raise value
        return value

    def post_json(self, path, payload):
        if self.post_exc:
            raise self.post_exc
        value = self.post_map.get(path, {})
        if isinstance(value, Exception):
            raise value
        return value


def test_set_enforcement_mode_validation():
    service = SettingsService(_FakeTabServerClient())
    with pytest.raises(SettingsServiceError) as exc:
        service.set_enforcement_mode("invalid")
    assert exc.value.code == "VALIDATION_ERROR"
    assert exc.value.status_code == 400


def test_get_budgets_injects_defaults_and_master_daily_seconds():
    service = SettingsService(
        _FakeTabServerClient(
            get_map={
                "/api/domains/budgets": {
                    "classification_budgets": {
                        "ENTERTAINMENT:DISTRACTION": {"max_cumulative_time_seconds": 900},
                    },
                    "master_budget": {"max_total_distraction_seconds": 2700},
                },
                "/api/distraction/budget": {"used_seconds": 100, "budget_seconds": 2700},
            }
        )
    )

    result = service.get_budgets()
    cb = result["classification_budgets"]
    assert cb["ENTERTAINMENT:DISTRACTION"]["daily_seconds"] == 900
    assert "GAMING:DISTRACTION" in cb
    assert result["master_budget"]["daily_seconds"] == 2700
    assert result["distraction"]["used_seconds"] == 100


def test_get_enforcement_mode_offline_mapping():
    service = SettingsService(
        _FakeTabServerClient(get_map={"/api/enforcement_mode": TabServerUnavailableError("offline")})
    )
    with pytest.raises(SettingsServiceError) as exc:
        service.get_enforcement_mode()
    assert exc.value.code == "DEVICE_OFFLINE"
    assert exc.value.status_code == 409


def test_update_master_budget_maps_daily_seconds():
    captured: dict = {}

    class _CapturingClient(_FakeTabServerClient):
        def post_json(self, path, payload):
            captured["path"] = path
            captured["payload"] = payload
            return {"success": True}

    service = SettingsService(_CapturingClient())
    service.update_master_budget({"daily_seconds": 900})
    assert captured["path"] == "/api/domains/budgets/master"
    assert captured["payload"] == {"max_total_distraction_seconds": 900}


def test_update_master_budget_requires_a_field():
    service = SettingsService(_FakeTabServerClient())
    with pytest.raises(SettingsServiceError) as exc:
        service.update_master_budget({})
    assert exc.value.code == "VALIDATION_ERROR"


def test_set_enforcement_mode_maps_403_to_validation_error():
    service = SettingsService(
        _FakeTabServerClient(post_exc=TabServerRequestError(status_code=403, message="password required"))
    )
    with pytest.raises(SettingsServiceError) as exc:
        service.set_enforcement_mode("enforcing")
    assert exc.value.code == "VALIDATION_ERROR"
    assert exc.value.status_code == 403

