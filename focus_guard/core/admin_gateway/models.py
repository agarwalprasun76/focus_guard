"""Shared request/response models for admin gateway scaffold."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class ApiError:
    """Standardized API error envelope payload."""

    code: str
    message: str
    details: dict[str, Any] | None = None
    retry_after_seconds: int | None = None


@dataclass
class HealthResponse:
    """Lightweight health response for gateway service."""

    status: str
    service: str
    version: str


class LoginRequest(BaseModel):
    """Login payload for admin authentication."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    """Refresh payload containing existing access token."""

    token: str = Field(..., min_length=1)


class AuthTokenResponse(BaseModel):
    """Response payload returned by login/refresh endpoints."""

    token: str
    expires_at: datetime
    role: str = "admin"


class AuthMeResponse(BaseModel):
    """Identity response payload for authenticated admin."""

    username: str
    role: str = "admin"
    created_at: datetime
