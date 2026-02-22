"""Verify packaged admin runtime endpoints and SPA asset paths."""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from urllib import request
from urllib.error import HTTPError, URLError


class _AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.asset_links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = dict(attrs)
        if tag == "script" and attrs_dict.get("src"):
            self.asset_links.append(str(attrs_dict["src"]))
        if tag == "link" and attrs_dict.get("href"):
            self.asset_links.append(str(attrs_dict["href"]))


def _fetch_text(url: str, timeout_seconds: float) -> tuple[int, str, dict[str, str]]:
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="replace")
        headers = {k.lower(): v for k, v in response.headers.items()}
        return int(response.status), body, headers


def _fetch_json(url: str, timeout_seconds: float) -> tuple[int, dict]:
    status, body, _ = _fetch_text(url, timeout_seconds=timeout_seconds)
    return status, json.loads(body) if body.strip() else {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify packaged admin runtime")
    parser.add_argument("--base-url", default="http://127.0.0.1:58393", help="Runtime base URL")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")

    report: dict[str, object] = {
        "base_url": base,
        "checks": {},
    }

    try:
        health_status, health_payload = _fetch_json(f"{base}/admin/health", timeout_seconds=args.timeout)
        report["checks"]["health"] = {"status": health_status, "payload": health_payload}
        if health_status != 200:
            raise RuntimeError("/admin/health did not return 200")

        meta_status, meta_payload = _fetch_json(f"{base}/admin/api/v1/meta", timeout_seconds=args.timeout)
        report["checks"]["meta"] = {"status": meta_status, "payload": meta_payload}
        if meta_status != 200 or meta_payload.get("service") != "admin_gateway":
            raise RuntimeError("/admin/api/v1/meta contract check failed")

        dashboard_status, dashboard_payload = _fetch_json(
            f"{base}/admin/api/v1/dashboard?device_id=packaged-smoke",
            timeout_seconds=args.timeout,
        )
        report["checks"]["dashboard"] = {"status": dashboard_status, "has_device": "device" in dashboard_payload}
        if dashboard_status != 200 or "device" not in dashboard_payload:
            raise RuntimeError("/admin/api/v1/dashboard contract check failed")

        admin_status, admin_html, _ = _fetch_text(f"{base}/admin", timeout_seconds=args.timeout)
        parser = _AssetParser()
        parser.feed(admin_html)
        asset_links = parser.asset_links
        admin_assets = [x for x in asset_links if x.startswith("/admin/assets/")]
        report["checks"]["admin_shell"] = {
            "status": admin_status,
            "asset_links": asset_links[:10],
            "admin_asset_links_found": len(admin_assets),
        }
        if admin_status != 200:
            raise RuntimeError("/admin did not return 200")
        if not admin_assets:
            raise RuntimeError("No /admin/assets/* links found in /admin HTML")

    except HTTPError as exc:
        report["error"] = f"HTTPError: {exc.code} {exc.reason}"
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    except URLError as exc:
        report["error"] = f"URLError: {exc.reason}"
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    except Exception as exc:  # noqa: BLE001
        report["error"] = str(exc)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    report["result"] = "pass"
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
