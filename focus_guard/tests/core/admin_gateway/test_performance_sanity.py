"""P4-06 performance sanity checks for admin gateway API latency."""

from __future__ import annotations

import json
import socket
import time
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


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int((len(ordered) - 1) * p)
    return ordered[idx]


class TestPerformanceSanity(unittest.TestCase):
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

    def _measure_endpoint(self, method: str, path: str, *, auth: bool = False, iterations: int = 20) -> dict[str, float]:
        headers = {"Authorization": "Bearer seed-token"} if auth else None
        timings_ms: list[float] = []

        for _ in range(iterations):
            start = time.perf_counter()
            if method == "GET":
                response = self.client.get(path, headers=headers)
            else:
                raise AssertionError(f"Unsupported method: {method}")
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self.assertEqual(response.status_code, 200)
            timings_ms.append(elapsed_ms)

        return {
            "avg_ms": round(sum(timings_ms) / len(timings_ms), 2),
            "p95_ms": round(_percentile(timings_ms, 0.95), 2),
            "max_ms": round(max(timings_ms), 2),
        }

    def test_api_latency_sanity_snapshot(self) -> None:
        snapshot = {
            "health": self._measure_endpoint("GET", "/admin/health"),
            "dashboard": self._measure_endpoint("GET", "/admin/api/v1/dashboard?device_id=perf-host"),
            "devices": self._measure_endpoint("GET", "/admin/api/v1/devices", auth=True),
            "exceptions_list": self._measure_endpoint(
                "GET",
                "/admin/api/v1/exceptions?status=all&limit=50&offset=0",
            ),
        }

        print("P4-06_API_LATENCY_SNAPSHOT=" + json.dumps(snapshot, sort_keys=True))

        # Sanity thresholds for local dev environment (non-benchmark grade)
        self.assertLess(snapshot["health"]["p95_ms"], 500.0)
        self.assertLess(snapshot["dashboard"]["p95_ms"], 1000.0)
        self.assertLess(snapshot["devices"]["p95_ms"], 1000.0)
        self.assertLess(snapshot["exceptions_list"]["p95_ms"], 1000.0)


if __name__ == "__main__":
    unittest.main()
