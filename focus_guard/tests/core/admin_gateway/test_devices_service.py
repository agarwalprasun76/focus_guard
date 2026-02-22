"""Unit tests for DevicesService (P2-06)."""

from __future__ import annotations

import unittest

from focus_guard.core.admin_gateway.services.devices_service import DevicesService, DevicesServiceError
from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerRequestError,
    TabServerUnavailableError,
)


class _FakeTabServerClient:
    def __init__(self) -> None:
        self.calls = []

    def get_json(self, path, params=None):
        self.calls.append(("GET", path, params))
        if path == "/api/health":
            return {"status": "healthy", "machine_name": "prasun-pc"}
        if path == "/api/status":
            return {"connected_browsers": 2}
        if path == "/api/enforcement_mode":
            return {"enforcement_mode": "enforcing"}
        return {}

    def post_json(self, path, payload):
        self.calls.append(("POST", path, payload))
        if path == "/api/enforcement_mode":
            return {"success": True, "enforcement_mode": payload.get("mode")}
        return {"success": True}


class TestDevicesService(unittest.TestCase):
    def test_list_devices_returns_single_device_payload(self) -> None:
        service = DevicesService(_FakeTabServerClient())

        result = service.list_devices()

        self.assertEqual(len(result["devices"]), 1)
        device = result["devices"][0]
        self.assertEqual(device["id"], "prasun-pc")
        self.assertEqual(device["status"], "online")
        self.assertEqual(device["enforcement_mode"], "enforcing")
        self.assertEqual(device["browser_status"]["connected_browsers"], 2)

    def test_set_enforcement_mode_validates_mode(self) -> None:
        service = DevicesService(_FakeTabServerClient())

        with self.assertRaises(DevicesServiceError) as ctx:
            service.set_enforcement_mode("prasun-pc", {"mode": "invalid"})

        self.assertEqual(ctx.exception.code, "VALIDATION_ERROR")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_set_enforcement_mode_proxies_to_tab_server(self) -> None:
        client = _FakeTabServerClient()
        service = DevicesService(client)

        result = service.set_enforcement_mode("prasun-pc", {"mode": "tracking", "password": "secret"})

        self.assertTrue(result["updated"])
        self.assertEqual(result["mode"], "tracking")
        self.assertTrue(any(c[1] == "/api/enforcement_mode" for c in client.calls))

    def test_unavailable_tab_server_maps_to_device_offline(self) -> None:
        class _UnavailableClient(_FakeTabServerClient):
            def get_json(self, path, params=None):  # type: ignore[override]
                raise TabServerUnavailableError("offline")

        service = DevicesService(_UnavailableClient())

        with self.assertRaises(DevicesServiceError) as ctx:
            service.list_devices()

        self.assertEqual(ctx.exception.code, "DEVICE_OFFLINE")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_request_error_maps_to_validation_or_upstream(self) -> None:
        class _RequestErrorClient(_FakeTabServerClient):
            def post_json(self, path, payload):  # type: ignore[override]
                raise TabServerRequestError(status_code=403, message="forbidden")

        service = DevicesService(_RequestErrorClient())

        with self.assertRaises(DevicesServiceError) as ctx:
            service.set_enforcement_mode("prasun-pc", {"mode": "tracking"})

        self.assertEqual(ctx.exception.code, "VALIDATION_ERROR")
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
