"""Configuration values for the admin gateway scaffold.

Environment overrides (see ``load_admin_gateway_config`` and Day 11 ADR):

* ``FOCUS_GUARD_ADMIN_GATEWAY_HOST`` — bind address for managed/gateway process (default ``127.0.0.1``). Use non-loopback only with explicit firewall discipline; **never** pair with consumer port-forward without ADR review.
* ``FOCUS_GUARD_ADMIN_GATEWAY_PORT`` — listen port (default ``58393``). When changed, default browser CORS origins follow this port.
* ``FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS`` — comma-separated extra ``Origin`` values (e.g. HTTPS tunnel URL serving the admin UI). Required when the SPA is loaded from a hostname not already in the default list.
* ``FOCUS_GUARD_ADMIN_ENFORCE_ORIGIN_CHECKS`` — ``0`` / ``false`` disables origin guard (discouraged).
* ``FOCUS_GUARD_ADMIN_ALLOW_REQUESTS_WITHOUT_ORIGIN`` — ``0`` / ``false`` rejects API calls with no ``Origin`` (stricter; breaks some CLI/curl unless they send a matching origin policy off).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from dataclasses import field
from typing import Mapping, Optional

from focus_guard.core.tab_server_endpoint import resolve_tab_server_base_url

DEFAULT_ADMIN_GATEWAY_HOST = "127.0.0.1"
DEFAULT_ADMIN_GATEWAY_PORT = 58393


def _resolve_default_tab_server_base_url() -> str:
    env_base_url = os.getenv("FOCUS_GUARD_TAB_SERVER_BASE_URL")
    if env_base_url:
        return env_base_url.rstrip("/")

    return resolve_tab_server_base_url()


def _parse_positive_int(raw: str, fallback: int) -> int:
    try:
        v = int(raw.strip())
        return v if v > 0 and v < 65536 else fallback
    except (TypeError, ValueError):
        return fallback


def _env_truthy(value: str | None, default: bool = True) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def browser_origins_for_port(port: int) -> tuple[str, ...]:
    """Origins commonly used when the gateway and Vite dev server are local."""

    return (
        f"http://localhost:{port}",
        f"http://127.0.0.1:{port}",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


def _default_allowed_origins_tuple() -> tuple[str, ...]:
    return browser_origins_for_port(DEFAULT_ADMIN_GATEWAY_PORT)


def load_admin_gateway_config(environ: Mapping[str, str] | None = None) -> "AdminGatewayConfig":
    """Build config from defaults + optional process environment."""

    env: Mapping[str, str] = environ if environ is not None else os.environ

    host = (env.get("FOCUS_GUARD_ADMIN_GATEWAY_HOST") or DEFAULT_ADMIN_GATEWAY_HOST).strip() or DEFAULT_ADMIN_GATEWAY_HOST
    port = _parse_positive_int(
        env.get("FOCUS_GUARD_ADMIN_GATEWAY_PORT") or str(DEFAULT_ADMIN_GATEWAY_PORT),
        DEFAULT_ADMIN_GATEWAY_PORT,
    )

    extra_line = env.get("FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS") or ""
    additions: tuple[str, ...] = tuple(
        p.strip().rstrip("/")
        for p in extra_line.split(",")
        if isinstance(p, str) and p.strip()
    )

    enforce_origin = _env_truthy(env.get("FOCUS_GUARD_ADMIN_ENFORCE_ORIGIN_CHECKS"), True)
    allow_no_origin = _env_truthy(env.get("FOCUS_GUARD_ADMIN_ALLOW_REQUESTS_WITHOUT_ORIGIN"), True)

    return AdminGatewayConfig(
        host=host,
        port=port,
        allowed_origins=browser_origins_for_port(port),
        additional_allowed_origins=additions,
        enforce_origin_checks=enforce_origin,
        allow_requests_without_origin=allow_no_origin,
        tab_server_base_url=_resolve_default_tab_server_base_url(),
    )


@dataclass(frozen=True)
class AdminGatewayConfig:
    """Runtime config for the admin gateway service."""

    host: str = DEFAULT_ADMIN_GATEWAY_HOST
    port: int = DEFAULT_ADMIN_GATEWAY_PORT
    api_prefix: str = "/admin/api/v1"
    allowed_origins: tuple[str, ...] = field(default_factory=_default_allowed_origins_tuple)
    additional_allowed_origins: tuple[str, ...] = ()
    enforce_origin_checks: bool = True
    allow_requests_without_origin: bool = True
    tab_server_base_url: str = field(default_factory=_resolve_default_tab_server_base_url)
    admin_ui_dist_dir: Optional[str] = None
    admin_username: str = "admin"
    auth_token_ttl_seconds: int = 3600
