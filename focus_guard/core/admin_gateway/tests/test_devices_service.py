from __future__ import annotations

import pytest

from focus_guard.core.admin_gateway.services.devices_service import (
    DevicesService,
    DevicesServiceError,
)
from focus_guard.core.admin_gateway.services.tab_server_client import (
    TabServerRequestError,
    TabServerUnavailableError,
)


class _FakeTabServerClient:
    def __init__(self, get_map=None, post_result=None, post_exc=None):
        self.get_map = get_map or {}
        self.post_result = post_result or {}
        self.post_exc = post_exc
        self.last_post_path = None
        self.last_post_payload = None

    def get_json(self, path, params=None):
        value = self.get_map.get(path)
        if isinstance(value, Exception):
            raise value
        return value

    def post_json(self, path, payload):
        self.last_post_path = path
        self.last_post_payload = payload
        if self.post_exc:
            raise self.post_exc
        return self.post_result


def test_list_devices_happy_path():
    client = _FakeTabServerClient(
        get_map={
            "/api/health": {"machine_name": "kid-laptop"},
            "/api/status": {"connected_browsers": 2},
            "/api/enforcement_mode": {"enforcement_mode": "advisory"},
        }
    )
    service = DevicesService(client)

    result = service.list_devices()
    assert "devices" in result
    assert result["devices"][0]["id"] == "kid-laptop"
    assert result["devices"][0]["enforcement_mode"] == "advisory"
    assert result["devices"][0]["browser_status"]["connected_browsers"] == 2


def test_list_devices_health_offline_maps_to_device_offline():
    client = _FakeTabServerClient(
        get_map={"/api/health": TabServerUnavailableError("offline")}
    )
    service = DevicesService(client)

    with pytest.raises(DevicesServiceError) as exc:
        service.list_devices()

    assert exc.value.code == "DEVICE_OFFLINE"
    assert exc.value.status_code == 409


def test_set_enforcement_mode_validation():
    client = _FakeTabServerClient()
    service = DevicesService(client)

    with pytest.raises(DevicesServiceError) as exc:
        service.set_enforcement_mode("kid-laptop", {"mode": "invalid"})

    assert exc.value.code == "VALIDATION_ERROR"
    assert exc.value.status_code == 400


def test_set_enforcement_mode_passes_password_and_maps_response():
    client = _FakeTabServerClient(post_result={"success": True, "enforcement_mode": "tracking"})
    service = DevicesService(client)

    result = service.set_enforcement_mode("kid-laptop", {"mode": "tracking", "password": "pw123"})
    assert result == {"updated": True, "device_id": "kid-laptop", "mode": "tracking"}
    assert client.last_post_path == "/api/enforcement_mode"
    assert client.last_post_payload == {"mode": "tracking", "password": "pw123"}


def test_set_enforcement_mode_maps_upstream_403_to_validation():
    client = _FakeTabServerClient(
        post_exc=TabServerRequestError(status_code=403, message="password required")
    )
    service = DevicesService(client)

    with pytest.raises(DevicesServiceError) as exc:
        service.set_enforcement_mode("kid-laptop", {"mode": "enforcing"})

    assert exc.value.code == "VALIDATION_ERROR"
    assert exc.value.status_code == 403

