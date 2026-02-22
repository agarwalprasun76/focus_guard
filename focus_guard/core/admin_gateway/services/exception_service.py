"""Exception/override orchestration scaffold for admin gateway."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerClient,
    TabServerRequestError,
    TabServerUnavailableError,
)


@dataclass
class ExceptionServiceError(Exception):
    """Typed service error for API layer translation."""

    code: str
    message: str
    status_code: int


class ExceptionService:
    """Handles exception create/list/revoke operations."""

    def __init__(self, tab_server_client: TabServerClient) -> None:
        self._tab_server_client = tab_server_client

    def create_exception(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create exception/rule action by mapping type to tab-server endpoints."""

        domain = str(payload.get("domain") or "").strip().lower()
        action_type = str(payload.get("type") or "").strip().lower()
        reason = str(payload.get("reason") or "").strip()
        emergency = bool(payload.get("emergency", False))

        if not domain:
            raise ExceptionServiceError("VALIDATION_ERROR", "domain is required", 400)

        if action_type not in {"temporary", "permanent", "budgeted", "block"}:
            raise ExceptionServiceError("VALIDATION_ERROR", "type must be temporary|permanent|budgeted|block", 400)

        try:
            if action_type == "temporary":
                duration = int(payload.get("duration_seconds") or 0)
                if duration <= 0:
                    raise ExceptionServiceError("VALIDATION_ERROR", "duration_seconds must be > 0", 400)

                request_reason = reason
                if emergency and request_reason and not request_reason.startswith("EMERGENCY:"):
                    request_reason = f"EMERGENCY: {request_reason}"

                upstream = self._tab_server_client.post_json(
                    "/api/override",
                    {
                        "domain": domain,
                        "duration": duration,
                        "request_reason": request_reason,
                    },
                )

                override = upstream.get("override", {}) if isinstance(upstream, dict) else {}
                override_id = upstream.get("override_id") or override.get("id") or ""
                return {
                    "id": override_id,
                    "status": "active" if upstream.get("granted", False) else "denied",
                    "type": action_type,
                    "domain": domain,
                    "expires_at": self._to_iso_utc(override.get("start_time"), override.get("duration_seconds")),
                    "audit_event_id": None,
                    "message": upstream.get("message"),
                }

            if action_type == "permanent":
                self._tab_server_client.post_json(
                    "/api/domains/whitelist",
                    {
                        "domain": domain,
                        "action": "add",
                    },
                )
                return {
                    "id": f"perm_{domain}",
                    "status": "active",
                    "type": action_type,
                    "domain": domain,
                    "expires_at": None,
                    "audit_event_id": None,
                }

            if action_type == "budgeted":
                budget_seconds = int(payload.get("budget_seconds_per_day") or -1)
                if budget_seconds < 0:
                    raise ExceptionServiceError("VALIDATION_ERROR", "budget_seconds_per_day must be >= 0", 400)

                self._tab_server_client.post_json(
                    "/api/domains/budgets/domain",
                    {
                        "domain": domain,
                        "max_cumulative_time_seconds": budget_seconds,
                    },
                )
                return {
                    "id": f"budget_{domain}",
                    "status": "active",
                    "type": action_type,
                    "domain": domain,
                    "expires_at": None,
                    "audit_event_id": None,
                }

            # action_type == "block"
            self._tab_server_client.post_json(
                "/api/should_block/rules",
                {
                    "domain": domain,
                    "reason": reason or "blocked by admin",
                },
            )
            return {
                "id": f"block_{domain}",
                "status": "active",
                "type": action_type,
                "domain": domain,
                "expires_at": None,
                "audit_event_id": None,
            }
        except ExceptionServiceError:
            raise
        except TabServerUnavailableError as exc:
            raise ExceptionServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            if exc.status_code in (400, 404):
                raise ExceptionServiceError("VALIDATION_ERROR", exc.message, 400) from exc
            raise ExceptionServiceError("UPSTREAM_ERROR", exc.message, 502) from exc

    def revoke_exception(self, exception_id: str, device_id: str | None = None) -> dict[str, Any]:
        """Revoke active exception by ID (idempotent)."""

        try:
            domain = self._resolve_domain_for_exception_id(exception_id)
            if not domain:
                return {"revoked": True, "id": exception_id}

            _ = device_id  # reserved for future multi-device use
            self._tab_server_client.post_json("/api/override/revoke", {"domain": domain})
            return {"revoked": True, "id": exception_id}
        except TabServerUnavailableError as exc:
            raise ExceptionServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            if exc.status_code in (400, 404):
                return {"revoked": True, "id": exception_id}
            raise ExceptionServiceError("UPSTREAM_ERROR", exc.message, 502) from exc

    def list_exceptions(
        self,
        device_id: str | None = None,
        status: str = "all",
        domain: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List active/history exceptions by combining active overrides and override log."""

        try:
            active_resp = self._tab_server_client.get_json("/api/override/active")
            log_resp = self._tab_server_client.get_json("/api/override/log", params={"limit": 100})
        except TabServerUnavailableError as exc:
            raise ExceptionServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            raise ExceptionServiceError("UPSTREAM_ERROR", exc.message, 502) from exc

        active_overrides = active_resp.get("overrides", []) if isinstance(active_resp, dict) else []
        log_entries = log_resp.get("log", []) if isinstance(log_resp, dict) else []

        exceptions: list[dict[str, Any]] = []

        for item in active_overrides:
            start_ts = item.get("start_time")
            duration = item.get("duration_seconds")
            expires_at = self._to_iso_utc(start_ts, duration)
            remaining = 0
            if isinstance(start_ts, (int, float)) and isinstance(duration, (int, float)):
                remaining = max(0, int((start_ts + duration) - datetime.now(timezone.utc).timestamp()))

            exceptions.append(
                {
                    "id": item.get("id") or "",
                    "domain": item.get("domain") or "",
                    "type": "temporary",
                    "status": "active",
                    "created_at": self._timestamp_to_iso(item.get("start_time")),
                    "expires_at": expires_at,
                    "remaining_seconds": remaining,
                    "reason": item.get("block_reason"),
                    "emergency": str(item.get("request_reason", "")).upper().startswith("EMERGENCY:"),
                }
            )

        # Include historical entries as non-active records.
        for entry in log_entries:
            event_type = str(entry.get("event_type") or "").lower()
            if event_type not in {"granted", "revoked", "expired"}:
                continue

            mapped_status = {
                "granted": "expired",
                "revoked": "revoked",
                "expired": "expired",
            }.get(event_type, "expired")
            details = entry.get("details") or {}

            exceptions.append(
                {
                    "id": entry.get("override_id") or "",
                    "domain": entry.get("domain") or "",
                    "type": "temporary",
                    "status": mapped_status,
                    "created_at": self._timestamp_to_iso(entry.get("timestamp")),
                    "expires_at": details.get("expires_at"),
                    "remaining_seconds": int(details.get("remaining_seconds", 0) or 0),
                    "reason": details.get("reason") or details.get("request_reason"),
                    "emergency": str(details.get("request_reason", "")).upper().startswith("EMERGENCY:"),
                }
            )

        # Deduplicate by (id, status, domain) while preserving order.
        seen: set[tuple[str, str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for item in exceptions:
            key = (item.get("id") or "", item.get("status") or "", item.get("domain") or "")
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        normalized_status = (status or "all").lower()
        if normalized_status in {"active", "expired", "revoked"}:
            deduped = [item for item in deduped if item.get("status") == normalized_status]

        normalized_domain = str(domain or "").strip().lower()
        if normalized_domain:
            deduped = [item for item in deduped if str(item.get("domain") or "").lower() == normalized_domain]

        total = len(deduped)
        limit = max(1, min(int(limit or 50), 200))
        offset = max(0, int(offset or 0))
        paged = deduped[offset : offset + limit]

        if device_id:
            _ = device_id  # reserved for future multi-device filtering

        return {
            "exceptions": paged,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _resolve_domain_for_exception_id(self, exception_id: str) -> str | None:
        if not exception_id:
            return None

        active_resp = self._tab_server_client.get_json("/api/override/active")
        for item in active_resp.get("overrides", []):
            if item.get("id") == exception_id:
                domain = str(item.get("domain") or "").strip().lower()
                if domain:
                    return domain

        log_resp = self._tab_server_client.get_json("/api/override/log", params={"limit": 100})
        for entry in reversed(log_resp.get("log", [])):
            if entry.get("override_id") == exception_id:
                domain = str(entry.get("domain") or "").strip().lower()
                if domain:
                    return domain

        return None

    @staticmethod
    def _timestamp_to_iso(value: Any) -> str | None:
        if not isinstance(value, (int, float)):
            return None
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")

    def _to_iso_utc(self, start_time: Any, duration_seconds: Any) -> str | None:
        if not isinstance(start_time, (int, float)) or not isinstance(duration_seconds, (int, float)):
            return None
        expiry_ts = float(start_time) + float(duration_seconds)
        return self._timestamp_to_iso(expiry_ts)
