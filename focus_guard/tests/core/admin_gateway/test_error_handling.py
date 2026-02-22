"""Tests for structured error model and translation layer (P2-07)."""

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
        return {}

    def post_json(self, path, payload):
        return {"success": True, "enforcement_mode": payload.get("mode", "enforcing")}


class TestStructuredErrorModel(unittest.TestCase):
    def setUp(self) -> None:
        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: _FakeAuthService()
        app.dependency_overrides[get_tab_server_client] = lambda: _FakeTabServerClient()
        self.client = TestClient(app)

    def test_auth_missing_token_uses_error_envelope(self) -> None:
        response = self.client.get("/admin/api/v1/devices")

        self.assertEqual(response.status_code, 401)
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(body["error"]["message"], "missing bearer token")

    def test_validation_error_uses_standard_model(self) -> None:
        # password is required in LoginRequest
        response = self.client.post("/admin/api/v1/auth/login", json={"username": "admin"})

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("details", body["error"])


if __name__ == "__main__":
    unittest.main()
