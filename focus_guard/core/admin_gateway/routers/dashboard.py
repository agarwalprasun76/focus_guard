"""Dashboard routes scaffold for admin gateway."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from focus_guard.core.admin_gateway.dependencies import get_tab_server_client
from focus_guard.core.admin_gateway.services.dashboard_service import DashboardService

router = APIRouter(prefix="/admin/api/v1", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(
    device_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    tab_server_client=Depends(get_tab_server_client),
) -> dict:
    """Dashboard aggregation. Optional start_date/end_date (YYYY-MM-DD) filter override/friction data."""

    service = DashboardService(tab_server_client)
    return service.get_dashboard(
        device_id=device_id,
        start_date=start_date,
        end_date=end_date,
    )
