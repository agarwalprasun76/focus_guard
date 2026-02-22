"""Tests for P2-08 CORS/origin accessibility safeguards."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from focus_guard.core.admin_gateway.app import create_app
from focus_guard.core.admin_gateway.config import AdminGatewayConfig


class TestOriginSafeguards(unittest.TestCase):
    def test_blocks_unallowed_origin(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.get("/admin/health", headers={"Origin": "http://evil.example"})

        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(body["error"]["message"], "origin not allowed")

    def test_blocks_unallowed_origin_on_api_route(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.get("/admin/api/v1/dashboard", headers={"Origin": "http://evil.example"})

        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(body["error"]["message"], "origin not allowed")

    def test_allows_configured_lan_origin(self) -> None:
        config = AdminGatewayConfig(
            additional_allowed_origins=("http://192.168.1.25:3000",),
        )
        app = create_app(config)
        client = TestClient(app)

        response = client.get("/admin/health", headers={"Origin": "http://192.168.1.25:3000"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://192.168.1.25:3000")

    def test_can_require_origin_header_for_browser_only_access(self) -> None:
        config = AdminGatewayConfig(
            allow_requests_without_origin=False,
        )
        app = create_app(config)
        client = TestClient(app)

        response = client.get("/admin/health")

        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(body["error"]["message"], "origin header required")

    def test_options_preflight_is_not_blocked_by_origin_guard(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.options(
            "/admin/api/v1/dashboard",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        # OPTIONS is handled by CORS middleware; disallowed origin preflight returns 400.
        # This confirms our custom admin origin guard is not incorrectly rejecting OPTIONS as 403.
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
