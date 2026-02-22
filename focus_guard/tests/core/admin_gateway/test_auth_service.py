"""Unit tests for admin gateway AuthService (P2-02)."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from focus_guard.core.admin_gateway.config import AdminGatewayConfig
from focus_guard.core.admin_gateway.services.auth_service import AuthError, AuthService


class _FakeDeploymentConfig:
    def __init__(self, password_hash: str) -> None:
        self.config_password_hash = password_hash


class TestAuthService(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.program_data = Path(self._temp_dir.name)

        self.config = AdminGatewayConfig(
            admin_username="admin",
            auth_token_ttl_seconds=600,
        )

        self.password = "secret123"
        self.password_hash = hashlib.sha256(self.password.encode("utf-8")).hexdigest()

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def _service(self, password_hash: str | None = None) -> AuthService:
        hash_value = self.password_hash if password_hash is None else password_hash

        with patch(
            "focus_guard.core.admin_gateway.services.auth_service.DeploymentConfig.get_config_path",
            return_value=self.program_data / "deployment_config.json",
        ):
            service = AuthService(self.config)

        self._patcher = patch(
            "focus_guard.core.admin_gateway.services.auth_service.DeploymentConfig.load",
            return_value=_FakeDeploymentConfig(hash_value),
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)
        return service

    def test_login_success_returns_token(self) -> None:
        service = self._service()

        result = service.login(username="admin", password=self.password)

        self.assertIn("token", result)
        self.assertEqual(result["role"], "admin")
        self.assertIsNotNone(result["expires_at"])

    def test_login_fails_for_wrong_password(self) -> None:
        service = self._service()

        with self.assertRaises(AuthError) as ctx:
            service.login(username="admin", password="wrong")

        self.assertEqual(ctx.exception.code, "UNAUTHORIZED")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_login_forbidden_when_password_not_configured(self) -> None:
        service = self._service(password_hash="")

        with self.assertRaises(AuthError) as ctx:
            service.login(username="admin", password=self.password)

        self.assertEqual(ctx.exception.code, "FORBIDDEN")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_refresh_rotates_and_revokes_old_token(self) -> None:
        service = self._service()
        login_result = service.login(username="admin", password=self.password)
        old_token = login_result["token"]

        refreshed = service.refresh(old_token)
        new_token = refreshed["token"]

        self.assertNotEqual(old_token, new_token)

        with self.assertRaises(AuthError) as ctx:
            service.me(old_token)

        self.assertEqual(ctx.exception.code, "UNAUTHORIZED")

        me_payload = service.me(new_token)
        self.assertEqual(me_payload["username"], "admin")

    def test_logout_is_idempotent(self) -> None:
        service = self._service()
        login_result = service.login(username="admin", password=self.password)

        self.assertEqual(service.logout(login_result["token"]), {"success": True})
        self.assertEqual(service.logout(login_result["token"]), {"success": True})


if __name__ == "__main__":
    unittest.main()
