"""Settings routes for admin gateway — enforcement, budgets, domain management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from focus_guard.core.admin_gateway.dependencies import get_tab_server_client, require_authenticated_admin
from focus_guard.core.admin_gateway.error_handling import translate_service_error
from focus_guard.core.admin_gateway.services.settings_service import SettingsService, SettingsServiceError

router = APIRouter(prefix="/admin/api/v1/settings", tags=["settings"])


def _svc(tab_server_client) -> SettingsService:
    return SettingsService(tab_server_client)


# ── Enforcement mode ───────────────────────────────────────────────

@router.get("/enforcement")
def get_enforcement(
    tab_server_client=Depends(get_tab_server_client),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).get_enforcement_mode()
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


@router.post("/enforcement")
def set_enforcement(
    payload: dict[str, Any],
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).set_enforcement_mode(
            mode=str(payload.get("mode", "")),
            password=payload.get("password"),
        )
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


# ── Budgets ────────────────────────────────────────────────────────

@router.get("/budgets")
def get_budgets(
    tab_server_client=Depends(get_tab_server_client),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).get_budgets()
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


@router.post("/budgets/master")
def update_master_budget(
    payload: dict[str, Any],
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).update_master_budget(payload)
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


@router.post("/budgets/classification")
def update_classification_budget(
    payload: dict[str, Any],
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).update_classification_budget(payload)
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


@router.get("/extension-status")
def get_extension_status(
    tab_server_client=Depends(get_tab_server_client),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).get_extension_status()
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


# ── Domain management ──────────────────────────────────────────────

@router.get("/domains")
def get_domains(
    tab_server_client=Depends(get_tab_server_client),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).get_domains_overview()
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


@router.post("/domains/category")
def set_domain_category(
    payload: dict[str, Any],
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).set_domain_category(payload)
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


@router.post("/domains/whitelist")
def whitelist_domain(
    payload: dict[str, Any],
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).whitelist_domain(payload)
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


@router.post("/domains/budget")
def set_domain_budget(
    payload: dict[str, Any],
    tab_server_client=Depends(get_tab_server_client),
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    try:
        return _svc(tab_server_client).set_domain_budget(payload)
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


# ── Email configuration ───────────────────────────────────────────

@router.get("/email")
def get_email_config() -> dict[str, Any]:
    try:
        return SettingsService.get_email_config()
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc


@router.post("/email")
def update_email_config(
    payload: dict[str, Any],
    _: dict[str, Any] = Depends(require_authenticated_admin),
) -> dict[str, Any]:
    try:
        return SettingsService.update_email_config(payload)
    except SettingsServiceError as exc:
        raise translate_service_error(exc) from exc
