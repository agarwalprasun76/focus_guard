"""Dashboard routes scaffold for admin gateway."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from focus_guard.core.admin_gateway.dependencies import get_tab_server_client
from focus_guard.core.admin_gateway.services.dashboard_service import DashboardService

router = APIRouter(prefix="/admin/api/v1", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(
    device_id: str | None = None,
    tab_server_client=Depends(get_tab_server_client),
) -> dict:
    """Placeholder dashboard aggregation endpoint; implemented in P2-04."""

    service = DashboardService(tab_server_client)
    return service.get_dashboard(device_id=device_id)
