"""Admin gateway router for application activity data."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from focus_guard.core.admin_gateway.dependencies import get_tab_server_client
from focus_guard.core.admin_gateway.error_handling import translate_service_error
from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerClient,
    TabServerRequestError,
    TabServerUnavailableError,
)

router = APIRouter(prefix="/admin/api/v1/activity", tags=["activity"])


@router.get("/apps")
def get_app_usage(
    date: str = Query(default="", description="YYYY-MM-DD, defaults to today"),
    start_date: str = Query(default="", description="Range start YYYY-MM-DD (inclusive)"),
    end_date: str = Query(default="", description="Range end YYYY-MM-DD (inclusive)"),
    limit: int = Query(default=30, ge=1, le=100),
    tab_server_client: TabServerClient = Depends(get_tab_server_client),
) -> dict[str, Any]:
    """Proxy GET /api/activity/apps from the tab server."""
    try:
        params = f"?limit={limit}"
        if start_date and end_date:
            params += f"&start_date={start_date}&end_date={end_date}"
        elif date:
            params += f"&date={date}"
        return tab_server_client.get_json(f"/api/activity/apps{params}")
    except (TabServerUnavailableError, TabServerRequestError) as exc:
        raise translate_service_error(exc) from exc
