"""Application bootstrap for FocusGuard admin gateway (P2-01 scaffold)."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.responses import RedirectResponse

from focus_guard.core.admin_gateway.config import AdminGatewayConfig
from focus_guard.core.admin_gateway.error_handling import build_error_envelope
from focus_guard.core.admin_gateway.error_handling import register_error_handlers
from focus_guard.core.admin_gateway.models import HealthResponse
from focus_guard.core.admin_gateway.routers import include_routers


def create_app(config: AdminGatewayConfig | None = None) -> FastAPI:
    """Create and configure the admin gateway app instance."""

    cfg = config or AdminGatewayConfig()

    app = FastAPI(
        title="FocusGuard Admin Gateway",
        version="0.1.0",
        description="Phase 1 admin UX gateway scaffold",
    )

    allowed_origins = tuple(dict.fromkeys(cfg.allowed_origins + cfg.additional_allowed_origins))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def enforce_admin_origin_policy(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        path = request.url.path
        if request.method != "OPTIONS" and cfg.enforce_origin_checks and path.startswith("/admin"):
            origin = request.headers.get("origin")
            if origin:
                if origin not in allowed_origins and not _is_same_origin(origin, request):
                    response = JSONResponse(
                        status_code=403,
                        content=build_error_envelope(
                            code="FORBIDDEN",
                            message="origin not allowed",
                            details={"origin": origin, "request_id": request_id},
                        ),
                    )
                    response.headers["X-Request-ID"] = request_id
                    return response
            elif not cfg.allow_requests_without_origin:
                response = JSONResponse(
                    status_code=403,
                    content=build_error_envelope(
                        code="FORBIDDEN",
                        message="origin header required",
                        details={"request_id": request_id},
                    ),
                )
                response.headers["X-Request-ID"] = request_id
                return response

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    register_error_handlers(app)

    @app.get("/admin/health")
    def health() -> dict[str, str]:
        payload = HealthResponse(status="ok", service="admin_gateway", version="0.1.0")
        return {
            "status": payload.status,
            "service": payload.service,
            "version": payload.version,
        }

    @app.get("/", include_in_schema=False)
    def root_redirect() -> Response:
        return RedirectResponse(url="/admin", status_code=307)

    include_routers(app)

    admin_ui_dir = _resolve_admin_ui_dist_dir(cfg)
    if admin_ui_dir is not None:
        index_file = admin_ui_dir / "index.html"

        @app.get("/admin", include_in_schema=False)
        def serve_admin_ui_root() -> Response:
            return FileResponse(index_file)

        @app.get("/admin/{ui_path:path}", include_in_schema=False)
        def serve_admin_ui_path(ui_path: str) -> Response:
            # Avoid hijacking API/health routes when frontend path fallback is active.
            if _is_reserved_admin_path(ui_path):
                return JSONResponse(
                    status_code=404,
                    content=build_error_envelope(code="NOT_FOUND", message="Not found"),
                )

            requested = _safe_resolve(admin_ui_dir, ui_path)
            if requested is not None and requested.is_file():
                return FileResponse(requested)
            return FileResponse(index_file)

    return app


def _resolve_admin_ui_dist_dir(cfg: AdminGatewayConfig) -> Path | None:
    configured = cfg.admin_ui_dist_dir
    if configured:
        candidate = Path(configured).expanduser().resolve()
        index_file = candidate / "index.html"
        if candidate.is_dir() and index_file.is_file():
            return candidate
        return None

    repo_root = Path(__file__).resolve().parents[3]
    default_candidates = [
        repo_root / "admin_ui" / "dist",
        repo_root / "focus_guard" / "admin_ui" / "dist",
    ]

    # PyInstaller onefile runtime: bundled data is extracted under sys._MEIPASS.
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            meipass_root = Path(meipass).resolve()
            default_candidates = [
                meipass_root / "admin_ui" / "dist",
                meipass_root / "focus_guard" / "admin_ui" / "dist",
                *default_candidates,
            ]

        executable_dir = Path(sys.executable).resolve().parent
        default_candidates.extend(
            [
                executable_dir / "admin_ui" / "dist",
                executable_dir / "focus_guard" / "admin_ui" / "dist",
            ]
        )

    for candidate in default_candidates:
        index_file = candidate / "index.html"
        if candidate.is_dir() and index_file.is_file():
            return candidate
    return None


def _safe_resolve(base_dir: Path, relative_path: str) -> Path | None:
    candidate = (base_dir / relative_path).resolve()
    try:
        candidate.relative_to(base_dir)
    except ValueError:
        return None
    return candidate


def _is_reserved_admin_path(ui_path: str) -> bool:
    normalized = ui_path.strip("/")
    return normalized == "api" or normalized.startswith("api/") or normalized == "health"


def _is_same_origin(origin: str, request: Request) -> bool:
    request_origin = f"{request.url.scheme}://{request.url.netloc}"
    return origin.rstrip("/") == request_origin.rstrip("/")
