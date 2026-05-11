from __future__ import annotations

from focus_guard.core.admin_gateway.services.dashboard_service import DashboardService


class _FakeTabServerClient:
    def __init__(self, get_map=None):
        self.get_map = get_map or {}
        self.calls = []

    def get_json(self, path, params=None):
        self.calls.append((path, params))
        value = self.get_map.get(path)
        if callable(value):
            return value(params)
        if value is None:
            return {}
        return value


def test_dashboard_includes_consolidated_kpis_and_generated_at():
    client = _FakeTabServerClient(
        get_map={
            "/api/health": {"machine_name": "kid-laptop"},
            "/api/distraction/budget": {
                "total_limit_seconds": 3600,
                "total_used_seconds": 900,
                "usage_percent": 25,
                "blocks_today": 3,
            },
            "/api/distraction/sites": {"sites": [{"domain": "youtube.com", "active_seconds": 300}]},
            "/api/override/stats": {"total_overrides": 2},
            "/api/override/log": {"log": [{"domain": "youtube.com", "override_id": "abc", "details": {"remaining_seconds": 100}}]},
            "/api/enforcement_mode": {"enforcement_mode": "advisory"},
            "/api/blocked/sites": {"blocked_sites": [{"domain": "youtube.com", "count": 3}], "total_blocks": 3},
            "/api/saved_links/stats": {"total": 5, "unviewed": 2, "top_domains": []},
            "/api/saved_links": {"links": []},
            "/api/tabs": {"tabs": []},
            "/api/activity/stats": {"total_events": 12, "blocked_count": 4, "distracting_count": 6},
            "/api/activity/logs": {"activities": []},
        }
    )
    svc = DashboardService(client)

    result = svc.get_dashboard()

    assert result["device"]["name"] == "default-device"
    assert isinstance(result["generated_at_utc"], float)
    assert result["kpis"]["focus_score"] == 75
    assert result["kpis"]["blocks_today"] == 3
    assert result["kpis"]["overrides_today"] == 2
    assert result["kpis"]["usage_percent"] == 25
    assert result["kpis"]["total_events"] == 12
    assert result["kpis"]["unviewed_saved_links"] == 2


def test_dashboard_passes_date_range_to_override_log_request():
    captured_params = {}

    def _override_log(params):
        captured_params.update(params or {})
        return {"log": []}

    client = _FakeTabServerClient(
        get_map={
            "/api/health": {},
            "/api/distraction/budget": {},
            "/api/distraction/sites": {"sites": []},
            "/api/override/stats": {},
            "/api/override/log": _override_log,
            "/api/enforcement_mode": {},
            "/api/blocked/sites": {},
            "/api/saved_links/stats": {},
            "/api/saved_links": {},
            "/api/tabs": {"tabs": []},
            "/api/activity/stats": {},
            "/api/activity/logs": {"activities": []},
        }
    )
    svc = DashboardService(client)
    svc.get_dashboard(start_date="2026-05-01", end_date="2026-05-03")

    assert captured_params["since"] == "2026-05-01"
    assert captured_params["until"] == "2026-05-03"
    assert captured_params["limit"] == 25

    assert ("/api/activity/stats", {"start_date": "2026-05-01", "end_date": "2026-05-03"}) in client.calls
    log_calls = [c for c in client.calls if c[0] == "/api/activity/logs"]
    assert log_calls
    assert log_calls[0][1] == {
        "start_date": "2026-05-01",
        "end_date": "2026-05-03",
        "blocked": "true",
        "limit": 10,
    }

