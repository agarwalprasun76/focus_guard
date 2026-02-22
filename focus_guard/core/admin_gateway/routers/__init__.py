"""Route registration for admin gateway scaffold."""

from __future__ import annotations

from typing import Any


def include_routers(app: Any) -> None:
    """Attach all router modules to the app instance.

    The app is typed as Any to keep P2-01 scaffold import-light.
    """

    from focus_guard.core.admin_gateway.routers.auth import router as auth_router
    from focus_guard.core.admin_gateway.routers.dashboard import router as dashboard_router
    from focus_guard.core.admin_gateway.routers.devices import router as devices_router
    from focus_guard.core.admin_gateway.routers.exceptions import router as exceptions_router
    from focus_guard.core.admin_gateway.routers.meta import router as meta_router
    from focus_guard.core.admin_gateway.routers.settings import router as settings_router

    app.include_router(auth_router)
    app.include_router(meta_router)
    app.include_router(dashboard_router)
    app.include_router(exceptions_router)
    app.include_router(devices_router)
    app.include_router(settings_router)
