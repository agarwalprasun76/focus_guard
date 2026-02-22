"""Structured API error model and translation helpers for admin gateway."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from focus_guard.core.admin_gateway.models import ApiError


_STATUS_TO_CODE = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    500: "INTERNAL_ERROR",
    502: "UPSTREAM_ERROR",
}


def build_error_envelope(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retry_after_seconds: int | None = None,
) -> dict[str, Any]:
    """Build API-contract-compliant error envelope."""

    payload = asdict(
        ApiError(
            code=code,
            message=message,
            details=details,
            retry_after_seconds=retry_after_seconds,
        )
    )
    payload = {k: v for k, v in payload.items() if v is not None}
    return {"error": payload}


def http_error(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retry_after_seconds: int | None = None,
) -> HTTPException:
    """Create HTTPException with standardized error envelope."""

    return HTTPException(
        status_code=status_code,
        detail=build_error_envelope(
            code=code,
            message=message,
            details=details,
            retry_after_seconds=retry_after_seconds,
        ),
    )


def translate_service_error(exc: Exception, fallback_code: str = "INTERNAL_ERROR") -> HTTPException:
    """Translate typed service errors to standardized HTTPException."""

    if hasattr(exc, "status_code") and hasattr(exc, "code") and hasattr(exc, "message"):
        return http_error(
            status_code=int(getattr(exc, "status_code")),
            code=str(getattr(exc, "code")),
            message=str(getattr(exc, "message")),
        )

    return http_error(
        status_code=500,
        code=fallback_code,
        message=str(exc) or "Unexpected internal error",
    )


def register_error_handlers(app) -> None:
    """Register centralized exception handlers for structured errors."""

    @app.exception_handler(HTTPException)
    async def _handle_http_exception(_: Request, exc: HTTPException) -> Response:
        if isinstance(exc.detail, dict):
            if "error" in exc.detail:
                payload = exc.detail
            elif "code" in exc.detail and "message" in exc.detail:
                payload = build_error_envelope(
                    code=str(exc.detail.get("code")),
                    message=str(exc.detail.get("message")),
                    details=exc.detail.get("details"),
                    retry_after_seconds=exc.detail.get("retry_after_seconds"),
                )
            else:
                payload = build_error_envelope(
                    code=_STATUS_TO_CODE.get(exc.status_code, "INTERNAL_ERROR"),
                    message=str(exc.detail),
                )
        else:
            payload = build_error_envelope(
                code=_STATUS_TO_CODE.get(exc.status_code, "INTERNAL_ERROR"),
                message=str(exc.detail),
            )

        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> Response:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=build_error_envelope(
                code="VALIDATION_ERROR",
                message="Invalid request payload",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(_: Request, __: Exception) -> Response:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=build_error_envelope(
                code="INTERNAL_ERROR",
                message="Internal server error",
            ),
        )
