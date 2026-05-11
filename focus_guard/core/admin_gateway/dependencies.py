"""Dependency helpers for admin gateway scaffold."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, Header

from focus_guard.core.admin_gateway.config import AdminGatewayConfig, load_admin_gateway_config
from focus_guard.core.admin_gateway.error_handling import http_error, translate_service_error
from focus_guard.core.admin_gateway.services.auth_service import AuthService
from focus_guard.core.admin_gateway.services.tab_server_client import TabServerClient

_AUTH_SERVICE: AuthService | None = None


def get_gateway_config() -> AdminGatewayConfig:
    """Return gateway config (defaults + ``FOCUS_GUARD_ADMIN_*`` environment overrides)."""

    return load_admin_gateway_config()


def get_tab_server_client() -> TabServerClient:
    """Create a client for upstream tab-server calls."""

    config = get_gateway_config()
    return TabServerClient(base_url=config.tab_server_base_url)


def get_auth_service() -> AuthService:
    """Return process-wide auth service instance for token state."""

    global _AUTH_SERVICE
    if _AUTH_SERVICE is None:
        _AUTH_SERVICE = AuthService(get_gateway_config())
    return _AUTH_SERVICE


def require_authenticated_admin(
    authorization: Optional[str] = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """Validate bearer token and return identity payload.

    Applied to protected mutation endpoints in P2-03.
    """

    if not authorization or not authorization.lower().startswith("bearer "):
        raise http_error(status_code=401, code="UNAUTHORIZED", message="missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise http_error(status_code=401, code="UNAUTHORIZED", message="missing bearer token")

    try:
        return auth_service.me(token)
    except Exception as exc:
        if hasattr(exc, "status_code") and hasattr(exc, "code") and hasattr(exc, "message"):
            raise translate_service_error(exc) from exc
        raise http_error(status_code=401, code="UNAUTHORIZED", message="invalid token") from exc
