"""Upstream client abstraction for tab server requests."""

from __future__ import annotations

import json
import logging
from urllib import parse, request
from urllib.error import HTTPError, URLError
from typing import Any

logger = logging.getLogger(__name__)


class TabServerClient:
    """Minimal tab-server client scaffold.

    P2-01 intentionally keeps transport implementation light. P2-04+ will add
    concrete HTTP calls, retries, and error translation.
    """

    def __init__(self, base_url: str, api_token: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = 5.0
        self._api_token = api_token
        self._api_token_loaded = api_token is not None

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET JSON payload from tab server."""

        url = self._build_url(path, params=params)
        req = request.Request(url=url, method="GET")
        return self._request_json(req)

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON payload to tab server."""

        url = self._build_url(path)
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        token = self._get_api_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = request.Request(
            url=url,
            method="POST",
            data=body,
            headers=headers,
        )
        return self._request_json(req)

    def _get_api_token(self) -> str | None:
        if self._api_token_loaded:
            return self._api_token

        self._api_token_loaded = True
        try:
            from focus_guard.core.browser_v2.tab_server.api_auth import get_api_auth_manager

            self._api_token = get_api_auth_manager().token
        except Exception:
            self._api_token = None
        return self._api_token

    def _build_url(self, path: str, params: dict[str, Any] | None = None) -> str:
        full_path = path if path.startswith("/") else f"/{path}"
        url = f"{self._base_url}{full_path}"
        if params:
            query = parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                url = f"{url}?{query}"
        return url

    def _request_json(self, req: request.Request) -> dict[str, Any]:
        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except HTTPError as exc:
            payload = ""
            try:
                payload = exc.read().decode("utf-8")
            except Exception:
                payload = ""
            message = payload or str(exc)
            raise TabServerRequestError(status_code=exc.code, message=message) from exc
        except URLError as exc:
            raise TabServerUnavailableError(str(exc)) from exc
        except TimeoutError as exc:
            raise TabServerUnavailableError(str(exc)) from exc
        except json.JSONDecodeError as exc:
            raise TabServerRequestError(status_code=502, message="Invalid JSON from tab server") from exc
        except Exception as exc:
            raise TabServerRequestError(status_code=500, message=str(exc)) from exc


class TabServerError(Exception):
    """Base class for tab-server client errors."""


class TabServerUnavailableError(TabServerError):
    """Raised when tab server cannot be reached."""


class TabServerRequestError(TabServerError):
    """Raised when tab server returns an invalid/failed response."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
