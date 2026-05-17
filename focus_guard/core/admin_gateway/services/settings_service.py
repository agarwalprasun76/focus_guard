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

    # Default categories shown even when no budgets are configured
    _DEFAULT_CATEGORIES = [
        "ENTERTAINMENT:DISTRACTION",
        "SOCIAL_MEDIA:DISTRACTION",
        "GAMING:DISTRACTION",
        "NEWS:DISTRACTION",
        "SHOPPING:DISTRACTION",
    ]

    def get_budgets(self) -> dict[str, Any]:
        try:
            budgets = self._ts.get_json("/api/domains/budgets")
            distraction = self._ts.get_json("/api/distraction/budget")
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            raise SettingsServiceError("UPSTREAM_ERROR", exc.message, 502) from exc

        # Transform classification_budgets: add daily_seconds from max_cumulative_time_seconds
        raw_cb = budgets.get("classification_budgets", {})
        classification_budgets: dict[str, Any] = {}
        for key, val in raw_cb.items():
            entry = dict(val) if isinstance(val, dict) else {}
            entry["daily_seconds"] = entry.get("max_cumulative_time_seconds", 0)
            classification_budgets[key] = entry

        # Ensure default categories are always present
        for cat_key in self._DEFAULT_CATEGORIES:
            if cat_key not in classification_budgets:
                classification_budgets[cat_key] = {"daily_seconds": 0, "max_cumulative_time_seconds": 0}

        budgets["classification_budgets"] = classification_budgets

        # Transform master_budget: add daily_seconds
        master = budgets.get("master_budget", {})
        if "daily_seconds" not in master:
            master["daily_seconds"] = master.get("max_total_distraction_seconds", 3600)
        budgets["master_budget"] = master

        return {**budgets, "distraction": distraction}

    @staticmethod
    def _normalize_master_budget_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """Map admin UI ``daily_seconds`` to tab-server ``max_total_distraction_seconds``."""
        body = dict(payload)
        if "daily_seconds" in body and "max_total_distraction_seconds" not in body:
            body["max_total_distraction_seconds"] = body.pop("daily_seconds")
        elif "daily_seconds" in body:
            body.pop("daily_seconds", None)
        return body

    def update_master_budget(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = self._normalize_master_budget_payload(payload)
        if "max_total_distraction_seconds" not in body and not any(
            k in body for k in ("warning_threshold_percent", "categories_to_track")
        ):
            raise SettingsServiceError(
                "VALIDATION_ERROR",
                "daily_seconds or max_total_distraction_seconds is required",
                400,
            )
        try:
            return self._ts.post_json("/api/domains/budgets/master", body)
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

    def get_extension_status(self) -> dict[str, Any]:
        """Tab-server extension heartbeats (Chrome/Edge poll ~every 2s)."""
        try:
            return self._ts.get_json("/api/status")
        except TabServerUnavailableError as exc:
            raise SettingsServiceError("DEVICE_OFFLINE", str(exc), 409) from exc
        except TabServerRequestError as exc:
            raise SettingsServiceError("UPSTREAM_ERROR", exc.message, 502) from exc

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

    # ── Email configuration ─────────────────────────────────────────

    @staticmethod
    def get_email_config() -> dict[str, Any]:
        try:
            from focus_guard.deployment.config import DeploymentConfig
            cfg = DeploymentConfig.load()
            return {
                "enabled": cfg.email.enabled,
                "smtp_server": cfg.email.smtp_server,
                "smtp_port": cfg.email.smtp_port,
                "sender_email": cfg.email.sender_email,
                "recipients": cfg.email.recipients,
                "is_configured": cfg.email.is_configured(),
                "schedule": {
                    "hourly_enabled": cfg.reporting.schedule.hourly_enabled,
                    "hourly_interval_minutes": cfg.reporting.schedule.hourly_interval_minutes,
                    "daily_enabled": cfg.reporting.schedule.daily_enabled,
                    "daily_hour": cfg.reporting.schedule.daily_hour,
                },
            }
        except Exception as exc:
            raise SettingsServiceError("INTERNAL_ERROR", f"Failed to read email config: {exc}", 500) from exc

    @staticmethod
    def update_email_config(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from focus_guard.deployment.config import DeploymentConfig
            cfg = DeploymentConfig.load()

            # Handle test email request
            if payload.get("test"):
                if not cfg.email.is_configured():
                    raise SettingsServiceError("VALIDATION_ERROR", "Email not configured — set SMTP and recipients first", 400)
                try:
                    import smtplib
                    from email.mime.text import MIMEText
                    msg = MIMEText(
                        "This is a test email from FocusGuard.\n\n"
                        "If you received this, your email configuration is working correctly.\n\n"
                        "— FocusGuard",
                        "plain",
                    )
                    msg["Subject"] = "FocusGuard — Test Email"
                    msg["From"] = cfg.email.sender_email
                    msg["To"] = ", ".join(cfg.email.recipients)
                    with smtplib.SMTP(cfg.email.smtp_server, cfg.email.smtp_port, timeout=10) as server:
                        server.starttls()
                        server.login(
                            cfg.email.smtp_username or cfg.email.sender_email,
                            cfg.email.smtp_password,
                        )
                        server.sendmail(cfg.email.sender_email, cfg.email.recipients, msg.as_string())
                    return {"test_sent": True}
                except Exception as send_exc:
                    raise SettingsServiceError("UPSTREAM_ERROR", f"Failed to send test email: {send_exc}", 502) from send_exc

            if "enabled" in payload:
                cfg.email.enabled = bool(payload["enabled"])
            if "recipients" in payload:
                recipients = payload["recipients"]
                if isinstance(recipients, str):
                    recipients = [r.strip() for r in recipients.split(",") if r.strip()]
                cfg.email.recipients = recipients
            if "smtp_server" in payload:
                cfg.email.smtp_server = str(payload["smtp_server"])
            if "smtp_port" in payload:
                cfg.email.smtp_port = int(payload["smtp_port"])
            if "sender_email" in payload:
                cfg.email.sender_email = str(payload["sender_email"])
            if "smtp_username" in payload:
                cfg.email.smtp_username = str(payload["smtp_username"])
            if "smtp_password" in payload:
                cfg.email.smtp_password = str(payload["smtp_password"])

            # Schedule updates
            schedule = payload.get("schedule", {})
            if "hourly_enabled" in schedule:
                cfg.reporting.schedule.hourly_enabled = bool(schedule["hourly_enabled"])
            if "daily_enabled" in schedule:
                cfg.reporting.schedule.daily_enabled = bool(schedule["daily_enabled"])
            if "hourly_interval_minutes" in schedule:
                cfg.reporting.schedule.hourly_interval_minutes = max(1, int(schedule["hourly_interval_minutes"]))

            cfg.save()
            return {"updated": True, "is_configured": cfg.email.is_configured()}
        except SettingsServiceError:
            raise
        except Exception as exc:
            raise SettingsServiceError("INTERNAL_ERROR", f"Failed to update email config: {exc}", 500) from exc
