"""Dashboard orchestration for admin gateway."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerClient,
    TabServerError,
)

_DASHBOARD_THREAD_POOL_SIZE = 6

# Domains to exclude from Problem Sites / Recent Overrides (BUG-015: filter synthetic)
_SYNTHETIC_DOMAIN_PREFIXES = (
    "localhost",
    "127.0.0.1",
    "example.com",
    "example.org",
    "example.net",
    "test.",
    ".local",
)


def _is_synthetic_domain(domain: str) -> bool:
    """Return True if domain looks like a test/synthetic entry and should be hidden from parents."""
    if not domain or not isinstance(domain, str):
        return True
    d = domain.strip().lower()
    if not d:
        return True
    for prefix in _SYNTHETIC_DOMAIN_PREFIXES:
        if prefix.startswith("."):
            if d.endswith(prefix) or prefix in d:
                return True
        elif d == prefix or d.startswith(prefix + "."):
            return True
    return False


class DashboardService:
    """Aggregates dashboard data from tab-server endpoints."""

    def __init__(self, tab_server_client: TabServerClient) -> None:
        self._tab_server_client = tab_server_client

    def get_dashboard(
        self,
        device_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Aggregate dashboard payload from tab-server endpoints.

        All upstream calls run in parallel via a thread pool to avoid the
        cumulative latency of 12 sequential HTTP round-trips.

        start_date / end_date: optional YYYY-MM-DD; when set, override log
        and friction data are filtered to that range. Budget/stats remain today.
        """

        target_device = device_id or "default-device"

        override_log_params: dict[str, Any] = {"limit": 25}
        if start_date:
            override_log_params["since"] = start_date
        if end_date:
            override_log_params["until"] = end_date

        requests: dict[str, tuple[str, dict[str, Any] | None]] = {
            "health": ("/api/health", None),
            "budget": ("/api/distraction/budget", None),
            "distraction_sites": ("/api/distraction/sites", None),
            "override_stats": ("/api/override/stats", None),
            "override_log_resp": ("/api/override/log", override_log_params),
            "enforcement": ("/api/enforcement_mode", None),
            "blocked_sites_resp": ("/api/blocked/sites", None),
            "saved_links_stats": ("/api/saved_links/stats", None),
            "saved_links_resp": ("/api/saved_links", {"limit": 5}),
            "tabs_snapshot": ("/api/tabs", None),
            "activity_stats": ("/api/activity/stats", None),
            "blocked_activity_resp": ("/api/activity/logs", {"blocked": "true", "limit": 10}),
        }

        results = self._fetch_all_parallel(requests)

        health = results["health"]
        budget = results["budget"]
        distraction_sites = results["distraction_sites"]
        override_stats = results["override_stats"]
        override_log_resp = results["override_log_resp"]
        enforcement = results["enforcement"]
        blocked_sites_resp = results["blocked_sites_resp"]
        saved_links_stats = results["saved_links_stats"]
        saved_links_resp = results["saved_links_resp"]
        tabs_snapshot = results["tabs_snapshot"]
        activity_stats = results["activity_stats"]
        blocked_activity_resp = results["blocked_activity_resp"]

        override_log = override_log_resp.get("log", [])
        recent_overrides = self._build_recent_overrides(override_log)
        top_friction = self._build_top_friction(override_log, distraction_sites.get("sites", []))
        open_tabs = self._build_open_tabs(tabs_snapshot)
        recent_blocked_tabs = self._build_recent_blocked_tabs(blocked_activity_resp.get("activities", []))
        attention_items = self._compute_attention_items(
            top_friction=top_friction,
            budget_warning=bool(budget.get("warning", False)),
        )

        total_limit = float(budget.get("total_limit_seconds", 0) or 0)
        total_used = float(budget.get("total_used_seconds", 0) or 0)
        usage_percent = float(budget.get("usage_percent", 0) or 0)
        focus_score = max(0, min(100, int(round(100 - usage_percent))))

        return {
            "device": {
                "id": target_device,
                "name": target_device,
                "status": "online" if health else "offline",
                "enforcement_mode": enforcement.get("enforcement_mode", "enforcing"),
                "last_seen": None,
            },
            "focus_score": focus_score,
            "budget": {
                "used_seconds": total_used,
                "total_seconds": total_limit,
                "percent": usage_percent,
            },
            "blocks_today": int(budget.get("blocks_today", 0) or 0),
            "overrides_today": int(override_stats.get("total_overrides", 0) or 0),
            "blocked_sites": blocked_sites_resp.get("blocked_sites", []),
            "total_blocks": int(blocked_sites_resp.get("total_blocks", 0) or 0),
            "saved_links": {
                "total": int(saved_links_stats.get("total", 0) or 0),
                "unviewed": int(saved_links_stats.get("unviewed", 0) or 0),
                "top_domains": saved_links_stats.get("top_domains", []),
                "recent": saved_links_resp.get("links", []),
            },
            "activity_summary": {
                "total_events": int(activity_stats.get("total_events", 0) or 0),
                "blocked_count": int(activity_stats.get("blocked_count", 0) or 0),
                "distracting_count": int(activity_stats.get("distracting_count", 0) or 0),
                "blocked_percentage": float(activity_stats.get("blocked_percentage", 0.0) or 0.0),
                "distracting_percentage": float(activity_stats.get("distracting_percentage", 0.0) or 0.0),
            },
            "open_tabs": open_tabs,
            "recent_blocked_tabs": recent_blocked_tabs,
            "attention_items": attention_items,
            "recent_overrides": recent_overrides,
            "top_friction": top_friction,
        }

    def _fetch_all_parallel(
        self,
        requests: dict[str, tuple[str, dict[str, Any] | None]],
    ) -> dict[str, dict[str, Any]]:
        """Fire all tab-server GET requests concurrently and collect results.

        Each failed request returns ``{}`` so downstream code always gets a dict.
        """
        results: dict[str, dict[str, Any]] = {}

        with ThreadPoolExecutor(max_workers=_DASHBOARD_THREAD_POOL_SIZE) as pool:
            future_to_key = {
                pool.submit(self._safe_get, path, params): key
                for key, (path, params) in requests.items()
            }
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                results[key] = future.result()

        return results

    def _safe_get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        default: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fallback = default or {}
        try:
            payload = self._tab_server_client.get_json(path, params=params)
            return payload if isinstance(payload, dict) else fallback
        except TabServerError:
            return fallback

    def _build_recent_overrides(self, override_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
        recent: list[dict[str, Any]] = []
        for entry in reversed(override_log[-10:]):
            domain = str(entry.get("domain") or "").strip()
            if _is_synthetic_domain(domain):
                continue
            details = entry.get("details") or {}
            if not isinstance(details, dict):
                details = {}
            remaining = details.get("remaining_seconds")
            if remaining is None:
                remaining = 0
            try:
                remaining = int(remaining)
            except (TypeError, ValueError):
                remaining = 0
            # Human-friendly status (BUG-015): Active vs Expired, not raw action
            status = "Active" if remaining > 0 else "Expired"
            recent.append(
                {
                    "id": str(entry.get("override_id") or entry.get("id") or ""),
                    "domain": domain,
                    "status": status,
                    "expires_at": details.get("expires_at"),
                    "remaining_seconds": remaining,
                    "timestamp": entry.get("timestamp"),
                }
            )
        return recent

    def _build_open_tabs(self, tabs_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        tabs = tabs_snapshot.get("tabs", []) if isinstance(tabs_snapshot, dict) else []
        open_tabs: list[dict[str, Any]] = []
        for tab in tabs:
            if not isinstance(tab, dict):
                continue
            open_tabs.append(
                {
                    "id": str(tab.get("id") or ""),
                    "browser": str(tab.get("browser") or ""),
                    "title": str(tab.get("title") or ""),
                    "url": str(tab.get("url") or ""),
                    "active": bool(tab.get("active", False)),
                }
            )
        return open_tabs[:20]

    def _build_recent_blocked_tabs(self, activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocked: list[dict[str, Any]] = []
        for item in activities:
            if not isinstance(item, dict):
                continue
            blocked.append(
                {
                    "timestamp": item.get("timestamp"),
                    "domain": item.get("domain") or "",
                    "title": item.get("title") or "",
                    "url": item.get("url") or "",
                    "browser": item.get("browser") or "",
                    "reason": item.get("block_reason") or "blocked",
                }
            )
        return blocked[:10]

    def _build_top_friction(
        self,
        override_log: list[dict[str, Any]],
        sites: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        override_counts: dict[str, int] = {}
        for entry in override_log:
            domain = str(entry.get("domain") or "").strip().lower()
            if not domain or _is_synthetic_domain(domain):
                continue
            override_counts[domain] = override_counts.get(domain, 0) + 1

        time_by_domain: dict[str, float] = {}
        for site in sites:
            if not isinstance(site, dict):
                continue
            domain = str(site.get("domain") or "").strip().lower()
            if not domain or _is_synthetic_domain(domain):
                continue
            time_by_domain[domain] = float(site.get("active_seconds", 0) or 0)

        domains = set(override_counts.keys()) | set(time_by_domain.keys())
        ranked = sorted(
            domains,
            key=lambda d: (override_counts.get(d, 0), time_by_domain.get(d, 0.0)),
            reverse=True,
        )

        return [
            {
                "domain": domain,
                "override_count": override_counts.get(domain, 0),
                "time_used_seconds": time_by_domain.get(domain, 0.0),
            }
            for domain in ranked[:10]
        ]

    def _compute_attention_items(
        self,
        top_friction: list[dict[str, Any]],
        budget_warning: bool,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        if budget_warning:
            items.append(
                {
                    "type": "budget_warning",
                    "domain": None,
                    "count": 0,
                    "suggestion": "review_budget",
                }
            )

        for entry in top_friction:
            if entry.get("override_count", 0) >= 3:
                items.append(
                    {
                        "type": "frequent_override",
                        "domain": entry.get("domain"),
                        "count": entry.get("override_count", 0),
                        "suggestion": "promote_to_rule",
                    }
                )

        return items[:10]
