"""Route protection tests for admin gateway mutation endpoints (P2-03)."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from focus_guard.core.admin_gateway.app import create_app
from focus_guard.core.admin_gateway.dependencies import get_auth_service, get_tab_server_client


class _FakeAuthService:
    def me(self, token: str):
        if token != "valid-token":
            class _Err(Exception):
                status_code = 401
                code = "UNAUTHORIZED"
                message = "invalid token"

            raise _Err()
        return {"username": "admin", "role": "admin", "created_at": None}


class _FakeTabServerClient:
    def get_json(self, path, params=None):
        if path == "/api/override/active":
            return {"overrides": [{"id": "exc_1", "domain": "youtube.com"}]}
        if path == "/api/override/log":
            return {"log": []}
        return {}

    def post_json(self, path, payload):
        if path == "/api/override":
            return {
                "granted": True,
                "override": {
                    "id": "exc_1",
                    "start_time": 0,
                    "duration_seconds": payload.get("duration", 0),
                },
            }
        if path == "/api/override/revoke":
            return {"revoked": True, "domain": payload.get("domain")}
        return {"success": True}


class TestAuthRouteProtection(unittest.TestCase):
    def setUp(self) -> None:
        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: _FakeAuthService()
        app.dependency_overrides[get_tab_server_client] = lambda: _FakeTabServerClient()
        self.client = TestClient(app)

    def test_post_exceptions_requires_auth(self) -> None:
        response = self.client.post("/admin/api/v1/exceptions", json={"domain": "youtube.com"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_protected_mutations_reject_malformed_bearer_header(self) -> None:
        response = self.client.post(
            "/admin/api/v1/exceptions",
            json={"domain": "youtube.com", "type": "temporary", "duration_seconds": 300},
            headers={"Authorization": "Token valid-token"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_protected_mutations_reject_invalid_token(self) -> None:
        response = self.client.put(
            "/admin/api/v1/devices/default-device/enforcement",
            json={"mode": "tracking"},
            headers={"Authorization": "Bearer invalid-token"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_delete_exceptions_requires_auth(self) -> None:
        response = self.client.delete("/admin/api/v1/exceptions/exc_1")
        self.assertEqual(response.status_code, 401)

    def test_put_devices_enforcement_requires_auth(self) -> None:
        response = self.client.put(
            "/admin/api/v1/devices/default-device/enforcement",
            json={"mode": "tracking"},
        )
        self.assertEqual(response.status_code, 401)

    def test_protected_mutations_accept_valid_bearer(self) -> None:
        headers = {"Authorization": "Bearer valid-token"}

        post_response = self.client.post(
            "/admin/api/v1/exceptions",
            json={"domain": "youtube.com", "type": "temporary", "duration_seconds": 300},
            headers=headers,
        )
        self.assertEqual(post_response.status_code, 200)

        delete_response = self.client.delete(
            "/admin/api/v1/exceptions/exc_1",
            headers=headers,
        )
        self.assertEqual(delete_response.status_code, 200)

        put_response = self.client.put(
            "/admin/api/v1/devices/default-device/enforcement",
            json={"mode": "tracking"},
            headers=headers,
        )
        self.assertEqual(put_response.status_code, 200)

    def test_non_mutation_exceptions_list_is_not_guarded_in_p2_03(self) -> None:
        response = self.client.get("/admin/api/v1/exceptions")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
