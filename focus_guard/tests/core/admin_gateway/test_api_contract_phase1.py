"""Contract-style API tests for admin gateway Phase 1 (P2-10)."""

from __future__ import annotations

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


class _FakeTabServerClient:
    def __init__(self) -> None:
        self.enforcement_mode = "enforcing"
        self._active_overrides = [
            {
                "id": "exc_1",
                "domain": "youtube.com",
                "start_time": 1000,
                "duration_seconds": 300,
                "block_reason": "study",
                "request_reason": "homework video",
            }
        ]
        self._log = [
            {
                "timestamp": 1000,
                "event_type": "granted",
                "action": "granted",
                "domain": "youtube.com",
                "override_id": "exc_1",
                "details": {"request_reason": "homework video"},
            }
        ]

    def get_json(self, path, params=None):
        if path == "/api/health":
            return {"status": "healthy", "machine_name": "prasun-pc"}
        if path == "/api/status":
            return {"connected_browsers": 2}
        if path == "/api/enforcement_mode":
            return {"enforcement_mode": self.enforcement_mode}
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
            return {"total_overrides": len(self._log)}
        if path == "/api/override/log":
            return {"log": list(self._log)}
        if path == "/api/override/active":
            return {"overrides": list(self._active_overrides)}
        return {}

    def post_json(self, path, payload):
        if path == "/api/override":
            created = {
                "id": "exc_2",
                "domain": payload.get("domain"),
                "start_time": 2000,
                "duration_seconds": payload.get("duration", 300),
                "block_reason": "admin",
                "request_reason": payload.get("request_reason", ""),
            }
            self._active_overrides.append(created)
            self._log.append(
                {
                    "timestamp": 2000,
                    "event_type": "granted",
                    "action": "granted",
                    "domain": created["domain"],
                    "override_id": created["id"],
                    "details": {"request_reason": created["request_reason"]},
                }
            )
            return {"granted": True, "override": created}
        if path == "/api/override/revoke":
            domain = payload.get("domain")
            self._active_overrides = [x for x in self._active_overrides if x.get("domain") != domain]
            return {"revoked": True, "domain": domain}
        if path == "/api/enforcement_mode":
            self.enforcement_mode = payload.get("mode", self.enforcement_mode)
            return {"success": True, "enforcement_mode": self.enforcement_mode}
        return {"success": True}


class TestApiContractPhase1(unittest.TestCase):
    def setUp(self) -> None:
        app = create_app()
        auth_service = _FakeAuthService()
        tab_client = _FakeTabServerClient()
        app.dependency_overrides[get_auth_service] = lambda: auth_service
        app.dependency_overrides[get_tab_server_client] = lambda: tab_client
        self.client = TestClient(app)

    def _auth_headers(self):
        return {"Authorization": "Bearer seed-token"}

    def test_auth_login_refresh_me_logout_contract(self) -> None:
        login = self.client.post("/admin/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
        self.assertEqual(login.status_code, 200)
        login_body = login.json()
        self.assertIn("token", login_body)
        self.assertIn("expires_at", login_body)
        self.assertEqual(login_body["role"], "admin")

        refresh = self.client.post("/admin/api/v1/auth/refresh", json={"token": "seed-token"})
        self.assertEqual(refresh.status_code, 200)
        self.assertIn("token", refresh.json())

        me = self.client.get("/admin/api/v1/auth/me", headers={"Authorization": "Bearer seed-token-r"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["username"], "admin")

        logout = self.client.post("/admin/api/v1/auth/logout", headers={"Authorization": "Bearer seed-token-r"})
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(logout.json(), {"success": True})

    def test_meta_contract_includes_capabilities_and_readiness(self) -> None:
        response = self.client.get("/admin/api/v1/meta")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["service"], "admin_gateway")
        self.assertEqual(body["version"], "0.1.0")
        self.assertIn("capabilities", body)
        self.assertIn("readiness", body)
        self.assertTrue(body["capabilities"]["request_id"])
        self.assertEqual(body["readiness"]["gateway"], "online")
        self.assertIn(body["readiness"]["tab_server"], {"online", "offline"})

    def test_dashboard_contract_shape(self) -> None:
        response = self.client.get("/admin/api/v1/dashboard?device_id=prasun-pc")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("device", body)
        self.assertIn("focus_score", body)
        self.assertIn("budget", body)
        self.assertIn("blocks_today", body)
        self.assertIn("overrides_today", body)
        self.assertIn("attention_items", body)
        self.assertIn("recent_overrides", body)
        self.assertIn("top_friction", body)

    def test_exceptions_contract_shape(self) -> None:
        create = self.client.post(
            "/admin/api/v1/exceptions",
            json={"domain": "youtube.com", "type": "temporary", "duration_seconds": 300},
            headers=self._auth_headers(),
        )
        self.assertEqual(create.status_code, 200)
        created = create.json()
        self.assertEqual(created["type"], "temporary")
        self.assertEqual(created["status"], "active")
        self.assertIn("id", created)

        listing = self.client.get("/admin/api/v1/exceptions?status=all&limit=50&offset=0")
        self.assertEqual(listing.status_code, 200)
        list_body = listing.json()
        self.assertIn("exceptions", list_body)
        self.assertIn("total", list_body)
        self.assertIn("limit", list_body)
        self.assertIn("offset", list_body)

        revoke = self.client.delete("/admin/api/v1/exceptions/exc_1", headers=self._auth_headers())
        self.assertEqual(revoke.status_code, 200)
        self.assertEqual(revoke.json()["revoked"], True)

    def test_dashboard_and_exceptions_remain_consistent_after_create(self) -> None:
        before = self.client.get("/admin/api/v1/dashboard?device_id=prasun-pc")
        self.assertEqual(before.status_code, 200)
        before_count = int(before.json()["overrides_today"])

        create = self.client.post(
            "/admin/api/v1/exceptions",
            json={"domain": "reddit.com", "type": "temporary", "duration_seconds": 300},
            headers=self._auth_headers(),
        )
        self.assertEqual(create.status_code, 200)

        listed = self.client.get("/admin/api/v1/exceptions?status=all&limit=50&offset=0")
        self.assertEqual(listed.status_code, 200)
        self.assertGreaterEqual(int(listed.json()["total"]), 1)

        after = self.client.get("/admin/api/v1/dashboard?device_id=prasun-pc")
        self.assertEqual(after.status_code, 200)
        self.assertGreaterEqual(int(after.json()["overrides_today"]), before_count)

    def test_devices_contract_shape(self) -> None:
        devices = self.client.get("/admin/api/v1/devices", headers=self._auth_headers())
        self.assertEqual(devices.status_code, 200)
        body = devices.json()
        self.assertIn("devices", body)
        self.assertEqual(body["devices"][0]["id"], "prasun-pc")
        self.assertIn("browser_status", body["devices"][0])

        enforcement = self.client.put(
            "/admin/api/v1/devices/prasun-pc/enforcement",
            json={"mode": "tracking"},
            headers=self._auth_headers(),
        )
        self.assertEqual(enforcement.status_code, 200)
        self.assertEqual(enforcement.json()["updated"], True)
        self.assertEqual(enforcement.json()["mode"], "tracking")

    def test_structured_error_contract_for_unauthorized(self) -> None:
        response = self.client.put(
            "/admin/api/v1/devices/prasun-pc/enforcement",
            json={"mode": "tracking"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIsNotNone(response.headers.get("x-request-id"))
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertIn("message", body["error"])

    def test_health_honors_provided_request_id_header(self) -> None:
        response = self.client.get("/admin/health", headers={"X-Request-ID": "req-contract-123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("x-request-id"), "req-contract-123")


if __name__ == "__main__":
    unittest.main()
