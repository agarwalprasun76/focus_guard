"""Tab server v2 providing HTTP endpoints for browser extension communication.

Endpoints:
    GET  /api/health       - Server health check
    GET  /api/tabs         - Get current tab snapshot
    POST /api/tabs         - Receive tab data from extension
    GET  /api/command      - Get pending commands for extension
    POST /api/command      - Acknowledge command processing
    GET  /api/should_block - Check if URL should be blocked
    POST /api/events       - Receive real-time events from extension
    GET  /api/status       - Get extension connection status
"""

from __future__ import annotations

import json
import logging
import time
from http import HTTPStatus
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs

from .api_models import TabsSnapshot, TabInfo, BrowserFamily, CommandRequest, CommandResult

logger = logging.getLogger(__name__)


class TabServerRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler exposing tab server endpoints for extension communication."""

    server_version = "FocusGuardTabServer/2.0"
    context: "TabServerContext"  # Injected by server bootstrap

    def log_message(self, format: str, *args) -> None:
        """Override to use Python logging instead of stderr."""
        logger.debug("%s - %s", self.address_string(), format % args)

    def _set_headers(
        self,
        status: HTTPStatus = HTTPStatus.OK,
        *,
        content_type: str = "application/json",
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Event-Type, X-Event-Batch, Authorization")
        self.end_headers()

    def _parse_path(self) -> tuple[str, Dict[str, str]]:
        """Parse path and query parameters."""
        parsed = urlparse(self.path)
        query_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        return parsed.path, query_params

    def _read_json_body(self) -> Dict[str, Any]:
        """Read and parse JSON body."""
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8"))

    def _require_auth(self) -> bool:
        """Check if the request has a valid API auth token.
        
        Returns True if authorized, False if not (and sends 401 response).
        All mutation endpoints (POST, DELETE) should call this first.
        """
        from .api_auth import get_api_auth_manager
        auth_mgr = get_api_auth_manager()
        auth_header = self.headers.get("Authorization", "")
        
        if auth_mgr.validate_request(auth_header):
            return True
        
        # Unauthorized — send 401
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("Content-Type", "application/json")
        self.send_header("WWW-Authenticate", 'Bearer realm="FocusGuard API"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Event-Type, X-Event-Batch, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps({
            "error": "Unauthorized",
            "message": "Valid Bearer token required for mutation endpoints. "
                       "Include header: Authorization: Bearer <token>",
        }).encode("utf-8"))
        return False

    def do_OPTIONS(self) -> None:  # noqa: N802
        """Handle CORS preflight requests."""
        self._set_headers(HTTPStatus.OK)

    def do_GET(self) -> None:  # noqa: N802
        path, params = self._parse_path()
        
        if path == "/api/health":
            self._handle_health()
        elif path == "/api/tabs":
            self._handle_tabs_snapshot()
        elif path == "/api/status":
            self._handle_status()
        elif path == "/api/command":
            self._handle_get_commands(params)
        elif path == "/api/should_block":
            self._handle_should_block(params)
        elif path == "/api/should_block/rules":
            self._handle_get_block_rules(params)
        elif path == "/api/override":
            self._handle_check_override(params)
        elif path == "/api/override/active":
            self._handle_get_active_overrides()
        elif path == "/api/override/log":
            self._handle_get_override_log(params)
        elif path == "/api/override/stats":
            self._handle_get_override_stats()
        elif path == "/api/audit":
            self._handle_get_audit_log(params)
        elif path == "/api/audit/summary":
            self._handle_get_audit_summary(params)
        elif path == "/api/domain/rules":
            self._handle_get_domain_rules(params)
        elif path == "/api/domain/usage":
            self._handle_get_domain_usage(params)
        elif path == "/api/domain/summary":
            self._handle_get_domain_summary()
        elif path == "/api/search/logs":
            self._handle_get_search_logs(params)
        elif path == "/api/search/stats":
            self._handle_get_search_stats(params)
        elif path == "/api/search/patterns":
            self._handle_get_search_patterns(params)
        elif path == "/api/activity/logs":
            self._handle_get_activity_logs(params)
        elif path == "/api/activity/stats":
            self._handle_get_activity_stats(params)
        elif path == "/api/activity/apps":
            self._handle_get_app_usage(params)
        elif path == "/api/distraction/budget":
            self._handle_get_distraction_budget()
        elif path == "/api/distraction/sites":
            self._handle_get_distraction_sites()
        elif path == "/api/enforcement_mode":
            self._handle_get_enforcement_mode()
        elif path == "/api/popup_context":
            self._handle_get_popup_context(params)
        elif path == "/api/domains/overview":
            self._handle_get_domains_overview(params)
        elif path == "/api/domains/budgets":
            self._handle_get_domains_budgets()
        elif path == "/api/auth/status":
            self._handle_get_auth_status()
        elif path == "/api/blocked/sites":
            self._handle_get_blocked_sites(params)
        elif path == "/api/saved_links":
            self._handle_get_saved_links(params)
        elif path == "/api/saved_links/stats":
            self._handle_get_saved_links_stats()
        elif path == "/api/analytics/daily":
            self._handle_get_daily_insights(params)
        elif path == "/api/analytics/weekly":
            self._handle_get_weekly_summary()
        elif path == "/api/analytics/heatmap":
            self._handle_get_usage_heatmap(params)
        else:
            self._set_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(b'{"error": "Not found"}')

    # Endpoints that modify blocking/enforcement config — require auth token.
    _AUTH_REQUIRED_PATHS = frozenset({
        "/api/should_block/rules",      # Add blocking rule
        "/api/override/revoke",         # Revoke an active override
        "/api/domain/rules",            # Set domain rule
        "/api/domain/rules/delete",     # Delete domain rule
        "/api/classification/reload",   # Reload classification config
        "/api/blocking/enable_classification",  # Enable classification blocking
        "/api/enforcement_mode",        # Change enforcement mode (critical!)
        "/api/domains/category",        # Move domains between categories
        "/api/domains/whitelist",       # Add/remove from always-allowed
        "/api/domains/budgets/domain",  # Set per-domain budget
        "/api/domains/budgets/classification",  # Set classification budget
        "/api/domains/budgets/master",  # Set master budget
    })

    def do_POST(self) -> None:  # noqa: N802
        path, params = self._parse_path()
        
        # Gate dangerous mutation endpoints behind auth
        if path in self._AUTH_REQUIRED_PATHS:
            if not self._require_auth():
                return
        
        if path == "/api/tabs":
            self._handle_tabs_update()
        elif path == "/api/command":
            self._handle_command_ack()
        elif path == "/api/events":
            self._handle_events()
        elif path == "/api/should_block/rules":
            self._handle_add_block_rule()
        elif path == "/api/override":
            self._handle_request_override()
        elif path == "/api/override/smart":
            self._handle_request_override_with_classification()
        elif path == "/api/override/start":
            self._handle_start_override_usage()
        elif path == "/api/override/revoke":
            self._handle_revoke_override()
        elif path == "/api/domain/rules":
            self._handle_set_domain_rule()
        elif path == "/api/domain/rules/delete":
            self._handle_delete_domain_rule()
        elif path == "/api/domain/active":
            self._handle_update_tab_active_state()
        elif path == "/api/classification/reload":
            self._handle_reload_classification_config()
        elif path == "/api/blocking/enable_classification":
            self._handle_enable_classification_blocking()
        elif path == "/api/enforcement_mode":
            self._handle_set_enforcement_mode()
        elif path == "/api/domains/category":
            self._handle_set_domains_category()
        elif path == "/api/domains/whitelist":
            self._handle_set_domains_whitelist()
        elif path == "/api/domains/budgets/domain":
            self._handle_set_domain_budget()
        elif path == "/api/domains/budgets/classification":
            self._handle_set_classification_budget()
        elif path == "/api/domains/budgets/master":
            self._handle_set_master_budget()
        elif path == "/api/saved_links":
            self._handle_save_link()
        elif path == "/api/saved_links/view":
            self._handle_mark_link_viewed()
        elif path == "/api/saved_links/delete":
            self._handle_delete_saved_link()
        else:
            self._set_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(b'{"error": "Not found"}')

    # ------------------------------------------------------------------
    # GET Handlers
    # ------------------------------------------------------------------
    def _handle_get_auth_status(self) -> None:
        """Return API auth status (does NOT expose the token).
        
        If the caller provides a valid Authorization header, the response
        includes ``authenticated: true``; otherwise ``authenticated: false``.
        Useful for the extension to verify its stored token is still valid.
        """
        from .api_auth import get_api_auth_manager
        auth_mgr = get_api_auth_manager()
        auth_header = self.headers.get("Authorization", "")
        is_authed = auth_mgr.validate_request(auth_header) if auth_header else False
        status = auth_mgr.get_status()
        status["authenticated"] = is_authed
        # Never expose the actual token
        status.pop("token", None)
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps(status).encode("utf-8"))

    def _handle_health(self) -> None:
        """Return server health status."""
        payload = self.context.health_provider()
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def _handle_tabs_snapshot(self) -> None:
        """Return current tab snapshot."""
        snapshot: TabsSnapshot = self.context.tabs_provider()
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps(snapshot, default=_dataclass_to_dict).encode("utf-8"))

    def _handle_status(self) -> None:
        """Return extension connection status."""
        status = self.context.get_connection_status()
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps(status).encode("utf-8"))

    def _handle_get_commands(self, params: Dict[str, str]) -> None:
        """Return pending commands for a browser extension."""
        browser = params.get("browser", "")
        commands = self.context.get_pending_commands(browser)
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps({"commands": commands}).encode("utf-8"))

    def _handle_should_block(self, params: Dict[str, str]) -> None:
        """Check if a URL should be blocked.
        
        Query params:
            url: The URL to check
            domain: The domain of the URL
            title: The page title (optional, for better classification)
            tabId: The browser tab ID (optional, for search context tracking)
            referrer: The referrer URL (optional, for search context from navigation source)
        """
        url = params.get("url", "")
        domain = params.get("domain", "")
        title = params.get("title", "")
        referrer = params.get("referrer", "")
        tab_id_str = params.get("tabId", "")
        tab_id = int(tab_id_str) if tab_id_str.isdigit() else None
        
        # Track navigation for search context (detects entertainment searches)
        # Also process referrer if it's a search URL - this captures context from where user came from
        try:
            from .search_context_tracker import get_search_context_tracker
            tracker = get_search_context_tracker()
            
            # First process referrer if it's a search URL (to capture search context)
            if referrer:
                tracker.process_navigation(referrer, tab_id, "")
            
            # Then process the actual navigation
            tracker.process_navigation(url, tab_id, title, referrer)
        except Exception as e:
            logger.debug("Search context tracking failed: %s", e)
        
        decision = self.context.check_blocking(url, domain, title, tab_id)
        self._set_headers(HTTPStatus.OK)
        # Use to_dict() to include classification and budget info
        self.wfile.write(json.dumps(decision.to_dict()).encode("utf-8"))

    def _handle_get_block_rules(self, params: Dict[str, str]) -> None:
        """Return current blocking rules."""
        rules = self.context.get_block_rules()
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps({"rules": rules}).encode("utf-8"))

    def _handle_add_block_rule(self) -> None:
        """Add a blocking rule."""
        try:
            data = self._read_json_body()
            domain = data.get("domain", "")
            reason = data.get("reason", "blocked")
            
            if not domain:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain is required"}).encode("utf-8"))
                return
            
            self.context.add_block_rule(domain, reason)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({"status": "ok", "domain": domain}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to add block rule: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def do_DELETE(self) -> None:  # noqa: N802
        path, params = self._parse_path()
        
        # All DELETE endpoints require auth
        if not self._require_auth():
            return
        
        if path == "/api/should_block/rules":
            self._handle_delete_block_rule(params)
        else:
            self._set_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(b'{"error": "Not found"}')

    def _handle_delete_block_rule(self, params: Dict[str, str]) -> None:
        """Remove a blocking rule."""
        domain = params.get("domain", "")
        if not domain:
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": "domain parameter required"}).encode("utf-8"))
            return
        
        self.context.remove_block_rule(domain)
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps({"status": "ok", "domain": domain}).encode("utf-8"))

    def _handle_check_override(self, params: Dict[str, str]) -> None:
        """Check if a domain has an active override."""
        domain = params.get("domain", "")
        if not domain:
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": "domain parameter required"}).encode("utf-8"))
            return
        
        result = self.context.check_override(domain)
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps(result).encode("utf-8"))

    def _handle_get_active_overrides(self) -> None:
        """Get all active overrides."""
        overrides = self.context.get_active_overrides()
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps({"overrides": overrides}).encode("utf-8"))

    def _handle_get_override_log(self, params: Dict[str, str]) -> None:
        """Get override log entries."""
        limit = int(params.get("limit", "100"))
        domain = params.get("domain")
        log = self.context.get_override_log(limit, domain)
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps({"log": log}).encode("utf-8"))

    def _handle_get_override_stats(self) -> None:
        """Get override statistics."""
        stats = self.context.get_override_stats()
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps(stats).encode("utf-8"))
    
    def _handle_get_audit_log(self, params: Dict[str, str]) -> None:
        """Get audit log entries with optional filtering."""
        date_str = params.get("date")  # YYYY-MM-DD format
        event_type = params.get("event_type")
        domain = params.get("domain")
        limit = int(params.get("limit", "100"))
        
        events = self.context.get_audit_events(
            date_str=date_str,
            event_type=event_type,
            domain=domain,
            limit=limit,
        )
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps({"events": events}).encode("utf-8"))
    
    def _handle_get_audit_summary(self, params: Dict[str, str]) -> None:
        """Get audit summary for a given day."""
        date_str = params.get("date")  # YYYY-MM-DD format, defaults to today
        summary = self.context.get_audit_summary(date_str)
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(json.dumps(summary).encode("utf-8"))

    # ------------------------------------------------------------------
    # POST Handlers
    # ------------------------------------------------------------------
    def _handle_tabs_update(self) -> None:
        """Receive tab data from browser extension."""
        try:
            data = self._read_json_body()
            self.context.update_tabs(data)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to process tab update: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_command_ack(self) -> None:
        """Acknowledge command processing from extension."""
        try:
            data = self._read_json_body()
            browser = data.get("browser", "")
            self.context.acknowledge_commands(browser)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({"status": "acknowledged"}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to process command ack: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_events(self) -> None:
        """Receive real-time events from browser extension."""
        try:
            data = self._read_json_body()
            is_batch = self.headers.get("X-Event-Batch") == "true"
            
            if is_batch and "events" in data:
                for event in data["events"]:
                    self.context.process_event(event)
            else:
                self.context.process_event(data)
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to process event: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_request_override(self) -> None:
        """Request a temporary override for a blocked domain."""
        try:
            data = self._read_json_body()
            domain = data.get("domain", "")
            url = data.get("url", "")
            block_reason = data.get("block_reason", "")
            browser = data.get("browser", "unknown")
            duration = data.get("duration")
            request_reason = data.get("request_reason", "")
            
            if not domain:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain is required"}).encode("utf-8"))
                return
            
            result = self.context.request_override(
                domain=domain,
                url=url,
                block_reason=block_reason,
                browser=browser,
                duration=duration,
                request_reason=request_reason,
            )
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to process override request: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))
    
    def _handle_request_override_with_classification(self) -> None:
        """Request a temporary override with content classification.
        
        This endpoint classifies the content (using LLM or rules) and applies
        classification-aware budgets. Educational content gets more generous
        limits than distracting content.
        
        Request body:
            domain: str - The domain to allow temporarily
            url: str - The original URL that was blocked
            block_reason: str - Why the site was blocked
            browser: str - Which browser made the request
            duration: int (optional) - Override duration in seconds
            request_reason: str (optional) - User's reason for requesting
            tab_id: str (optional) - Tab ID for usage tracking
            context: dict (optional) - Additional context for classification:
                - title: Page/video title
                - description: Page description
                - channel: YouTube channel name
                - video_id: YouTube video ID
        
        Response:
            granted: bool
            override: dict (if granted)
            classification: dict with category, usefulness, confidence
            message: str
            remaining_today: int
            budget: dict with budget details
            require_screenshot: bool
            notify_parent: bool
            screenshot_taken: bool
        """
        try:
            data = self._read_json_body()
            domain = data.get("domain", "")
            url = data.get("url", "")
            block_reason = data.get("block_reason", "")
            browser = data.get("browser", "unknown")
            duration = data.get("duration")
            request_reason = data.get("request_reason", "")
            tab_id = data.get("tab_id")
            context = data.get("context", {})
            
            if not domain:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain is required"}).encode("utf-8"))
                return
            
            result = self.context.request_override_with_classification(
                domain=domain,
                url=url,
                block_reason=block_reason,
                browser=browser,
                duration=duration,
                request_reason=request_reason,
                tab_id=tab_id,
                context=context,
            )
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to process smart override request: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_start_override_usage(self) -> None:
        """Start using an override - called when user navigates to the site."""
        try:
            data = self._read_json_body()
            domain = data.get("domain", "")
            tab_id = data.get("tab_id", "unknown")
            
            if not domain:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain is required"}).encode("utf-8"))
                return
            
            result = self.context.start_override_usage(domain, tab_id)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to start override usage: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_revoke_override(self) -> None:
        """Revoke an active override."""
        try:
            data = self._read_json_body()
            domain = data.get("domain", "")
            
            if not domain:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain is required"}).encode("utf-8"))
                return
            
            revoked = self.context.revoke_override(domain)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({"revoked": revoked, "domain": domain}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to revoke override: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    # ------------------------------------------------------------------
    # Domain Rules and Usage Handlers
    # ------------------------------------------------------------------
    def _handle_get_domain_rules(self, params: Dict[str, str]) -> None:
        """Get domain rules configuration."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            
            domain = params.get("domain")
            if domain:
                rule = tracker.get_rule(domain)
                self._set_headers(HTTPStatus.OK)
                self.wfile.write(json.dumps(rule.to_dict()).encode("utf-8"))
            else:
                rules = tracker.get_all_rules()
                self._set_headers(HTTPStatus.OK)
                self.wfile.write(json.dumps({
                    "rules": [r.to_dict() for r in rules]
                }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get domain rules: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_domain_usage(self, params: Dict[str, str]) -> None:
        """Get domain usage statistics."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            
            domain = params.get("domain")
            stats = tracker.get_daily_stats(domain)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(stats).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get domain usage: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_domain_summary(self) -> None:
        """Get domain usage summary for email reports."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            
            summary = tracker.get_summary_for_email()
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(summary).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get domain summary: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_set_domain_rule(self) -> None:
        """Set a domain rule configuration."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker, DomainRuleConfig
            tracker = get_domain_usage_tracker()
            
            data = self._read_json_body()
            domain = data.get("domain")
            if not domain:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain is required"}).encode("utf-8"))
                return
            
            rule = DomainRuleConfig(
                domain=domain,
                max_overrides_per_day=data.get("max_overrides_per_day", 3),
                max_override_duration_seconds=data.get("max_override_duration_seconds", 300),
                max_cumulative_time_seconds=data.get("max_cumulative_time_seconds", 900),
                use_nonlinear_scaling=data.get("use_nonlinear_scaling", True),
                min_override_duration_seconds=data.get("min_override_duration_seconds", 60),
                only_count_active_window=data.get("only_count_active_window", True),
            )
            tracker.set_rule(rule)
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({"success": True, "rule": rule.to_dict()}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to set domain rule: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_delete_domain_rule(self) -> None:
        """Delete a domain rule configuration."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            
            data = self._read_json_body()
            domain = data.get("domain")
            if not domain:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain is required"}).encode("utf-8"))
                return
            
            deleted = tracker.remove_rule(domain)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({"deleted": deleted, "domain": domain}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to delete domain rule: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_update_tab_active_state(self) -> None:
        """Update whether a tab is in an active window."""
        try:
            from .domain_usage_tracker import get_domain_usage_tracker
            tracker = get_domain_usage_tracker()
            
            data = self._read_json_body()
            tab_id = data.get("tab_id")
            is_active = data.get("is_active", False)
            
            if not tab_id:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "tab_id is required"}).encode("utf-8"))
                return
            
            tracker.update_tab_active_state(str(tab_id), is_active)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to update tab active state: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    # ------------------------------------------------------------------
    # Classification Config Handlers
    # ------------------------------------------------------------------
    def _handle_reload_classification_config(self) -> None:
        """Reload classification rules from config file.
        
        Called by UI after editing classification_rules.json.
        """
        try:
            from .classification_service import get_classification_service, reset_classification_service
            
            # Reset the service to force reload
            reset_classification_service()
            
            # Get fresh instance (will reload config)
            svc = get_classification_service()
            
            # Also reload the generic URL classifier if it exists
            if svc._domain_classifier is not None:
                try:
                    svc._domain_classifier.reload_config()
                except Exception as e:
                    logger.warning("Could not reload domain classifier config: %s", e)
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "success": True,
                "message": "Classification config reloaded"
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to reload classification config: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_enable_classification_blocking(self) -> None:
        """Enable classification-based blocking at runtime.
        
        Can be called to enable blocking without restarting the server.
        """
        try:
            from .classification_blocker import setup_classification_blocking
            from .blocking import get_blocking_manager
            
            setup_classification_blocking()
            
            # Verify it's set
            bm = get_blocking_manager()
            is_enabled = bm._external_checker is not None
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "success": True,
                "enabled": is_enabled,
                "message": "Classification-based blocking enabled" if is_enabled else "Failed to enable"
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to enable classification blocking: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    # ------------------------------------------------------------------
    # Enforcement Mode Handlers
    # ------------------------------------------------------------------
    def _handle_get_enforcement_mode(self) -> None:
        """Return the current enforcement mode."""
        try:
            from focus_guard.deployment.config import DeploymentConfig, EnforcementMode
            config = DeploymentConfig.load()
            mode = config.enforcement_mode
            valid_modes = [m.value for m in EnforcementMode]
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "enforcement_mode": mode,
                "valid_modes": valid_modes,
                "description": {
                    "tracking": "Log only — no blocking, no popups",
                    "advisory": "Log + non-blocking notifications",
                    "enforcing": "Full blocking + budgets + overrides",
                },
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get enforcement mode: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_set_enforcement_mode(self) -> None:
        """Set the enforcement mode.
        
        Request body:
            mode: str — one of 'tracking', 'advisory', 'enforcing'
            password: str — required if config_password_hash is set in DeploymentConfig
        """
        try:
            import hashlib as _hashlib
            from focus_guard.deployment.config import DeploymentConfig, EnforcementMode
            data = self._read_json_body()
            new_mode = data.get("mode", "")
            password = data.get("password", "")
            
            valid_modes = {m.value for m in EnforcementMode}
            if new_mode not in valid_modes:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({
                    "error": f"Invalid mode '{new_mode}'. Must be one of: {sorted(valid_modes)}"
                }).encode("utf-8"))
                return
            
            config = DeploymentConfig.load()
            old_mode = config.enforcement_mode
            
            # Password check: if a config password is set, require it
            if config.config_password_hash:
                if not password:
                    self._set_headers(HTTPStatus.FORBIDDEN)
                    self.wfile.write(json.dumps({
                        "error": "Password required to change enforcement mode",
                        "password_required": True,
                    }).encode("utf-8"))
                    return
                provided_hash = _hashlib.sha256(password.encode()).hexdigest()
                if provided_hash != config.config_password_hash:
                    logger.warning(
                        "ALERT: Failed password attempt to change enforcement mode "
                        "from '%s' to '%s'", old_mode, new_mode,
                    )
                    # Audit log the failed attempt
                    try:
                        from .audit_logger import get_audit_logger
                        get_audit_logger().log_event(
                            event_type="enforcement_mode_password_failed",
                            domain="",
                            details={
                                "attempted_mode": new_mode,
                                "current_mode": old_mode,
                            },
                        )
                    except Exception:
                        pass
                    self._set_headers(HTTPStatus.FORBIDDEN)
                    self.wfile.write(json.dumps({
                        "error": "Incorrect password",
                        "password_required": True,
                    }).encode("utf-8"))
                    return
            
            config.enforcement_mode = new_mode
            config.save()
            
            logger.info("Enforcement mode changed: %s -> %s", old_mode, new_mode)
            
            # Audit log
            try:
                from .audit_logger import get_audit_logger
                get_audit_logger().log_event(
                    event_type="enforcement_mode_changed",
                    domain="",
                    details={
                        "old_mode": old_mode,
                        "new_mode": new_mode,
                    },
                )
            except Exception:
                pass
            
            # Email alert (always, regardless of password)
            self._send_enforcement_mode_alert(config, old_mode, new_mode)
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "success": True,
                "enforcement_mode": new_mode,
                "previous_mode": old_mode,
                "message": f"Enforcement mode changed from '{old_mode}' to '{new_mode}'",
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to set enforcement mode: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _send_enforcement_mode_alert(self, config, old_mode: str, new_mode: str) -> None:
        """Send email alert when enforcement mode changes (best-effort)."""
        try:
            if not config.email.is_configured():
                return
            import smtplib
            from email.mime.text import MIMEText

            subject = f"[FocusGuard ALERT] Enforcement mode changed: {old_mode} → {new_mode}"
            body = (
                f"The FocusGuard enforcement mode was changed.\n\n"
                f"Previous mode: {old_mode}\n"
                f"New mode:      {new_mode}\n"
                f"Machine: {config.machine_name}\n"
                f"User: {config.user_name}\n"
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"If you did not authorize this change, investigate immediately.\n"
            )

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = config.email.sender_email
            msg["To"] = ", ".join(config.email.recipients)

            with smtplib.SMTP(config.email.smtp_server, config.email.smtp_port) as server:
                if config.email.use_tls:
                    server.starttls()
                server.login(config.email.smtp_username, config.email.smtp_password)
                server.send_message(msg)
            logger.info("Sent enforcement mode change email alert")
        except Exception as e:
            logger.debug("Could not send enforcement mode email alert: %s", e)

    # ------------------------------------------------------------------
    # Popup Context Handler
    # ------------------------------------------------------------------
    def _handle_get_popup_context(self, params: Dict[str, str]) -> None:
        """Return personalized context for the blocking page.
        
        Query params:
            domain: The blocked domain (optional, for domain-specific stats)
        
        Returns JSON with:
            user_display_name, motivational_message, streak_days,
            focus_score, blocks_today, tone, show_* flags
        """
        import random
        import datetime
        
        try:
            from focus_guard.deployment.config import DeploymentConfig
            config = DeploymentConfig.load()
            popup = config.popup
            
            domain = params.get("domain", "")
            
            # --- User name ---
            display_name = popup.user_display_name or config.user_name or ""
            
            # --- Motivational message ---
            motivational_message = ""
            if popup.show_motivational_message and popup.motivational_messages:
                motivational_message = random.choice(popup.motivational_messages)
            
            # --- Streak calculation ---
            # Count consecutive days with at least one block (user was protected)
            streak_days = 0
            if popup.show_streak:
                streak_days = self._calculate_streak()
            
            # --- Focus score ---
            # Ratio of productive vs distraction time today (0-100)
            focus_score = 0
            blocks_today = 0
            if popup.show_focus_score:
                focus_score, blocks_today = self._calculate_focus_score()
            
            # --- Tone-specific greeting ---
            greetings = {
                "encouraging": [
                    f"Hey{(' ' + display_name) if display_name else ''}, you've got this!",
                    f"Keep it up{(', ' + display_name) if display_name else ''}! You're building great habits.",
                    f"Nice catch! FocusGuard is keeping you on track.",
                ],
                "firm": [
                    f"This site is blocked{(', ' + display_name) if display_name else ''}.",
                    f"Stay disciplined. Back to work.",
                    f"Not now. You have better things to do.",
                ],
                "playful": [
                    f"Oops! Caught you{(', ' + display_name) if display_name else ''}! 😄",
                    f"Nice try! But FocusGuard says no. 🛡️",
                    f"Distraction detected! Shields up! 🚀",
                ],
            }
            tone = popup.tone if popup.tone in greetings else "encouraging"
            greeting = random.choice(greetings[tone])
            
            payload = {
                "user_display_name": display_name,
                "greeting": greeting,
                "motivational_message": motivational_message,
                "streak_days": streak_days,
                "focus_score": focus_score,
                "blocks_today": blocks_today,
                "tone": tone,
                "show_streak": popup.show_streak,
                "show_focus_score": popup.show_focus_score,
                "show_motivational_message": popup.show_motivational_message,
            }
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get popup context: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))
    
    def _calculate_streak(self) -> int:
        """Calculate consecutive days with blocking activity."""
        import datetime
        try:
            from .storage import get_storage
            storage = get_storage()
            if not storage:
                return 0
            
            today = datetime.date.today()
            streak = 0
            for days_ago in range(0, 365):
                check_date = today - datetime.timedelta(days=days_ago)
                date_str = check_date.isoformat()
                # Check if there were any block events on this date
                logs = storage.get_domain_usage_logs(date_str)
                if logs and any(log.get("blocked", False) or log.get("override_count", 0) > 0 for log in logs):
                    streak += 1
                else:
                    if days_ago == 0:
                        continue  # Today might not have data yet
                    break
            return streak
        except Exception:
            return 0
    
    def _calculate_focus_score(self) -> tuple:
        """Calculate today's focus score (0-100) and block count.
        
        Returns:
            (focus_score, blocks_today)
        """
        try:
            from .domain_usage_tracker import get_master_distraction_budget
            budget = get_master_distraction_budget()
            status = budget.check_budget()
            usage_pct = status.get("usage_percent", 0)
            # Invert: low distraction usage = high focus score
            focus_score = max(0, min(100, int(100 - usage_pct)))
            blocks_today = status.get("blocks_today", 0)
            return focus_score, blocks_today
        except Exception:
            return 75, 0

    # ------------------------------------------------------------------
    # Domain Management Handlers (Section 7)
    # ------------------------------------------------------------------

    def _handle_get_domains_overview(self, params: Dict[str, str]) -> None:
        """GET /api/domains/overview — all domains with category, status, budget, usage."""
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()

            all_domains = mgr.get_all_known_domains()
            always_allowed = mgr.get_always_allowed_domains()
            per_rules = mgr.get_per_domain_rules()

            # Enrich with today's usage from tracker
            usage_stats: Dict[str, Any] = {}
            try:
                from .domain_usage_tracker import get_domain_usage_tracker
                tracker = get_domain_usage_tracker()
                usage_stats = tracker.get_daily_stats()  # all domains
            except Exception:
                pass

            # Collect categories for the frontend filter dropdown
            categories_set: set = set()

            for entry in all_domains:
                d = entry["domain"]
                cat = entry.get("category", "unknown")
                categories_set.add(cat)

                # Frontend-expected fields
                entry["whitelisted"] = d in always_allowed
                entry["blocked"] = entry.get("status") == "blocked"

                # Budget: extract max_cumulative_time_seconds from per-domain rule
                rule = per_rules.get(d) or entry.get("per_domain_rule")
                if rule and rule.get("max_cumulative_time_seconds"):
                    entry["budget_seconds"] = rule["max_cumulative_time_seconds"]
                else:
                    entry["budget_seconds"] = None

                # Usage stats
                if d in usage_stats:
                    s = usage_stats[d]
                    entry["usage_seconds"] = s.get("total_active_seconds", 0)
                    entry["visit_count"] = s.get("visit_count", s.get("override_count", 0))
                    entry["time_used_today_seconds"] = entry["usage_seconds"]
                    entry["overrides_used_today"] = s.get("override_count", 0)
                else:
                    entry["usage_seconds"] = 0
                    entry["visit_count"] = 0
                    entry["time_used_today_seconds"] = 0
                    entry["overrides_used_today"] = 0

            # Apply filters
            category_filter = params.get("category")
            status_filter = params.get("status")
            if category_filter:
                all_domains = [d for d in all_domains if d.get("category") == category_filter]
            if status_filter:
                all_domains = [d for d in all_domains if d.get("status") == status_filter]

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "domains": all_domains,
                "categories": sorted(categories_set),
                "total": len(all_domains),
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get domains overview: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_domains_budgets(self) -> None:
        """GET /api/domains/budgets — all budget configs."""
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "per_domain_rules": mgr.get_per_domain_rules(),
                "classification_budgets": mgr.get_classification_budgets(),
                "master_budget": mgr.get_master_budget(),
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get domain budgets: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_set_domains_category(self) -> None:
        """POST /api/domains/category — move domains to a category."""
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()

            data = self._read_json_body()
            # Accept both singular "domain" and plural "domains"
            domains = data.get("domains", [])
            if not domains and data.get("domain"):
                domains = [data["domain"]]
            category = data.get("category", "")
            if not domains or not category:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain(s) and category are required"}).encode("utf-8"))
                return

            mgr.move_domains_to_category(domains, category)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "success": True,
                "moved": domains,
                "category": category,
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to set domain category: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_set_domains_whitelist(self) -> None:
        """POST /api/domains/whitelist — add/remove from always-allowed."""
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()

            data = self._read_json_body()
            domain = data.get("domain", "")
            action = data.get("action", "")
            if not domain or action not in ("add", "remove"):
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain and action (add|remove) required"}).encode("utf-8"))
                return

            if action == "add":
                mgr.add_always_allowed_domain(domain)
            else:
                mgr.remove_always_allowed_domain(domain)

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "success": True,
                "domain": domain,
                "action": action,
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to update whitelist: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_set_domain_budget(self) -> None:
        """POST /api/domains/budgets/domain — set per-domain budget."""
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()

            data = self._read_json_body()
            domain = data.get("domain", "")
            if not domain:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "domain is required"}).encode("utf-8"))
                return

            # Accept "daily_seconds" from admin UI and map to max_cumulative_time_seconds
            daily_seconds = data.get("daily_seconds")
            if daily_seconds is not None:
                cumulative = int(daily_seconds)
            else:
                cumulative = data.get("max_cumulative_time_seconds", 900)

            rule = {
                "max_overrides_per_day": data.get("max_overrides_per_day", 3),
                "max_override_duration_seconds": data.get("max_override_duration_seconds", 300),
                "max_cumulative_time_seconds": cumulative,
                "penalty_per_extra_override_seconds": data.get("penalty_per_extra_override_seconds", 60),
            }
            mgr.set_per_domain_rule(domain, rule)

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "success": True,
                "domain": domain,
                "rule": rule,
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to set domain budget: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_set_classification_budget(self) -> None:
        """POST /api/domains/budgets/classification — set classification budget."""
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()

            data = self._read_json_body()
            # Accept both "key" (e.g. "GAMING:DISTRACTION") and "classification" (e.g. "Entertainment")
            key = data.get("key", "")
            if not key and data.get("classification"):
                # Map simple classification name to key format (CATEGORY:DISTRACTION)
                classification = data["classification"].upper()
                key = f"{classification}:DISTRACTION"
            if not key or ":" not in key:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "key (CATEGORY:USEFULNESS) or classification is required"}).encode("utf-8"))
                return

            # Accept "daily_seconds" from admin UI and map to max_cumulative_time_seconds
            daily_seconds = data.get("daily_seconds")
            if daily_seconds is not None:
                cumulative = int(daily_seconds)
            else:
                cumulative = data.get("max_cumulative_time_seconds", 900)

            budget = {
                "max_cumulative_time_seconds": cumulative,
                "max_overrides_per_day": data.get("max_overrides_per_day", 3),
                "max_override_duration_seconds": data.get("max_override_duration_seconds", 300),
                "penalty_per_extra_override_seconds": data.get("penalty_per_extra_override_seconds", 60),
                "require_screenshot": data.get("require_screenshot", False),
                "notify_parent": data.get("notify_parent", False),
            }
            mgr.set_classification_budget(key, budget)

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "success": True,
                "key": key,
                "budget": budget,
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to set classification budget: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_set_master_budget(self) -> None:
        """POST /api/domains/budgets/master — update master distraction budget."""
        try:
            from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
            mgr = get_domain_config_manager()

            data = self._read_json_body()
            current = mgr.get_master_budget()
            if "max_total_distraction_seconds" in data:
                current["max_total_distraction_seconds"] = data["max_total_distraction_seconds"]
            if "warning_threshold_percent" in data:
                current["warning_threshold_percent"] = data["warning_threshold_percent"]
            if "categories_to_track" in data:
                current["categories_to_track"] = data["categories_to_track"]

            mgr.set_master_budget(current)

            # Also update the live MasterDistractionBudget singleton
            try:
                from .domain_usage_tracker import get_master_distraction_budget, MasterDistractionBudgetConfig
                live_budget = get_master_distraction_budget()
                live_budget.update_config(MasterDistractionBudgetConfig.from_dict(current))
            except Exception:
                pass

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "success": True,
                "master_budget": current,
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to set master budget: %s", exc)
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    # ------------------------------------------------------------------
    # Search Logs and Stats Handlers
    # ------------------------------------------------------------------
    def _handle_get_search_logs(self, params: Dict[str, str]) -> None:
        """Get recent search logs.
        
        Query params:
            limit: Max entries to return (default 100)
            engine: Filter by search engine (google, bing, etc.)
            distracting: If 'true', only return distracting searches
            since: ISO timestamp to filter searches after
        """
        try:
            from .search_logger import get_search_logger
            logger_instance = get_search_logger()
            
            limit = int(params.get("limit", "100"))
            engine = params.get("engine")
            distracting_only = params.get("distracting", "").lower() == "true"
            since = params.get("since")
            
            entries = logger_instance.get_recent_searches(
                limit=limit,
                search_engine=engine,
                distracting_only=distracting_only,
                since=since,
            )
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "searches": [e.to_dict() for e in entries],
                "count": len(entries),
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get search logs: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_search_stats(self, params: Dict[str, str]) -> None:
        """Get search statistics.
        
        Query params:
            since: ISO timestamp to filter stats after (e.g., today's date for daily stats)
        """
        try:
            from .search_logger import get_search_logger
            logger_instance = get_search_logger()
            
            since = params.get("since")
            stats = logger_instance.get_search_stats(since=since)
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(stats).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get search stats: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_search_patterns(self, params: Dict[str, str]) -> None:
        """Get common distracting search patterns.
        
        Query params:
            limit: Max patterns to return (default 20)
            since: ISO timestamp to filter patterns after
        """
        try:
            from .search_logger import get_search_logger
            logger_instance = get_search_logger()
            
            limit = int(params.get("limit", "20"))
            since = params.get("since")
            
            patterns = logger_instance.get_distracting_search_patterns(
                limit=limit,
                since=since,
            )
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "patterns": patterns,
                "count": len(patterns),
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get search patterns: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    # ------------------------------------------------------------------
    # Activity Logs Handlers
    # ------------------------------------------------------------------
    def _handle_get_activity_logs(self, params: Dict[str, str]) -> None:
        """Get recent activity logs.
        
        Query params:
            limit: Max entries to return (default 100)
            event_type: Filter by event type (visit, block, classification)
            domain: Filter by domain
            blocked: If 'true', only return blocked events
            distracting: If 'true', only return distracting events
            since: ISO timestamp to filter after
        """
        try:
            from .activity_logger import get_activity_logger
            activity_logger = get_activity_logger()
            
            limit = int(params.get("limit", "100"))
            event_type = params.get("event_type")
            domain = params.get("domain")
            blocked_only = params.get("blocked", "").lower() == "true"
            distracting_only = params.get("distracting", "").lower() == "true"
            since = params.get("since")
            
            entries = activity_logger.get_recent_activity(
                limit=limit,
                event_type=event_type,
                domain=domain,
                blocked_only=blocked_only,
                distracting_only=distracting_only,
                since=since,
            )
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "activities": [e.to_dict() for e in entries],
                "count": len(entries),
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get activity logs: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_activity_stats(self, params: Dict[str, str]) -> None:
        """Get activity statistics.
        
        Query params:
            since: ISO timestamp to filter stats after
        """
        try:
            from .activity_logger import get_activity_logger
            activity_logger = get_activity_logger()
            
            since = params.get("since")
            stats = activity_logger.get_activity_stats(since=since)
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(stats).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get activity stats: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    # ------------------------------------------------------------------
    # App Usage Handler (non-browser application activity)
    # ------------------------------------------------------------------
    def _handle_get_app_usage(self, params: Dict[str, str]) -> None:
        """Get application usage summary from the activity database.

        Query params:
            date: YYYY-MM-DD (default today) — single day query
            start_date: YYYY-MM-DD — range start (inclusive)
            end_date: YYYY-MM-DD — range end (inclusive)
            limit: max apps to return (default 30)
        If start_date and end_date are provided, returns aggregated data
        across the range plus a per-day breakdown.
        """
        try:
            import os
            import sqlite3
            from datetime import date as _date, timedelta

            limit = min(100, max(1, int(params.get("limit", "30"))))

            # Determine date range
            start_date = params.get("start_date", "")
            end_date = params.get("end_date", "")
            single_date = params.get("date", "")

            if start_date and end_date:
                is_range = True
                date_str = start_date  # for response
            else:
                is_range = False
                date_str = single_date or _date.today().isoformat()
                start_date = date_str
                end_date = date_str

            # Locate usage.db written by EnhancedActivityLogger.
            # LOCALAPPDATA is the primary write location for the tray-app path.
            # ProgramData may contain a stale/empty DB from other components.
            local_app = os.environ.get("LOCALAPPDATA", "")
            program_data = os.environ.get("PROGRAMDATA", "")
            candidates = []
            if local_app:
                candidates.append(os.path.join(local_app, "FocusGuard", "usage.db"))
            try:
                from focus_guard.deployment.config import DeploymentConfig
                cfg_dir = str(DeploymentConfig.load().storage.get_data_directory())
                cfg_candidate = os.path.join(cfg_dir, "usage.db")
                if cfg_candidate not in candidates:
                    candidates.append(cfg_candidate)
            except Exception:
                pass
            if program_data:
                pd_candidate = os.path.join(program_data, "FocusGuard", "usage.db")
                if pd_candidate not in candidates:
                    candidates.append(pd_candidate)
            home = os.path.expanduser("~")
            candidates.append(os.path.join(home, ".focus_guard", "usage.db"))

            db_path = None
            for c in candidates:
                if os.path.isfile(c):
                    db_path = c
                    break

            if not db_path:
                self._set_headers(HTTPStatus.OK)
                self.wfile.write(json.dumps({
                    "date": date_str,
                    "start_date": start_date,
                    "end_date": end_date,
                    "apps": [],
                    "total_active_seconds": 0,
                    "total_sessions": 0,
                    "daily_breakdown": [],
                    "message": "No activity database found yet. Data will appear once the activity monitor has been running.",
                }).encode("utf-8"))
                return

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row

                # ── Primary: activity_samples (per-tick, most accurate) ──
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 1 FROM sqlite_master
                    WHERE type='table' AND name='activity_samples' LIMIT 1
                    """
                )
                has_samples = cursor.fetchone() is not None

                apps: list[dict] = []
                total_active = 0.0
                total_sessions = 0
                daily_breakdown: list[dict] = []

                if has_samples:
                    ts_start = f"{start_date} 00:00:00"
                    ts_end = f"{end_date} 23:59:59"
                    cursor.execute(
                        """
                        SELECT app_name,
                               SUM(sample_seconds) AS total_seconds,
                               COUNT(*)            AS sample_count,
                               MAX(domain)         AS last_domain,
                               MAX(window_title)   AS last_title
                        FROM activity_samples
                        WHERE timestamp >= ? AND timestamp <= ?
                        GROUP BY app_name
                        ORDER BY total_seconds DESC
                        LIMIT ?
                        """,
                        (ts_start, ts_end, limit),
                    )
                    for row in cursor.fetchall():
                        secs = row["total_seconds"] or 0
                        total_active += secs
                        total_sessions += row["sample_count"] or 0
                        apps.append({
                            "app_name": row["app_name"],
                            "active_seconds": round(secs, 1),
                            "sample_count": row["sample_count"],
                            "last_domain": row["last_domain"],
                            "last_title": row["last_title"],
                            "is_browser": self._is_browser_app(row["app_name"]),
                        })

                    if is_range:
                        cursor.execute(
                            """
                            SELECT DATE(timestamp) AS day,
                                   SUM(sample_seconds) AS total_seconds,
                                   COUNT(DISTINCT app_name) AS app_count,
                                   COUNT(*) AS sample_count
                            FROM activity_samples
                            WHERE timestamp >= ? AND timestamp <= ?
                            GROUP BY DATE(timestamp)
                            ORDER BY day
                            """,
                            (ts_start, ts_end),
                        )
                        for row in cursor.fetchall():
                            day_str = row["day"]
                            try:
                                day_obj = _date.fromisoformat(day_str)
                                day_name = day_obj.strftime("%A")
                            except Exception:
                                day_name = ""
                            daily_breakdown.append({
                                "date": day_str,
                                "day_of_week": day_name,
                                "total_seconds": round(row["total_seconds"] or 0, 1),
                                "app_count": row["app_count"],
                                "sample_count": row["sample_count"],
                            })
                else:
                    ts_start = f"{start_date} 00:00:00"
                    ts_end = f"{end_date} 23:59:59"
                    cursor.execute(
                        """
                        SELECT app_name,
                               SUM(active_duration) AS total_seconds,
                               COUNT(*)             AS session_count,
                               MAX(domain)          AS last_domain,
                               MAX(window_title)    AS last_title,
                               MAX(is_browser)      AS is_browser
                        FROM usage_sessions
                        WHERE start_time >= ? AND start_time <= ?
                        GROUP BY app_name
                        ORDER BY total_seconds DESC
                        LIMIT ?
                        """,
                        (ts_start, ts_end, limit),
                    )
                    for row in cursor.fetchall():
                        secs = row["total_seconds"] or 0
                        total_active += secs
                        total_sessions += row["session_count"] or 0
                        apps.append({
                            "app_name": row["app_name"],
                            "active_seconds": round(secs, 1),
                            "sample_count": row["session_count"],
                            "last_domain": row["last_domain"],
                            "last_title": row["last_title"],
                            "is_browser": bool(row["is_browser"]),
                        })

                    if is_range:
                        cursor.execute(
                            """
                            SELECT DATE(start_time) AS day,
                                   SUM(active_duration) AS total_seconds,
                                   COUNT(DISTINCT app_name) AS app_count,
                                   COUNT(*) AS session_count
                            FROM usage_sessions
                            WHERE start_time >= ? AND start_time <= ?
                            GROUP BY DATE(start_time)
                            ORDER BY day
                            """,
                            (ts_start, ts_end),
                        )
                        for row in cursor.fetchall():
                            day_str = row["day"]
                            try:
                                day_obj = _date.fromisoformat(day_str)
                                day_name = day_obj.strftime("%A")
                            except Exception:
                                day_name = ""
                            daily_breakdown.append({
                                "date": day_str,
                                "day_of_week": day_name,
                                "total_seconds": round(row["total_seconds"] or 0, 1),
                                "app_count": row["app_count"],
                                "session_count": row["session_count"],
                            })

                # ── Enrich with category from app_categories table ──
                cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_categories' LIMIT 1"
                )
                if cursor.fetchone():
                    cat_map: dict[str, dict] = {}
                    cursor.execute("SELECT app_name, category, subcategory, productivity_score FROM app_categories")
                    for row in cursor.fetchall():
                        cat_map[row["app_name"]] = {
                            "category": row["category"],
                            "subcategory": row["subcategory"],
                            "productivity_score": row["productivity_score"],
                        }
                    for app in apps:
                        info = cat_map.get(app["app_name"])
                        if info:
                            app["category"] = info["category"]
                            app["subcategory"] = info["subcategory"]
                            app["productivity_score"] = info["productivity_score"]

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "date": date_str,
                "start_date": start_date,
                "end_date": end_date,
                "apps": apps,
                "total_active_seconds": round(total_active, 1),
                "total_sessions": total_sessions,
                "daily_breakdown": daily_breakdown,
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get app usage: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    @staticmethod
    def _is_browser_app(app_name: str) -> bool:
        browsers = ("chrome", "firefox", "msedge", "opera", "safari", "brave", "vivaldi", "arc")
        lower = (app_name or "").lower()
        return any(b in lower for b in browsers)

    # ------------------------------------------------------------------
    # Master Distraction Budget Handlers
    # ------------------------------------------------------------------
    def _handle_get_distraction_budget(self) -> None:
        """Get the master distraction budget status.
        
        Returns:
            - budget_exhausted: bool
            - total_limit_seconds/formatted: total daily limit
            - total_used_seconds/formatted: time used today
            - remaining_seconds/formatted: time remaining
            - usage_percent: percentage used
            - warning: bool (if over 70%)
            - sites_visited: list of distraction sites visited today
            - sites_count: number of unique sites
            - total_overrides: total override count across all sites
        """
        try:
            from .domain_usage_tracker import get_master_distraction_budget
            budget = get_master_distraction_budget()
            status = budget.check_budget()
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(status).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get distraction budget: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_distraction_sites(self) -> None:
        """Get list of distraction sites visited today with time spent.
        
        Returns list sorted by time spent (descending).
        """
        try:
            from .domain_usage_tracker import get_master_distraction_budget
            budget = get_master_distraction_budget()
            status = budget.check_budget()
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "sites": status["sites_visited"],
                "count": status["sites_count"],
                "total_time_seconds": status["total_used_seconds"],
                "total_time_formatted": status["total_used_formatted"],
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get distraction sites: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))


    # ------------------------------------------------------------------
    # Blocked Sites Handler
    # ------------------------------------------------------------------
    def _handle_get_blocked_sites(self, params: Dict[str, str]) -> None:
        """Get list of blocked sites with block counts and details.

        Query params:
            since: ISO timestamp to filter from (defaults to start of today)
            limit: Max number of domains to return (default 20)

        Returns:
            blocked_sites: list of {domain, count, category, last_blocked}
            total_blocks: int
            blocks_today: int
        """
        try:
            from .activity_logger import get_activity_logger
            from .domain_usage_tracker import get_master_distraction_budget
            from datetime import datetime, date as _date

            limit = int(params.get("limit", "20"))
            since = params.get("since")
            if not since:
                since = _date.today().isoformat()

            activity = get_activity_logger()
            stats = activity.get_activity_stats(since=since) if activity else {}
            top_blocked = stats.get("top_blocked_domains", [])[:limit]

            # Enrich with category info from domain config manager
            try:
                from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
                mgr = get_domain_config_manager()
                for entry in top_blocked:
                    domain = entry.get("domain", "")
                    cat = mgr.get_domain_category(domain) if domain else None
                    entry["category"] = cat or "UNKNOWN"
            except Exception:
                for entry in top_blocked:
                    entry.setdefault("category", "UNKNOWN")

            # Get blocks_today from master budget
            blocks_today = 0
            try:
                budget = get_master_distraction_budget()
                budget_status = budget.check_budget()
                blocks_today = budget_status.get("blocks_today", 0)
            except Exception:
                blocks_today = stats.get("blocked_count", 0)

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "blocked_sites": top_blocked,
                "total_blocks": stats.get("blocked_count", 0),
                "blocks_today": blocks_today,
                "period_since": since,
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get blocked sites: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    # ------------------------------------------------------------------
    # Saved Links Handlers
    # ------------------------------------------------------------------
    def _handle_get_saved_links(self, params: Dict[str, str]) -> None:
        """Get saved links list.

        Query params:
            limit: int (default 50)
            offset: int (default 0)
            viewed: 'true'|'false' (optional filter)
            domain: str (optional filter)
        """
        try:
            from .saved_links import get_saved_links_store
            store = get_saved_links_store()

            limit = int(params.get("limit", "50"))
            offset = int(params.get("offset", "0"))
            viewed_param = params.get("viewed")
            viewed = None
            if viewed_param == "true":
                viewed = True
            elif viewed_param == "false":
                viewed = False
            domain = params.get("domain")

            links = store.get_links(limit=limit, offset=offset, viewed=viewed, domain=domain)
            total = store.get_link_count(viewed=viewed)

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({
                "links": [link.to_dict() for link in links],
                "total": total,
                "limit": limit,
                "offset": offset,
            }).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get saved links: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_saved_links_stats(self) -> None:
        """Get saved links summary statistics."""
        try:
            from .saved_links import get_saved_links_store
            store = get_saved_links_store()
            stats = store.get_stats()

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(stats).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get saved links stats: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_save_link(self) -> None:
        """Save a blocked link for later viewing.

        Request body:
            url: str (required)
            domain: str
            title: str
            category: str
            comment: str
        """
        try:
            from .saved_links import get_saved_links_store
            store = get_saved_links_store()

            data = self._read_json_body()
            url = data.get("url", "").strip()
            if not url:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "url is required"}).encode("utf-8"))
                return

            link = store.save_link(
                url=url,
                domain=data.get("domain", ""),
                title=data.get("title", ""),
                category=data.get("category", ""),
                comment=data.get("comment", ""),
            )

            self._set_headers(HTTPStatus.CREATED)
            self.wfile.write(json.dumps(link.to_dict()).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to save link: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_mark_link_viewed(self) -> None:
        """Mark a saved link as viewed.

        Request body:
            id: int (required)
        """
        try:
            from .saved_links import get_saved_links_store
            store = get_saved_links_store()

            data = self._read_json_body()
            link_id = data.get("id")
            if not link_id:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "id is required"}).encode("utf-8"))
                return

            updated = store.mark_viewed(int(link_id))
            if updated:
                self._set_headers(HTTPStatus.OK)
                self.wfile.write(json.dumps({"success": True, "id": link_id}).encode("utf-8"))
            else:
                self._set_headers(HTTPStatus.NOT_FOUND)
                self.wfile.write(json.dumps({"error": "Link not found"}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to mark link viewed: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_delete_saved_link(self) -> None:
        """Delete a saved link.

        Request body:
            id: int (required)
        """
        try:
            from .saved_links import get_saved_links_store
            store = get_saved_links_store()

            data = self._read_json_body()
            link_id = data.get("id")
            if not link_id:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "id is required"}).encode("utf-8"))
                return

            deleted = store.delete_link(int(link_id))
            if deleted:
                self._set_headers(HTTPStatus.OK)
                self.wfile.write(json.dumps({"success": True, "id": link_id}).encode("utf-8"))
            else:
                self._set_headers(HTTPStatus.NOT_FOUND)
                self.wfile.write(json.dumps({"error": "Link not found"}).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to delete saved link: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    # ------------------------------------------------------------------
    # Analytics Handlers
    # ------------------------------------------------------------------
    def _handle_get_daily_insights(self, params: Dict[str, str]) -> None:
        """Get consolidated daily insights.
        
        Query params:
            date: Date in YYYY-MM-DD format (defaults to today)
        """
        try:
            from .analytics_service import get_analytics_service
            service = get_analytics_service()
            
            date_str = params.get("date")
            insights = service.get_daily_insights(date_str)
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(insights.to_dict()).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get daily insights: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_weekly_summary(self) -> None:
        """Get weekly summary with trends."""
        try:
            from .analytics_service import get_analytics_service
            service = get_analytics_service()
            
            summary = service.get_weekly_summary()
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(summary).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get weekly summary: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_get_usage_heatmap(self, params: Dict[str, str]) -> None:
        """Get hourly usage heatmap.
        
        Query params:
            days: Number of days to include (default 7)
        """
        try:
            from .analytics_service import get_analytics_service
            service = get_analytics_service()
            
            days = int(params.get("days", "7"))
            heatmap = service.get_usage_heatmap(days)
            
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(heatmap).encode("utf-8"))
        except Exception as exc:
            logger.exception("Failed to get usage heatmap: %s", exc)
            self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))


class TabServerContext:
    """Callback container supplying business logic for request handlers.
    
    This class bridges the HTTP handlers with the actual business logic,
    allowing for dependency injection and easier testing.
    """

    def __init__(
        self,
        *,
        health_provider: Callable[[], dict],
        tabs_provider: Callable[[], TabsSnapshot],
        command_handler: Callable[[CommandRequest], CommandResult],
        tabs_updater: Optional[Callable[[Dict[str, Any]], None]] = None,
        blocking_checker: Optional[Callable[[str, str], Any]] = None,
        rules_provider: Optional[Callable[[], List[Dict[str, str]]]] = None,
        rule_adder: Optional[Callable[[str, str], None]] = None,
        rule_remover: Optional[Callable[[str], None]] = None,
        event_processor: Optional[Callable[[Dict[str, Any]], None]] = None,
        command_queue: Optional["CommandQueue"] = None,
    ) -> None:
        self._health_provider = health_provider
        self._tabs_provider = tabs_provider
        self._command_handler = command_handler
        self._tabs_updater = tabs_updater
        self._blocking_checker = blocking_checker
        self._rules_provider = rules_provider
        self._rule_adder = rule_adder
        self._rule_remover = rule_remover
        self._event_processor = event_processor
        self._command_queue = command_queue or CommandQueue()

    def health_provider(self) -> dict:
        return self._health_provider()

    def tabs_provider(self) -> TabsSnapshot:
        return self._tabs_provider()

    def command_handler(self, request: CommandRequest) -> CommandResult:
        return self._command_handler(request)

    def get_connection_status(self) -> dict:
        """Get extension connection status."""
        snapshot = self._tabs_provider()
        return {
            "connected_browsers": [
                {
                    "browser": b.browser.value if hasattr(b.browser, 'value') else b.browser,
                    "connected": b.connected,
                    "last_heartbeat": b.last_heartbeat,
                    "extension_version": b.extension_version,
                }
                for b in snapshot.browsers
            ],
            "total_tabs": len(snapshot.tabs),
            "timestamp": time.time(),
        }

    def update_tabs(self, data: Dict[str, Any]) -> None:
        """Process tab update from extension."""
        if self._tabs_updater:
            self._tabs_updater(data)

    def check_blocking(
        self, 
        url: str, 
        domain: str,
        title: str = "",
        tab_id: Optional[int] = None,
    ) -> Any:
        """Check if URL should be blocked.
        
        The override manager is consulted first: if the domain has an active
        (non-expired) override the request is allowed.  Once the override
        expires, subsequent calls will fall through to the normal blocking
        checker and the site will be blocked again.
        
        Enforcement mode (from DeploymentConfig) controls the final decision:
        - TRACKING:  Classification runs and is logged, but should_block is always False.
        - ADVISORY:  Same as tracking, plus a notification hint is included.
        - ENFORCING: Full blocking (current default behavior).
        
        Args:
            url: The URL to check
            domain: The domain of the URL
            title: The page title (for better classification)
            tab_id: The browser tab ID (for search context tracking)
        """
        from .blocking import BlockingDecision

        # --- Determine enforcement mode ---
        enforcement_mode = self._get_enforcement_mode()

        # --- Override check (skip in tracking mode — no overrides needed) ---
        if enforcement_mode == "enforcing":
            try:
                override_status = self.check_override(domain)
                if override_status.get("has_override"):
                    remaining = override_status.get("remaining_seconds", 0)
                    return BlockingDecision(
                        should_block=False,
                        reason=f"Override active ({int(remaining)}s remaining)",
                    )
            except Exception as exc:
                logger.debug("Override check failed (continuing): %s", exc)

        # --- Normal blocking check (always runs for classification/logging) ---
        decision = BlockingDecision(should_block=False)
        if self._blocking_checker:
            try:
                decision = self._blocking_checker(url, domain, title, tab_id)
            except TypeError:
                decision = self._blocking_checker(url, domain)

        # --- Apply enforcement mode ---
        if enforcement_mode != "enforcing" and decision.should_block:
            original_reason = decision.reason
            decision.should_block = False
            if enforcement_mode == "tracking":
                decision.reason = f"[TRACKING] Would block: {original_reason}"
            elif enforcement_mode == "advisory":
                decision.reason = f"[ADVISORY] Would block: {original_reason}"
            logger.info(
                "Enforcement mode '%s': allowing %s (would have blocked: %s)",
                enforcement_mode, domain, original_reason,
            )

        # --- Record block event for blocks_today counter ---
        if decision.should_block:
            try:
                from .domain_usage_tracker import get_master_distraction_budget
                get_master_distraction_budget().record_block(domain)
            except Exception:
                pass

        return decision

    def _get_enforcement_mode(self) -> str:
        """Get the current enforcement mode from DeploymentConfig.
        
        Returns 'enforcing' if config cannot be loaded (safe default).
        """
        try:
            from focus_guard.deployment.config import DeploymentConfig
            config = DeploymentConfig.load()
            return config.enforcement_mode
        except Exception:
            return "enforcing"

    def get_block_rules(self) -> List[Dict[str, str]]:
        """Get current blocking rules."""
        if self._rules_provider:
            return self._rules_provider()
        return []

    def add_block_rule(self, domain: str, reason: str = "blocked") -> None:
        """Add a blocking rule."""
        if self._rule_adder:
            self._rule_adder(domain, reason)

    def remove_block_rule(self, domain: str) -> None:
        """Remove a blocking rule."""
        if self._rule_remover:
            self._rule_remover(domain)

    def get_pending_commands(self, browser: str) -> List[Dict[str, Any]]:
        """Get pending commands for a browser."""
        return self._command_queue.get_commands(browser)

    def acknowledge_commands(self, browser: str) -> None:
        """Acknowledge that commands were processed."""
        self._command_queue.clear_commands(browser)

    def process_event(self, event: Dict[str, Any]) -> None:
        """Process a real-time event from extension."""
        if self._event_processor:
            self._event_processor(event)

    def queue_command(self, browser: str, command: Dict[str, Any]) -> None:
        """Queue a command for a browser extension."""
        self._command_queue.add_command(browser, command)

    # ------------------------------------------------------------------
    # Override Management
    # ------------------------------------------------------------------
    def check_override(self, domain: str) -> Dict[str, Any]:
        """Check if a domain has an active override."""
        from .override_manager import get_override_manager
        return get_override_manager().check_override(domain)

    def request_override(
        self,
        domain: str,
        url: str,
        block_reason: str,
        browser: str = "unknown",
        duration: Optional[int] = None,
        request_reason: str = "",
    ) -> Dict[str, Any]:
        """Request a temporary override for a blocked domain."""
        from .override_manager import get_override_manager
        return get_override_manager().request_override(
            domain=domain,
            url=url,
            block_reason=block_reason,
            browser=browser,
            duration=duration,
            request_reason=request_reason,
        )
    
    def request_override_with_classification(
        self,
        domain: str,
        url: str,
        block_reason: str,
        browser: str = "unknown",
        duration: Optional[int] = None,
        request_reason: str = "",
        tab_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Request a temporary override with content classification.
        
        This method classifies the content (using LLM or rules) and applies
        classification-aware budgets. Educational content gets more generous
        limits than distracting content.
        """
        from .override_manager import get_override_manager
        return get_override_manager().request_override_with_classification(
            domain=domain,
            url=url,
            block_reason=block_reason,
            browser=browser,
            duration=duration,
            request_reason=request_reason,
            tab_id=tab_id,
            context=context,
        )

    def revoke_override(self, domain: str) -> bool:
        """Revoke an active override."""
        from .override_manager import get_override_manager
        return get_override_manager().revoke_override(domain)

    def start_override_usage(self, domain: str, tab_id: str) -> Dict[str, Any]:
        """Start using an override - called when user navigates to the site."""
        from .override_manager import get_override_manager
        return get_override_manager().start_override_usage(domain, tab_id)

    def get_active_overrides(self) -> List[Dict[str, Any]]:
        """Get all active overrides."""
        from .override_manager import get_override_manager
        return get_override_manager().get_active_overrides()

    def get_override_log(self, limit: int = 100, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get override log entries."""
        from .override_manager import get_override_manager
        return get_override_manager().get_log(limit, domain)

    def get_override_stats(self) -> Dict[str, Any]:
        """Get override statistics."""
        from .override_manager import get_override_manager
        return get_override_manager().get_daily_stats()
    
    # ------------------------------------------------------------------
    # Audit Log
    # ------------------------------------------------------------------
    def get_audit_events(
        self,
        date_str: Optional[str] = None,
        event_type: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit log events with optional filtering."""
        from .audit_logger import get_audit_logger
        return get_audit_logger().get_events(
            date_str=date_str,
            event_type=event_type,
            domain=domain,
            limit=limit,
        )
    
    def get_audit_summary(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Get audit summary for a given day."""
        from .audit_logger import get_audit_logger
        return get_audit_logger().get_daily_summary(date_str)


class CommandQueue:
    """Thread-safe queue for commands to be sent to browser extensions."""

    def __init__(self) -> None:
        import threading
        self._lock = threading.Lock()
        self._commands: Dict[str, List[Dict[str, Any]]] = {}

    def add_command(self, browser: str, command: Dict[str, Any]) -> None:
        """Add a command for a browser."""
        with self._lock:
            if browser not in self._commands:
                self._commands[browser] = []
            self._commands[browser].append(command)

    def get_commands(self, browser: str) -> List[Dict[str, Any]]:
        """Get pending commands for a browser."""
        with self._lock:
            return self._commands.get(browser, []).copy()

    def clear_commands(self, browser: str) -> None:
        """Clear commands for a browser after acknowledgment."""
        with self._lock:
            if browser in self._commands:
                self._commands[browser] = []


class TabServer(ThreadingHTTPServer):
    """Threading HTTP server configured with the TabServerRequestHandler."""

    def __init__(self, server_address, context: TabServerContext):
        handler_class = type(
            "ContextualTabServerRequestHandler",
            (TabServerRequestHandler,),
            {"context": context},
        )
        super().__init__(server_address, handler_class)


def _dataclass_to_dict(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return {key: _dataclass_to_dict(getattr(obj, key)) for key in obj.__dataclass_fields__}
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _dataclass_to_dict(value) for key, value in obj.items()}
    if isinstance(obj, Enum):
        return obj.value
    return obj
