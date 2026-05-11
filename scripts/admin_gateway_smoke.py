"""Manual smoke helper for admin gateway Phase 1 APIs (P2-10).

Usage:
    python scripts/admin_gateway_smoke.py --password <ADMIN_PASSWORD>
    python scripts/admin_gateway_smoke.py --password <ADMIN_PASSWORD> --base-url https://guardian.example.com
"""

from __future__ import annotations

import argparse
import json
from urllib import error, request


DEFAULT_BASE_URL = "http://127.0.0.1:58393"


def _call(
    base_url: str,
    method: str,
    path: str,
    token: str | None = None,
    payload: dict | None = None,
):
    url = f"{base_url.rstrip('/')}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        parsed = json.loads(body) if body else {}
        return exc.code, parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Admin gateway smoke helper")
    parser.add_argument("--password", required=True, help="Admin password configured in deployment config")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Gateway root URL (default: {DEFAULT_BASE_URL}). Use your tunnel https://hostname for remote checks.",
    )
    args = parser.parse_args()
    base = args.base_url.strip().rstrip("/")

    print("[1] Health")
    status, body = _call(base, "GET", "/admin/health")
    print(status, body)

    print("[2] Login")
    status, body = _call(
        base,
        "POST",
        "/admin/api/v1/auth/login",
        payload={"username": "admin", "password": args.password},
    )
    print(status, body)
    token = body.get("token") if status == 200 else None
    if not token:
        print("Login failed, aborting smoke run.")
        return 1

    print("[3] Dashboard")
    status, body = _call(base, "GET", "/admin/api/v1/dashboard?device_id=default-device", token=token)
    print(status, list(body.keys()) if isinstance(body, dict) else body)

    print("[4] Exceptions create/list/revoke")
    status, created = _call(
        base,
        "POST",
        "/admin/api/v1/exceptions",
        token=token,
        payload={"domain": "youtube.com", "type": "temporary", "duration_seconds": 300, "reason": "smoke"},
    )
    print("create", status, created)

    status, listed = _call(base, "GET", "/admin/api/v1/exceptions?status=all&limit=50&offset=0", token=token)
    print("list", status, {"total": listed.get("total") if isinstance(listed, dict) else None})

    exception_id = created.get("id") if isinstance(created, dict) else None
    if exception_id:
        status, revoked = _call(base, "DELETE", f"/admin/api/v1/exceptions/{exception_id}", token=token)
        print("revoke", status, revoked)

    print("[5] Devices list + enforcement update")
    status, devices = _call(base, "GET", "/admin/api/v1/devices", token=token)
    print("devices", status, devices)

    device_id = "default-device"
    if isinstance(devices, dict) and devices.get("devices"):
        device_id = devices["devices"][0].get("id", device_id)

    status, enforcement = _call(
        base,
        "PUT",
        f"/admin/api/v1/devices/{device_id}/enforcement",
        token=token,
        payload={"mode": "tracking", "password": args.password},
    )
    print("enforcement", status, enforcement)

    print("[6] Logout")
    status, body = _call(base, "POST", "/admin/api/v1/auth/logout", token=token)
    print(status, body)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
