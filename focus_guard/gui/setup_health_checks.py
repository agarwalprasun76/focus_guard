"""Local setup health checks shared by the first-run checklist dialog (post-start)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

from focus_guard.core.admin_gateway.config import load_admin_gateway_config
from focus_guard.core.tab_server_endpoint import resolve_tab_server_base_url

logger = logging.getLogger(__name__)


def _loopback_health_host(cfg_host: str) -> str:
    """URL host for probing a server bound to all interfaces."""

    if cfg_host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return cfg_host


def admin_dashboard_http_url() -> str:
    cfg = load_admin_gateway_config()
    return f"http://{_loopback_health_host(cfg.host)}:{cfg.port}/admin"


def admin_health_http_url() -> str:
    cfg = load_admin_gateway_config()
    return f"http://{_loopback_health_host(cfg.host)}:{cfg.port}/admin/health"


def _check_http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as resp:  # noqa: S310 localhost diagnostics
            return 200 <= int(resp.status) < 300
    except (URLError, OSError, ValueError):
        return False


def _fetch_json(url: str, timeout: float = 2.0) -> Optional[dict]:
    try:
        with urlopen(url, timeout=timeout) as resp:  # noqa: S310 localhost diagnostics
            if not (200 <= int(resp.status) < 300):
                return None
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (URLError, OSError, ValueError, json.JSONDecodeError):
        return None


def _deployment_has_admin_password() -> bool:
    try:
        from focus_guard.deployment.config import DeploymentConfig

        cfg = DeploymentConfig.load()
        return bool((cfg.config_password_hash or "").strip())
    except Exception:
        logger.debug("Could not read deployment config for admin password hint", exc_info=True)
        return False


@dataclass(frozen=True)
class SetupHealthResult:
    """Result of validating local readiness."""

    level: str  # ready | warn | not_ready
    html_summary: str
    tab_health_ok: bool
    admin_health_ok: bool


def evaluate_setup_health(
    *,
    extension_install_acknowledged: Optional[bool] = None,
    admin_password_enabled: Optional[bool] = None,
) -> SetupHealthResult:
    """Probe tab server + admin gateway + extension status.

    *extension_install_acknowledged* ``None``: do not fail on unchecked install box (post-start flow).
    *admin_password_enabled* ``None``: read from DeploymentConfig.
    """

    if admin_password_enabled is None:
        admin_password_enabled = _deployment_has_admin_password()

    extension_ok = True
    if extension_install_acknowledged is not None:
        extension_ok = extension_install_acknowledged

    password_enabled = admin_password_enabled

    tab_base = resolve_tab_server_base_url()
    tab_health_ok = _check_http_ok(f"{tab_base}/api/health")
    admin_health_ok = _check_http_ok(admin_health_http_url())

    status_payload = None
    auth_payload = None
    if tab_health_ok:
        status_payload = _fetch_json(f"{tab_base}/api/status")
        auth_payload = _fetch_json(f"{tab_base}/api/auth/status")

    extension_connected = False
    if isinstance(status_payload, dict):
        for b in status_payload.get("connected_browsers") or []:
            if isinstance(b, dict) and b.get("connected"):
                extension_connected = True
                break

    issues = []
    warnings = []

    if extension_install_acknowledged is not None and not extension_install_acknowledged:
        issues.append("Extension install was not confirmed in the setup wizard.")

    if not password_enabled:
        warnings.append("Admin password is not set on this deployment yet (dashboard may be weaker).")

    if not tab_health_ok:
        warnings.append("Tab server health endpoint did not respond.")
    if not admin_health_ok:
        warnings.append(
            "Admin gateway health endpoint did not respond "
            "(Open Guardian Dashboard below may not load until services are listening)."
        )
    if tab_health_ok and isinstance(auth_payload, dict) and not auth_payload.get("token_exists"):
        warnings.append(
            "Tab server API auth token missing or unreadable — extensions may fail to authenticate."
        )
    if extension_ok and tab_health_ok and not extension_connected:
        warnings.append(
            "No browser appears connected yet. Install/enable the extension and open any tab "
            "(then Run connection check again)."
        )

    if issues:
        level = "not_ready"
        color = "#cc0000"
        title = "Issues to fix before relying on blocking"
    elif warnings:
        level = "warn"
        color = "#9c6500"
        title = "Working with notices"
    else:
        level = "ready"
        color = "#008800"
        title = "Looks good locally"

    lines = [f'<span style="color:{color}; font-weight:bold;">{title}</span>']
    for x in issues:
        lines.append(f"• {x}")
    for x in warnings:
        lines.append(f"• {x}")
    html = "<br>".join(lines)
    return SetupHealthResult(
        level=level,
        html_summary=html,
        tab_health_ok=tab_health_ok,
        admin_health_ok=admin_health_ok,
    )
