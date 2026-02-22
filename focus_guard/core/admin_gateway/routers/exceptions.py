"""Exception routes scaffold for admin gateway."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from focus_guard.core.admin_gateway.dependencies import (
    get_tab_server_client,
    require_authenticated_admin,
)
from focus_guard.core.admin_gateway.error_handling import translate_service_error
from focus_guard.core.admin_gateway.services.exception_service import ExceptionService, ExceptionServiceError

router = APIRouter(prefix="/admin/api/v1", tags=["exceptions"])


@router.post("/exceptions")
def create_exception(
    payload: dict[str, Any],
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    """Create exception/rule by proxying to tab-server endpoints."""

    service = ExceptionService(tab_server_client)
    try:
        return service.create_exception(payload)
    except ExceptionServiceError as exc:
        raise translate_service_error(exc) from exc


@router.get("/exceptions")
def list_exceptions(
    device_id: str | None = None,
    status: str = "all",
    domain: str | None = None,
    limit: int = 50,
    offset: int = 0,
    tab_server_client=Depends(get_tab_server_client),
) -> dict[str, Any]:
    """List exceptions/overrides from active and historical tab-server data."""

    service = ExceptionService(tab_server_client)
    try:
        return service.list_exceptions(
            device_id=device_id,
            status=status,
            domain=domain,
            limit=limit,
            offset=offset,
        )
    except ExceptionServiceError as exc:
        raise translate_service_error(exc) from exc


@router.delete("/exceptions/{exception_id}")
def revoke_exception(
    exception_id: str,
    device_id: str | None = None,
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    """Revoke exception by ID (idempotent)."""

    service = ExceptionService(tab_server_client)
    try:
        return service.revoke_exception(exception_id=exception_id, device_id=device_id)
    except ExceptionServiceError as exc:
        raise translate_service_error(exc) from exc
