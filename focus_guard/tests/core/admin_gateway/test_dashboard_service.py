"""Unit tests for admin gateway DashboardService aggregation (P2-04)."""

from __future__ import annotations

import unittest

from focus_guard.core.admin_gateway.services.dashboard_service import DashboardService
from focus_guard.core.admin_gateway.services.tab_server_client import TabServerUnavailableError


class _FakeTabClient:
    def __init__(self, payloads):
        self.payloads = payloads

    def get_json(self, path, params=None):
        key = (path, tuple(sorted((params or {}).items())))
        value = self.payloads.get(key)
        if isinstance(value, Exception):
            raise value
        if value is None:
            return {}
        return value


class TestDashboardService(unittest.TestCase):
    def test_aggregates_dashboard_payload(self) -> None:
        payloads = {
            ("/api/health", ()): {"status": "healthy"},
            ("/api/distraction/budget", ()): {
                "total_limit_seconds": 2700,
                "total_used_seconds": 1350,
                "usage_percent": 50.0,
                "blocks_today": 4,
                "warning": True,
            },
            ("/api/distraction/sites", ()): {
                "sites": [
                    {"domain": "youtube.com", "active_seconds": 900},
                    {"domain": "reddit.com", "active_seconds": 300},
                ],
            },
            ("/api/override/stats", ()): {"total_overrides": 5},
            ("/api/override/log", (("limit", 25),)): {
                "log": [
                    {"domain": "youtube.com", "action": "granted", "override_id": "o1", "details": {}},
                    {"domain": "youtube.com", "action": "granted", "override_id": "o2", "details": {}},
                    {"domain": "youtube.com", "action": "granted", "override_id": "o3", "details": {}},
                    {"domain": "reddit.com", "action": "granted", "override_id": "o4", "details": {}},
                ]
            },
            ("/api/enforcement_mode", ()): {"enforcement_mode": "enforcing"},
            ("/api/blocked/sites", ()): {
                "blocked_sites": [
                    {"domain": "youtube.com", "count": 3, "category": "ENTERTAINMENT"},
                    {"domain": "reddit.com", "count": 1, "category": "SOCIAL_MEDIA"},
                ],
                "total_blocks": 4,
                "blocks_today": 4,
            },
            ("/api/saved_links/stats", ()): {
                "total": 3,
                "unviewed": 2,
                "top_domains": [{"domain": "youtube.com", "count": 2}],
            },
            ("/api/saved_links", (("limit", 5),)): {
                "links": [
                    {
                        "id": 1,
                        "url": "https://youtube.com/watch?v=1",
                        "domain": "youtube.com",
                        "title": "Video",
                        "category": "ENTERTAINMENT",
                        "comment": "later",
                        "saved_at": "2026-02-21T10:00:00",
                        "viewed": False,
                        "viewed_at": None,
                    }
                ]
            },
            ("/api/tabs", ()): {
                "tabs": [
                    {
                        "id": "tab-1",
                        "browser": "chrome",
                        "title": "Focus task",
                        "url": "https://docs.example.com",
                        "active": True,
                    }
                ]
            },
            ("/api/activity/stats", ()): {
                "total_events": 20,
                "blocked_count": 5,
                "distracting_count": 8,
                "blocked_percentage": 25.0,
                "distracting_percentage": 40.0,
            },
            ("/api/activity/logs", (("blocked", "true"), ("limit", 10))): {
                "activities": [
                    {
                        "timestamp": "2026-02-21T11:00:00Z",
                        "domain": "youtube.com",
                        "title": "video",
                        "url": "https://youtube.com/watch?v=x",
                        "browser": "chrome",
                        "block_reason": "budget_exceeded",
                    }
                ]
            },
        }
        service = DashboardService(_FakeTabClient(payloads))

        dashboard = service.get_dashboard(device_id="prasun-pc")

        self.assertEqual(dashboard["device"]["id"], "prasun-pc")
        self.assertEqual(dashboard["device"]["status"], "online")
        self.assertEqual(dashboard["focus_score"], 50)
        self.assertEqual(dashboard["blocks_today"], 4)
        self.assertEqual(dashboard["overrides_today"], 5)
        self.assertEqual(len(dashboard["blocked_sites"]), 2)
        self.assertEqual(dashboard["total_blocks"], 4)
        self.assertEqual(dashboard["saved_links"]["unviewed"], 2)
        self.assertEqual(len(dashboard["saved_links"]["recent"]), 1)
        self.assertEqual(dashboard["activity_summary"]["total_events"], 20)
        self.assertEqual(len(dashboard["open_tabs"]), 1)
        self.assertEqual(len(dashboard["recent_blocked_tabs"]), 1)
        self.assertGreaterEqual(len(dashboard["top_friction"]), 1)
        self.assertTrue(any(i["type"] == "budget_warning" for i in dashboard["attention_items"]))
        self.assertTrue(any(i["type"] == "frequent_override" for i in dashboard["attention_items"]))

    def test_returns_offline_defaults_when_tab_server_unavailable(self) -> None:
        unavailable = TabServerUnavailableError("connection refused")
        payloads = {
            ("/api/health", ()): unavailable,
            ("/api/distraction/budget", ()): unavailable,
            ("/api/distraction/sites", ()): unavailable,
            ("/api/override/stats", ()): unavailable,
            ("/api/override/log", (("limit", 25),)): unavailable,
            ("/api/enforcement_mode", ()): unavailable,
            ("/api/blocked/sites", ()): unavailable,
            ("/api/saved_links/stats", ()): unavailable,
            ("/api/saved_links", (("limit", 5),)): unavailable,
            ("/api/tabs", ()): unavailable,
            ("/api/activity/stats", ()): unavailable,
            ("/api/activity/logs", (("blocked", "true"), ("limit", 10))): unavailable,
        }
        service = DashboardService(_FakeTabClient(payloads))

        dashboard = service.get_dashboard(device_id="offline-device")

        self.assertEqual(dashboard["device"]["status"], "offline")
        self.assertEqual(dashboard["focus_score"], 100)
        self.assertEqual(dashboard["overrides_today"], 0)
        self.assertEqual(dashboard["blocked_sites"], [])
        self.assertEqual(dashboard["total_blocks"], 0)
        self.assertEqual(dashboard["saved_links"]["total"], 0)
        self.assertEqual(dashboard["saved_links"]["recent"], [])
        self.assertEqual(dashboard["activity_summary"]["total_events"], 0)
        self.assertEqual(dashboard["open_tabs"], [])
        self.assertEqual(dashboard["recent_blocked_tabs"], [])
        self.assertEqual(dashboard["attention_items"], [])


if __name__ == "__main__":
    unittest.main()
