"""Meta/capabilities routes for admin gateway."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from focus_guard.core.admin_gateway.dependencies import get_tab_server_client
from focus_guard.core.admin_gateway.services.tab_server_client import TabServerError

router = APIRouter(prefix="/admin/api/v1", tags=["meta"])


@router.get("/meta")
def get_meta(tab_server_client=Depends(get_tab_server_client)) -> dict:
    """Return gateway capabilities and runtime readiness snapshot."""

    tab_server_state = "offline"
    try:
        health = tab_server_client.get_json("/api/health")
        if isinstance(health, dict) and health:
            tab_server_state = "online"
    except TabServerError:
        tab_server_state = "offline"

    gateway_state = "online"
    enforcement_state = "active" if tab_server_state == "online" else "degraded"

    return {
        "service": "admin_gateway",
        "version": "0.1.0",
        "capabilities": {
            "auth": ["login", "refresh", "logout", "me"],
            "dashboard": True,
            "exceptions": ["create", "list", "revoke"],
            "devices": ["list", "set_enforcement"],
            "origin_protection": True,
            "request_id": True,
        },
        "readiness": {
            "gateway": gateway_state,
            "tab_server": tab_server_state,
            "enforcement": enforcement_state,
        },
    }
