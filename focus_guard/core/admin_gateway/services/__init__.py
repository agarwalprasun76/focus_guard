"""Service layer for admin gateway scaffold."""

from focus_guard.core.admin_gateway.services.auth_service import AuthError, AuthService
from focus_guard.core.admin_gateway.services.dashboard_service import DashboardService
from focus_guard.core.admin_gateway.services.devices_service import DevicesService, DevicesServiceError
from focus_guard.core.admin_gateway.services.exception_service import ExceptionService
from focus_guard.core.admin_gateway.services.tab_server_client import TabServerClient

__all__ = [
    "AuthError",
    "AuthService",
    "DashboardService",
    "DevicesService",
    "DevicesServiceError",
    "ExceptionService",
    "TabServerClient",
]
