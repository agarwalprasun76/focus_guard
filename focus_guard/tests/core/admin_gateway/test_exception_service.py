"""Unit tests for ExceptionService proxy mapping (P2-05)."""

from __future__ import annotations

import unittest

from focus_guard.core.admin_gateway.services.exception_service import ExceptionService, ExceptionServiceError
from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerRequestError,
    TabServerUnavailableError,
)


class _FakeTabServerClient:
    def __init__(self) -> None:
        self.calls = []
        self.active_overrides = {"overrides": []}
        self.override_log = {"log": []}

    def get_json(self, path, params=None):
        self.calls.append(("GET", path, params))
        if path == "/api/override/active":
            return self.active_overrides
        if path == "/api/override/log":
            return self.override_log
        return {}

    def post_json(self, path, payload):
        self.calls.append(("POST", path, payload))
        if path == "/api/override":
            return {
                "granted": True,
                "override": {
                    "id": "ovr-1",
                    "start_time": 1000,
                    "duration_seconds": payload.get("duration", 300),
                },
            }
        if path == "/api/override/revoke":
            return {"revoked": True, "domain": payload.get("domain")}
        return {"success": True}


class TestExceptionService(unittest.TestCase):
    def test_create_temporary_maps_to_override_endpoint(self) -> None:
        client = _FakeTabServerClient()
        service = ExceptionService(client)

        result = service.create_exception(
            {
                "domain": "YouTube.com",
                "type": "temporary",
                "duration_seconds": 300,
                "reason": "homework",
            }
        )

        self.assertEqual(result["type"], "temporary")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["domain"], "youtube.com")
        self.assertTrue(any(call[1] == "/api/override" for call in client.calls))

    def test_create_permanent_maps_to_whitelist(self) -> None:
        client = _FakeTabServerClient()
        service = ExceptionService(client)

        result = service.create_exception(
            {"domain": "github.com", "type": "permanent", "reason": "always allow"}
        )

        self.assertEqual(result["id"], "perm_github.com")
        self.assertTrue(any(call[1] == "/api/domains/whitelist" for call in client.calls))

    def test_create_budgeted_requires_budget(self) -> None:
        client = _FakeTabServerClient()
        service = ExceptionService(client)

        with self.assertRaises(ExceptionServiceError) as ctx:
            service.create_exception({"domain": "reddit.com", "type": "budgeted"})

        self.assertEqual(ctx.exception.code, "VALIDATION_ERROR")

    def test_list_exceptions_combines_active_and_log(self) -> None:
        client = _FakeTabServerClient()
        client.active_overrides = {
            "overrides": [
                {
                    "id": "ovr-1",
                    "domain": "youtube.com",
                    "start_time": 1000,
                    "duration_seconds": 300,
                    "block_reason": "blocked",
                    "request_reason": "EMERGENCY: class",
                }
            ]
        }
        client.override_log = {
            "log": [
                {
                    "timestamp": 1010,
                    "event_type": "revoked",
                    "domain": "reddit.com",
                    "override_id": "ovr-2",
                    "details": {"request_reason": "done"},
                }
            ]
        }
        service = ExceptionService(client)

        result = service.list_exceptions(status="all", limit=50, offset=0)

        self.assertEqual(result["total"], 2)
        statuses = {entry["status"] for entry in result["exceptions"]}
        self.assertIn("active", statuses)
        self.assertIn("revoked", statuses)

    def test_revoke_exception_resolves_domain_and_calls_revoke(self) -> None:
        client = _FakeTabServerClient()
        client.active_overrides = {"overrides": [{"id": "ovr-1", "domain": "youtube.com"}]}
        service = ExceptionService(client)

        result = service.revoke_exception("ovr-1")

        self.assertEqual(result, {"revoked": True, "id": "ovr-1"})
        self.assertTrue(any(call[1] == "/api/override/revoke" for call in client.calls))

    def test_unavailable_upstream_maps_to_device_offline(self) -> None:
        class _UnavailableClient(_FakeTabServerClient):
            def get_json(self, path, params=None):  # type: ignore[override]
                raise TabServerUnavailableError("down")

        service = ExceptionService(_UnavailableClient())

        with self.assertRaises(ExceptionServiceError) as ctx:
            service.list_exceptions()

        self.assertEqual(ctx.exception.code, "DEVICE_OFFLINE")

    def test_request_error_maps_to_validation(self) -> None:
        class _RequestErrorClient(_FakeTabServerClient):
            def post_json(self, path, payload):  # type: ignore[override]
                raise TabServerRequestError(status_code=400, message="bad request")

        service = ExceptionService(_RequestErrorClient())

        with self.assertRaises(ExceptionServiceError) as ctx:
            service.create_exception(
                {
                    "domain": "youtube.com",
                    "type": "temporary",
                    "duration_seconds": 300,
                }
            )

        self.assertEqual(ctx.exception.code, "VALIDATION_ERROR")


if __name__ == "__main__":
    unittest.main()
