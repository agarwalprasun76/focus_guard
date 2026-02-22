"""I3-03 accelerated long-session drift stability checks for admin gateway."""

from __future__ import annotations

import time
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from focus_guard.core.admin_gateway.app import create_app
from focus_guard.core.admin_gateway.dependencies import get_auth_service, get_tab_server_client


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


class _SessionDriftTabClient:
    def __init__(self) -> None:
        self._active_overrides: list[dict] = []
        self._log: list[dict] = []
        self._next_id = 1

    def get_json(self, path: str, params=None):
        _ = params
        if path == "/api/health":
            return {"status": "healthy", "machine_name": "drift-host"}
        if path == "/api/status":
            return {"connected_browsers": 1}
        if path == "/api/enforcement_mode":
            return {"enforcement_mode": "enforcing"}
        if path == "/api/distraction/budget":
            used = min(1800, len(self._log) * 30)
            percent = round((used / 2700.0) * 100.0, 2)
            return {
                "total_limit_seconds": 2700,
                "total_used_seconds": used,
                "usage_percent": percent,
                "blocks_today": len(self._log),
                "warning": percent >= 80,
            }
        if path == "/api/distraction/sites":
            return {"sites": [{"domain": "youtube.com", "active_seconds": min(2400, len(self._log) * 20)}]}
        if path == "/api/override/stats":
            return {"total_overrides": len(self._log)}
        if path == "/api/override/log":
            return {"log": list(self._log)}
        if path == "/api/override/active":
            return {"overrides": list(self._active_overrides)}
        return {}

    def post_json(self, path: str, payload: dict):
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if path == "/api/override":
            override_id = f"exc_{self._next_id}"
            self._next_id += 1
            created = {
                "id": override_id,
                "domain": payload.get("domain", "youtube.com"),
                "start_time": now_ts,
                "duration_seconds": int(payload.get("duration", 180)),
                "block_reason": "study",
                "request_reason": payload.get("request_reason", "session-loop"),
            }
            self._active_overrides.append(created)
            self._log.append(
                {
                    "timestamp": now_ts,
                    "event_type": "granted",
                    "action": "granted",
                    "domain": created["domain"],
                    "override_id": created["id"],
                    "details": {"request_reason": created["request_reason"]},
                }
            )
            return {"granted": True, "override": created}

        if path == "/api/override/revoke":
            domain = str(payload.get("domain") or "")
            target = next((x for x in self._active_overrides if x.get("domain") == domain), None)
            self._active_overrides = [x for x in self._active_overrides if x.get("domain") != domain]
            if target:
                self._log.append(
                    {
                        "timestamp": now_ts,
                        "event_type": "revoked",
                        "action": "revoked",
                        "domain": target["domain"],
                        "override_id": target["id"],
                        "details": {"reason": "loop-revoke"},
                    }
                )
            return {"revoked": True, "domain": domain}

        return {"success": True}


class TestLongSessionDrift(unittest.TestCase):
    def setUp(self) -> None:
        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: _FakeAuthService()
        self._tab_client = _SessionDriftTabClient()
        app.dependency_overrides[get_tab_server_client] = lambda: self._tab_client

        self._app = app
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass
        self._app.dependency_overrides = {}

    @staticmethod
    def _auth_headers() -> dict[str, str]:
        return {"Authorization": "Bearer seed-token"}

    def test_accelerated_long_session_has_no_state_drift(self) -> None:
        dashboard_latencies_ms: list[float] = []

        for i in range(90):
            started = time.perf_counter()
            dashboard = self.client.get("/admin/api/v1/dashboard?device_id=drift-host")
            dashboard_latencies_ms.append((time.perf_counter() - started) * 1000.0)
            self.assertEqual(dashboard.status_code, 200)

            if i % 3 == 0:
                create = self.client.post(
                    "/admin/api/v1/exceptions",
                    json={"domain": "youtube.com", "type": "temporary", "duration_seconds": 180},
                    headers=self._auth_headers(),
                )
                self.assertEqual(create.status_code, 200)

            if i % 5 == 0:
                listed = self.client.get("/admin/api/v1/exceptions?status=active&limit=50&offset=0")
                self.assertEqual(listed.status_code, 200)
                active = listed.json()["exceptions"]
                if active:
                    revoke = self.client.delete(
                        f"/admin/api/v1/exceptions/{active[0]['id']}",
                        headers=self._auth_headers(),
                    )
                    self.assertEqual(revoke.status_code, 200)

        final_active = self.client.get("/admin/api/v1/exceptions?status=active&limit=200&offset=0")
        self.assertEqual(final_active.status_code, 200)
        active_items = final_active.json()["exceptions"]

        ids = [item["id"] for item in active_items]
        self.assertEqual(len(ids), len(set(ids)), "active override IDs drifted into duplicates")

        final_dashboard = self.client.get("/admin/api/v1/dashboard?device_id=drift-host")
        self.assertEqual(final_dashboard.status_code, 200)
        dashboard_body = final_dashboard.json()
        self.assertGreaterEqual(int(dashboard_body["overrides_today"]), len(active_items))
        self.assertIn(dashboard_body["device"]["status"], {"online", "offline"})

        p95_idx = int((len(dashboard_latencies_ms) - 1) * 0.95)
        p95 = sorted(dashboard_latencies_ms)[p95_idx]
        self.assertLess(p95, 500.0)


if __name__ == "__main__":
    unittest.main()
