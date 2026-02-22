"""Shared helpers for resolving FocusGuard tab-server endpoint contract."""

from __future__ import annotations

from focus_guard.deployment.config import DeploymentConfig

DEFAULT_TAB_SERVER_HOST = "127.0.0.1"
DEFAULT_TAB_SERVER_PORT = 58392


def resolve_tab_server_endpoint() -> tuple[str, int]:
    """Resolve tab-server host/port from deployment config with safe defaults."""
    try:
        cfg = DeploymentConfig.load()
        host = str(getattr(cfg, "tab_server_host", DEFAULT_TAB_SERVER_HOST) or DEFAULT_TAB_SERVER_HOST)
        port = int(getattr(cfg, "tab_server_port", DEFAULT_TAB_SERVER_PORT) or DEFAULT_TAB_SERVER_PORT)
        return host, port
    except Exception:
        return DEFAULT_TAB_SERVER_HOST, DEFAULT_TAB_SERVER_PORT


def resolve_tab_server_base_url() -> str:
    """Resolve tab-server HTTP base URL from the shared endpoint contract."""
    host, port = resolve_tab_server_endpoint()
    return f"http://{host}:{port}"
