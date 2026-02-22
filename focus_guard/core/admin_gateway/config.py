"""Configuration values for the admin gateway scaffold."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dataclasses import field
from typing import Optional

from focus_guard.core.tab_server_endpoint import resolve_tab_server_base_url


def _resolve_default_tab_server_base_url() -> str:
    env_base_url = os.getenv("FOCUS_GUARD_TAB_SERVER_BASE_URL")
    if env_base_url:
        return env_base_url.rstrip("/")

    return resolve_tab_server_base_url()


@dataclass(frozen=True)
class AdminGatewayConfig:
    """Runtime config for the admin gateway service."""

    host: str = "127.0.0.1"
    port: int = 58393
    api_prefix: str = "/admin/api/v1"
    allowed_origins: tuple[str, ...] = (
        "http://localhost:58393",
        "http://127.0.0.1:58393",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    additional_allowed_origins: tuple[str, ...] = ()
    enforce_origin_checks: bool = True
    allow_requests_without_origin: bool = True
    tab_server_base_url: str = field(default_factory=_resolve_default_tab_server_base_url)
    admin_ui_dist_dir: Optional[str] = None
    admin_username: str = "admin"
    auth_token_ttl_seconds: int = 3600
