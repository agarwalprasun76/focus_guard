"""Device endpoint service for admin gateway (P2-06)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerClient,
    TabServerRequestError,
    TabServerUnavailableError,
)


@dataclass
class DevicesServiceError(Exception):
    """Typed service error for devices API translation."""

    code: str
    message: str
    status_code: int


class DevicesService:
    """Provides device status and enforcement update operations."""

    def __init__(self, tab_server_client: TabServerClient) -> None:
        self._tab_server_client = tab_server_client

    def list_devices(self) -> dict[str, Any]:
        """Return single-device status payload (list-ready).

        Defensive against malformed tab server responses (BUG-012): never assume
        health/status/enforcement are dicts; coerce types so the frontend always
        receives a valid devices list.
        """
        health: dict[str, Any] = {}
        status: dict[str, Any] = {}
        enforcement: dict[str, Any] = {}

        try:
            raw = self._tab_server_client.get_json("/api/health")
            health = raw if isinstance(raw, dict) else {}
        except (TabServerUnavailableError, TabServerRequestError) as exc:
            raise DevicesServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except Exception as exc:
            raise DevicesServiceError("UPSTREAM_ERROR", str(exc), 502) from exc

        try:
            raw = self._tab_server_client.get_json("/api/status")
            status = raw if isinstance(raw, dict) else {}
        except (TabServerUnavailableError, TabServerRequestError, Exception):
            pass

        try:
            raw = self._tab_server_client.get_json("/api/enforcement_mode")
            enforcement = raw if isinstance(raw, dict) else {}
        except (TabServerUnavailableError, TabServerRequestError, Exception):
            pass

        connected_browsers = 0
        try:
            cb = status.get("connected_browsers")
            if cb is not None:
                connected_browsers = int(cb)
            else:
                browsers = status.get("browsers") if isinstance(status.get("browsers"), list) else []
                connected_browsers = len([b for b in browsers if isinstance(b, dict) and b.get("connected")])
        except (TypeError, ValueError):
            pass

        machine_name = str(health.get("machine_name") or "default-device").strip() or "default-device"
        mode = enforcement.get("enforcement_mode")
        if not isinstance(mode, str) or not mode.strip():
            mode = "enforcing"
        else:
            mode = str(mode).strip().lower()
        if mode not in ("tracking", "advisory", "enforcing"):
            mode = "enforcing"

        device_list = [
            {
                "id": machine_name,
                "name": machine_name,
                "status": "online",
                "enforcement_mode": mode,
                "last_seen": None,
                "browser_status": {
                    "connected_browsers": connected_browsers,
                },
            }
        ]
        return {"devices": device_list}

    def set_enforcement_mode(self, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Proxy enforcement mode update to tab server."""

        mode = str(payload.get("mode") or "").strip().lower()
        password = payload.get("password")

        if mode not in {"tracking", "advisory", "enforcing"}:
            raise DevicesServiceError(
                "VALIDATION_ERROR",
                "mode must be one of tracking|advisory|enforcing",
                400,
            )

        request_payload: dict[str, Any] = {"mode": mode}
        if password is not None:
            request_payload["password"] = password

        try:
            upstream = self._tab_server_client.post_json("/api/enforcement_mode", request_payload)
        except TabServerUnavailableError as exc:
            raise DevicesServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            if exc.status_code in (400, 403):
                raise DevicesServiceError("VALIDATION_ERROR", exc.message, exc.status_code) from exc
            raise DevicesServiceError("UPSTREAM_ERROR", exc.message, 502) from exc

        updated = bool(upstream.get("success", False) or upstream.get("updated", False))
        return {
            "updated": updated,
            "device_id": device_id,
            "mode": upstream.get("enforcement_mode", mode),
        }
