"""Device routes scaffold for admin gateway."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from focus_guard.core.admin_gateway.dependencies import get_tab_server_client, require_authenticated_admin
from focus_guard.core.admin_gateway.error_handling import translate_service_error
from focus_guard.core.admin_gateway.services.devices_service import DevicesService, DevicesServiceError

router = APIRouter(prefix="/admin/api/v1", tags=["devices"])


@router.get("/devices")
def list_devices(
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    """Return device status list (single-device MVP)."""

    service = DevicesService(tab_server_client)
    try:
        return service.list_devices()
    except DevicesServiceError as exc:
        raise translate_service_error(exc) from exc


@router.put("/devices/{device_id}/enforcement")
def set_enforcement_mode(
    device_id: str,
    payload: dict[str, Any],
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    """Set enforcement mode for a device."""

    service = DevicesService(tab_server_client)
    try:
        return service.set_enforcement_mode(device_id=device_id, payload=payload)
    except DevicesServiceError as exc:
        raise translate_service_error(exc) from exc
