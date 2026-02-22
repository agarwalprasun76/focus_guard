"""Tests for P2-09 static SPA serving from /admin."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from focus_guard.core.admin_gateway.app import create_app
from focus_guard.core.admin_gateway.config import AdminGatewayConfig


class TestAdminSpaServing(unittest.TestCase):
    def test_default_app_serves_real_repo_dist_when_present(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        dist_index = repo_root / "admin_ui" / "dist" / "index.html"
        if not dist_index.exists():
            self.skipTest("admin_ui/dist/index.html not present in this environment")

        app = create_app()
        client = TestClient(app)

        root_resp = client.get("/admin")
        self.assertEqual(root_resp.status_code, 200)
        self.assertIn("<html", root_resp.text.lower())

    def test_serves_index_and_asset_with_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dist = Path(temp_dir)
            (dist / "index.html").write_text("<html><body>Admin UI</body></html>", encoding="utf-8")
            (dist / "assets").mkdir(parents=True, exist_ok=True)
            (dist / "assets" / "app.js").write_text("console.log('ok');", encoding="utf-8")

            app = create_app(AdminGatewayConfig(admin_ui_dist_dir=str(dist)))
            client = TestClient(app)

            root_resp = client.get("/admin")
            self.assertEqual(root_resp.status_code, 200)
            self.assertIn("Admin UI", root_resp.text)

            asset_resp = client.get("/admin/assets/app.js")
            self.assertEqual(asset_resp.status_code, 200)
            self.assertIn("console.log", asset_resp.text)

            route_resp = client.get("/admin/exceptions/new")
            self.assertEqual(route_resp.status_code, 200)
            self.assertIn("Admin UI", route_resp.text)

            saved_links_resp = client.get("/admin/saved-links")
            self.assertEqual(saved_links_resp.status_code, 200)
            self.assertIn("Admin UI", saved_links_resp.text)

            login_resp = client.get("/admin/login")
            self.assertEqual(login_resp.status_code, 200)
            self.assertIn("Admin UI", login_resp.text)

    def test_admin_api_routes_not_hijacked_by_spa_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dist = Path(temp_dir)
            (dist / "index.html").write_text("<html>Admin UI</html>", encoding="utf-8")

            app = create_app(AdminGatewayConfig(admin_ui_dist_dir=str(dist)))
            client = TestClient(app)

            resp = client.get("/admin/api/v1/does-not-exist")
            self.assertEqual(resp.status_code, 404)
            body = resp.json()
            self.assertEqual(body["error"]["code"], "NOT_FOUND")

            # /admin/api (without trailing segment) must also remain reserved.
            reserved_api = client.get("/admin/api")
            self.assertEqual(reserved_api.status_code, 404)
            self.assertEqual(reserved_api.json()["error"]["code"], "NOT_FOUND")

            # /admin/health/ should resolve to backend health route behavior (not SPA fallback).
            health_slash = client.get("/admin/health/")
            self.assertEqual(health_slash.status_code, 404)
            self.assertEqual(health_slash.json()["error"]["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
