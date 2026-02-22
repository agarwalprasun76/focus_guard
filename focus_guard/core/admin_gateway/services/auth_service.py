"""Authentication service for admin gateway Phase 1."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from focus_guard.core.admin_gateway.config import AdminGatewayConfig
from focus_guard.deployment.config import DeploymentConfig


class AuthError(Exception):
    """Typed auth error with HTTP and API metadata."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass
class TokenPayload:
    """Decoded auth token payload."""

    sub: str
    role: str
    iat: int
    exp: int
    jti: str


class AuthService:
    """Login/refresh/logout/me flow for Phase 1.

    Uses the existing DeploymentConfig `config_password_hash` as the admin password source.
    """

    def __init__(self, config: AdminGatewayConfig) -> None:
        self._config = config
        self._secret = self._load_or_create_secret()
        self._revoked_jtis: set[str] = set()
        self._created_at = datetime.now(timezone.utc)

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Validate credentials and issue an access token."""

        if not username or not password:
            raise AuthError("VALIDATION_ERROR", "username and password are required", 400)

        if username != self._config.admin_username:
            raise AuthError("UNAUTHORIZED", "invalid credentials", 401)

        deployment_config = DeploymentConfig.load()
        if not deployment_config.config_password_hash:
            raise AuthError(
                "FORBIDDEN",
                "admin password is not configured; set it with `focus-guard set-password`",
                403,
            )

        provided_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(provided_hash, deployment_config.config_password_hash):
            raise AuthError("UNAUTHORIZED", "invalid credentials", 401)

        token, expires_at = self._issue_token(username=username, role="admin")
        return {
            "token": token,
            "expires_at": expires_at,
            "role": "admin",
        }

    def refresh(self, token: str) -> dict[str, Any]:
        """Rotate token after validating current token."""

        payload = self._decode_token(token)
        if payload.jti in self._revoked_jtis:
            raise AuthError("UNAUTHORIZED", "token has been revoked", 401)

        self._revoked_jtis.add(payload.jti)
        new_token, expires_at = self._issue_token(username=payload.sub, role=payload.role)
        return {
            "token": new_token,
            "expires_at": expires_at,
            "role": payload.role,
        }

    def logout(self, token: Optional[str]) -> dict[str, bool]:
        """Revoke active token if provided; always succeed for idempotency."""

        if token:
            try:
                payload = self._decode_token(token)
                self._revoked_jtis.add(payload.jti)
            except AuthError:
                # Logout stays idempotent even for invalid/expired tokens.
                pass
        return {"success": True}

    def me(self, token: str) -> dict[str, Any]:
        """Return identity for current token."""

        payload = self._decode_token(token)
        if payload.jti in self._revoked_jtis:
            raise AuthError("UNAUTHORIZED", "token has been revoked", 401)

        return {
            "username": payload.sub,
            "role": payload.role,
            "created_at": self._created_at,
        }

    def _issue_token(self, username: str, role: str) -> tuple[str, datetime]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._config.auth_token_ttl_seconds)
        payload = {
            "sub": username,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": secrets.token_hex(16),
        }
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii").rstrip("=")
        signature = hmac.new(self._secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        token = f"{payload_b64}.{signature}"
        return token, expires_at

    def _decode_token(self, token: str) -> TokenPayload:
        if not token:
            raise AuthError("UNAUTHORIZED", "token is required", 401)

        if "." not in token:
            raise AuthError("UNAUTHORIZED", "invalid token format", 401)

        payload_b64, provided_sig = token.rsplit(".", 1)
        expected_sig = hmac.new(self._secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise AuthError("UNAUTHORIZED", "invalid token signature", 401)

        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        try:
            payload_raw = base64.urlsafe_b64decode(padded.encode("ascii"))
            payload_dict = json.loads(payload_raw.decode("utf-8"))
        except Exception as exc:
            raise AuthError("UNAUTHORIZED", "invalid token payload", 401) from exc

        required_fields = {"sub", "role", "iat", "exp", "jti"}
        if not required_fields.issubset(payload_dict):
            raise AuthError("UNAUTHORIZED", "invalid token payload", 401)

        now_ts = int(datetime.now(timezone.utc).timestamp())
        if int(payload_dict["exp"]) < now_ts:
            raise AuthError("UNAUTHORIZED", "token has expired", 401)

        return TokenPayload(
            sub=str(payload_dict["sub"]),
            role=str(payload_dict["role"]),
            iat=int(payload_dict["iat"]),
            exp=int(payload_dict["exp"]),
            jti=str(payload_dict["jti"]),
        )

    def _load_or_create_secret(self) -> bytes:
        program_data = Path(DeploymentConfig.get_config_path()).parent
        secret_path = program_data / "admin_gateway_secret.key"
        secret_path.parent.mkdir(parents=True, exist_ok=True)

        if secret_path.exists():
            try:
                value = secret_path.read_text(encoding="utf-8").strip()
                if value:
                    return value.encode("utf-8")
            except Exception:
                pass

        secret = secrets.token_urlsafe(48)
        secret_path.write_text(secret, encoding="utf-8")
        return secret.encode("utf-8")
