"""I3-01 fault-injection coverage for admin gateway resilience behavior."""

from __future__ import annotations

import time
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from focus_guard.core.admin_gateway.app import create_app
from focus_guard.core.admin_gateway.dependencies import get_auth_service, get_tab_server_client
from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerRequestError,
    TabServerUnavailableError,
)


class _AuthErr(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class _FakeAuthService:
    def __init__(self) -> None:
        self._tokens = {"seed-token"}
        self._issued_at = datetime.now(timezone.utc)

    def login(self, username: str, password: str):
        if username != "admin" or password != "secret123":
            raise _AuthErr("UNAUTHORIZED", "invalid credentials", 401)
        return {
            "token": "seed-token",
            "expires_at": self._issued_at + timedelta(hours=1),
            "role": "admin",
        }

    def refresh(self, token: str):
        if token not in self._tokens:
            raise _AuthErr("UNAUTHORIZED", "invalid token", 401)
        self._tokens.remove(token)
        self._tokens.add("seed-token-r")
        return {
            "token": "seed-token-r",
            "expires_at": self._issued_at + timedelta(hours=2),
            "role": "admin",
        }

    def logout(self, token: str):
        if token:
            self._tokens.discard(token)
        return {"success": True}

    def me(self, token: str):
        if token not in self._tokens:
            raise _AuthErr("UNAUTHORIZED", "invalid token", 401)
        return {"username": "admin", "role": "admin", "created_at": self._issued_at}


class _FaultInjectionTabClient:
    def __init__(self) -> None:
        self.mode = "healthy"

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def get_json(self, path: str, params=None):
        _ = params

        if self.mode == "timeout":
            if path in {"/api/health", "/api/distraction/budget", "/api/distraction/sites"}:
                raise TabServerUnavailableError("simulated timeout")
        if self.mode == "connection_reset":
            if path in {"/api/override/stats", "/api/override/log", "/api/override/active"}:
                raise TabServerUnavailableError("simulated connection reset")
        if self.mode == "bad_json":
            raise TabServerRequestError(502, "invalid json")

        if path == "/api/health":
            return {"status": "healthy", "machine_name": "resilience-host"}
        if path == "/api/distraction/budget":
            return {
                "total_limit_seconds": 2700,
                "total_used_seconds": 600,
                "usage_percent": 22.2,
                "blocks_today": 3,
                "warning": False,
            }
        if path == "/api/distraction/sites":
            return {"sites": [{"domain": "youtube.com", "active_seconds": 600}]}
        if path == "/api/override/stats":
            return {"total_overrides": 2}
        if path == "/api/override/log":
            return {
                "log": [
                    {
                        "timestamp": 1000,
                        "event_type": "granted",
                        "action": "granted",
                        "domain": "youtube.com",
                        "override_id": "exc_1",
                        "details": {"request_reason": "homework"},
                    }
                ]
            }
        if path == "/api/override/active":
            return {"overrides": []}
        if path == "/api/enforcement_mode":
            return {"enforcement_mode": "enforcing"}
        return {}


class TestResilienceFaultInjection(unittest.TestCase):
    def setUp(self) -> None:
        self.tab_client = _FaultInjectionTabClient()
        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: _FakeAuthService()
        app.dependency_overrides[get_tab_server_client] = lambda: self.tab_client
        self._app = app
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass
        self._app.dependency_overrides = {}

    def test_fault_injection_timeout_and_reset_show_degraded_not_crash(self) -> None:
        self.tab_client.set_mode("timeout")

        meta = self.client.get("/admin/api/v1/meta")
        self.assertEqual(meta.status_code, 200)
        self.assertEqual(meta.json()["readiness"]["tab_server"], "offline")
        self.assertEqual(meta.json()["readiness"]["enforcement"], "degraded")

        dashboard = self.client.get("/admin/api/v1/dashboard?device_id=resilience-host")
        self.assertEqual(dashboard.status_code, 200)
        body = dashboard.json()
        self.assertEqual(body["device"]["status"], "offline")
        self.assertEqual(body["budget"]["used_seconds"], 0)
        self.assertIsInstance(body["top_friction"], list)

        self.tab_client.set_mode("connection_reset")
        listing = self.client.get("/admin/api/v1/exceptions?status=all&limit=50&offset=0")
        self.assertEqual(listing.status_code, 409)
        self.assertEqual(listing.json()["error"]["code"], "DEVICE_OFFLINE")

    def test_recovery_path_returns_online_without_process_restart(self) -> None:
        self.tab_client.set_mode("bad_json")
        degraded = self.client.get("/admin/api/v1/meta")
        self.assertEqual(degraded.status_code, 200)
        self.assertEqual(degraded.json()["readiness"]["tab_server"], "offline")

        self.tab_client.set_mode("healthy")
        recovered_meta = self.client.get("/admin/api/v1/meta")
        self.assertEqual(recovered_meta.status_code, 200)
        self.assertEqual(recovered_meta.json()["readiness"]["tab_server"], "online")

        recovered_dashboard = self.client.get("/admin/api/v1/dashboard?device_id=resilience-host")
        self.assertEqual(recovered_dashboard.status_code, 200)
        self.assertEqual(recovered_dashboard.json()["device"]["status"], "online")

    def test_latency_injection_sanity_budget(self) -> None:
        original_get_json = self.tab_client.get_json

        def delayed_get_json(path: str, params=None):
            time.sleep(0.02)
            return original_get_json(path, params=params)

        self.tab_client.get_json = delayed_get_json
        start = time.perf_counter()
        response = self.client.get("/admin/api/v1/dashboard?device_id=resilience-host")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed_ms, 1200.0)


if __name__ == "__main__":
    unittest.main()
