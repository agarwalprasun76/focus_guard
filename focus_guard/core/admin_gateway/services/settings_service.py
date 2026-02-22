"""Settings service for admin gateway — proxies configuration endpoints to tab server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerClient,
    TabServerRequestError,
    TabServerUnavailableError,
)


@dataclass
class SettingsServiceError(Exception):
    code: str
    message: str
    status_code: int


class SettingsService:
    """Read/write configuration via tab server API."""

    def __init__(self, tab_server_client: TabServerClient) -> None:
        self._ts = tab_server_client

    # ── Enforcement mode ───────────────────────────────────────────

    def get_enforcement_mode(self) -> dict[str, Any]:
        try:
            return self._ts.get_json("/api/enforcement_mode")
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            raise SettingsServiceError("UPSTREAM_ERROR", exc.message, 502) from exc

    def set_enforcement_mode(self, mode: str, password: str | None = None) -> dict[str, Any]:
        if mode not in {"tracking", "advisory", "enforcing"}:
            raise SettingsServiceError(
                "VALIDATION_ERROR",
                "mode must be one of tracking|advisory|enforcing",
                400,
            )
        payload: dict[str, Any] = {"mode": mode}
        if password is not None:
            payload["password"] = password
        try:
            result = self._ts.post_json("/api/enforcement_mode", payload)
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            code = "VALIDATION_ERROR" if exc.status_code in (400, 403) else "UPSTREAM_ERROR"
            raise SettingsServiceError(code, exc.message, exc.status_code) from exc
        return {
            "updated": bool(result.get("success") or result.get("updated")),
            "mode": result.get("enforcement_mode", mode),
        }

    # ── Budgets ────────────────────────────────────────────────────

    def get_budgets(self) -> dict[str, Any]:
        try:
            budgets = self._ts.get_json("/api/domains/budgets")
            distraction = self._ts.get_json("/api/distraction/budget")
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            raise SettingsServiceError("UPSTREAM_ERROR", exc.message, 502) from exc
        return {**budgets, "distraction": distraction}

    def update_master_budget(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._ts.post_json("/api/domains/budgets/master", payload)
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            code = "VALIDATION_ERROR" if exc.status_code == 400 else "UPSTREAM_ERROR"
            raise SettingsServiceError(code, exc.message, exc.status_code) from exc

    def update_classification_budget(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._ts.post_json("/api/domains/budgets/classification", payload)
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            code = "VALIDATION_ERROR" if exc.status_code == 400 else "UPSTREAM_ERROR"
            raise SettingsServiceError(code, exc.message, exc.status_code) from exc

    # ── Domain management ──────────────────────────────────────────

    def get_domains_overview(self) -> dict[str, Any]:
        try:
            return self._ts.get_json("/api/domains/overview")
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            raise SettingsServiceError("UPSTREAM_ERROR", exc.message, 502) from exc

    def set_domain_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._ts.post_json("/api/domains/category", payload)
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            code = "VALIDATION_ERROR" if exc.status_code == 400 else "UPSTREAM_ERROR"
            raise SettingsServiceError(code, exc.message, exc.status_code) from exc

    def whitelist_domain(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._ts.post_json("/api/domains/whitelist", payload)
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            code = "VALIDATION_ERROR" if exc.status_code == 400 else "UPSTREAM_ERROR"
            raise SettingsServiceError(code, exc.message, exc.status_code) from exc

    def set_domain_budget(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._ts.post_json("/api/domains/budgets/domain", payload)
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            code = "VALIDATION_ERROR" if exc.status_code == 400 else "UPSTREAM_ERROR"
            raise SettingsServiceError(code, exc.message, exc.status_code) from exc
