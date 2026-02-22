"""Agent-in-the-loop integration tests against a live tab server (P4-04)."""

from __future__ import annotations

import socket
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from focus_guard.core.admin_gateway.app import create_app
from focus_guard.core.admin_gateway.dependencies import get_auth_service, get_tab_server_client
from focus_guard.core.admin_gateway.services.tab_server_client import TabServerClient
from focus_guard.core.browser_v2.tab_server.runner import TabServerRunner


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


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class TestAgentInLoopRealTabServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._runner = TabServerRunner(
            host="127.0.0.1",
            port=_get_free_port(),
            use_persistent_blocking=False,
            health_check_interval=1.0,
        )
        cls._runner._start_security_monitors = lambda: None
        cls._runner._stop_security_monitors = lambda: None

        if not cls._runner.start():
            raise unittest.SkipTest(f"Could not start tab server: {cls._runner.get_status().error_message}")

        app = create_app()
        auth_service = _FakeAuthService()
        tab_client = TabServerClient(base_url=f"http://127.0.0.1:{cls._runner.get_status().port}")

        app.dependency_overrides[get_auth_service] = lambda: auth_service
        app.dependency_overrides[get_tab_server_client] = lambda: tab_client

        cls._app = app
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.client.close()
        except Exception:
            pass

        try:
            cls._app.dependency_overrides = {}
        except Exception:
            pass

        try:
            cls._runner.stop()
        except Exception:
            pass

        super().tearDownClass()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer seed-token"}

    def test_dashboard_and_devices_read_from_live_tab_server(self) -> None:
        dashboard = self.client.get("/admin/api/v1/dashboard?device_id=agent-loop-pc")
        self.assertEqual(dashboard.status_code, 200)
        dashboard_body = dashboard.json()
        self.assertEqual(dashboard_body["device"]["status"], "online")
        self.assertIn("budget", dashboard_body)
        self.assertIn("top_friction", dashboard_body)

        devices = self.client.get("/admin/api/v1/devices", headers=self._auth_headers())
        self.assertEqual(devices.status_code, 200)
        devices_body = devices.json()
        self.assertIn("devices", devices_body)
        self.assertGreaterEqual(len(devices_body["devices"]), 1)
        self.assertIn("browser_status", devices_body["devices"][0])

    def test_allow_and_revoke_override_against_live_tab_server(self) -> None:
        created = self.client.post(
            "/admin/api/v1/exceptions",
            json={"domain": "youtube.com", "type": "temporary", "duration_seconds": 180, "reason": "agent-loop"},
            headers=self._auth_headers(),
        )
        self.assertEqual(created.status_code, 200)
        created_body = created.json()
        self.assertEqual(created_body["type"], "temporary")
        self.assertEqual(created_body["status"], "active")
        self.assertTrue(created_body.get("id"))

        active_list = self.client.get("/admin/api/v1/exceptions?status=active&limit=50&offset=0")
        self.assertEqual(active_list.status_code, 200)
        active_body = active_list.json()
        self.assertGreaterEqual(active_body["total"], 1)

        revoke = self.client.delete(
            f"/admin/api/v1/exceptions/{created_body['id']}",
            headers=self._auth_headers(),
        )
        self.assertEqual(revoke.status_code, 200)
        self.assertEqual(revoke.json(), {"revoked": True, "id": created_body["id"]})


if __name__ == "__main__":
    unittest.main()
