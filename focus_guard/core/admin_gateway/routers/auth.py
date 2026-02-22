"""Auth routes scaffold for admin gateway."""

from __future__ import annotations

from datetime import timezone

from typing import Optional

try:
    from fastapi import APIRouter, Depends, Header
except ImportError as exc:  # pragma: no cover - scaffold import guard
    raise ImportError(
        "FastAPI is required for admin gateway routes. Install fastapi to run admin gateway."
    ) from exc

from focus_guard.core.admin_gateway.dependencies import get_auth_service
from focus_guard.core.admin_gateway.error_handling import http_error, translate_service_error
from focus_guard.core.admin_gateway.models import (
    AuthMeResponse,
    AuthTokenResponse,
    LoginRequest,
    RefreshRequest,
)
from focus_guard.core.admin_gateway.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/admin/api/v1/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> AuthTokenResponse:
    """Authenticate admin and return access token."""

    try:
        result = auth_service.login(username=payload.username, password=payload.password)
        return AuthTokenResponse(**result)
    except AuthError as exc:
        raise translate_service_error(exc) from exc


@router.post("/refresh")
def refresh(payload: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)) -> AuthTokenResponse:
    """Refresh access token."""

    try:
        result = auth_service.refresh(payload.token)
        return AuthTokenResponse(**result)
    except AuthError as exc:
        raise translate_service_error(exc) from exc


@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, bool]:
    """Logout current token; idempotent."""

    token = _extract_bearer_token(authorization)
    return auth_service.logout(token)


@router.get("/me")
def me(
    authorization: Optional[str] = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthMeResponse:
    """Return identity details for current token."""

    token = _extract_bearer_token(authorization)
    if not token:
        raise http_error(status_code=401, code="UNAUTHORIZED", message="missing bearer token")

    try:
        result = auth_service.me(token)
        created_at = result["created_at"].astimezone(timezone.utc)
        return AuthMeResponse(username=result["username"], role=result["role"], created_at=created_at)
    except AuthError as exc:
        raise translate_service_error(exc) from exc


def _extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    """Extract bearer token from Authorization header."""

    if not authorization_header:
        return None

    if not authorization_header.lower().startswith("bearer "):
        return None

    return authorization_header.split(" ", 1)[1].strip() or None
