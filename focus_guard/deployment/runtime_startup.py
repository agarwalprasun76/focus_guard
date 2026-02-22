"""Runtime startup orchestration for deployment entrypoints.

This module centralizes best-effort startup for local runtime dependencies used by
admin APIs:
- tab server
- admin gateway

It is intentionally conservative with process ownership:
- never kills unknown processes
- reuses healthy already-running services when detected
- falls back to nearby ports only for processes it launches
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from urllib import request
from urllib.error import HTTPError
from urllib.error import URLError


@dataclass
class RuntimeHandles:
    """Handles to managed runtime components started by the orchestrator."""

    tab_server_runner: Optional[object]
    admin_gateway_process: Optional[subprocess.Popen]
    tab_server_host: str
    tab_server_port: int
    admin_gateway_host: str
    admin_gateway_port: int


class RuntimeStartupError(RuntimeError):
    """Raised when required runtime dependencies cannot be brought up."""


class RuntimeStartupOrchestrator:
    """Best-effort orchestrator for tab server + admin gateway startup."""

    def __init__(
        self,
        *,
        tab_server_host: str,
        tab_server_port: int,
        admin_gateway_host: str,
        admin_gateway_port: int,
        start_admin_gateway: bool,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._tab_server_host = tab_server_host
        self._tab_server_port = tab_server_port
        self._admin_gateway_host = admin_gateway_host
        self._admin_gateway_port = admin_gateway_port
        self._start_admin_gateway = start_admin_gateway
        self._logger = logger or logging.getLogger(__name__)

    def start(self) -> RuntimeHandles:
        """Start or attach to runtime dependencies and return handles."""
        tab_runner = self._ensure_tab_server()

        admin_process: Optional[subprocess.Popen] = None
        if self._start_admin_gateway:
            admin_process = self._ensure_admin_gateway()
        else:
            self._logger.info("Admin gateway startup disabled by configuration")

        return RuntimeHandles(
            tab_server_runner=tab_runner,
            admin_gateway_process=admin_process,
            tab_server_host=self._tab_server_host,
            tab_server_port=self._tab_server_port,
            admin_gateway_host=self._admin_gateway_host,
            admin_gateway_port=self._admin_gateway_port,
        )

    def collect_diagnostics(self) -> dict:
        """Collect runtime diagnostics for tab server/admin gateway readiness."""
        tab_port_available = self._is_port_available(self._tab_server_host, self._tab_server_port)
        tab_status, tab_payload = self._fetch_json(
            f"http://{self._tab_server_host}:{self._tab_server_port}/api/health"
        )
        tab_healthy = tab_status == 200 and isinstance(tab_payload, dict) and tab_payload.get("status") == "healthy"

        admin_port_available = self._is_port_available(self._admin_gateway_host, self._admin_gateway_port)
        admin_health_status, admin_health_payload = self._fetch_json(
            f"http://{self._admin_gateway_host}:{self._admin_gateway_port}/admin/health"
        )
        admin_meta_status, admin_meta_payload = self._fetch_json(
            f"http://{self._admin_gateway_host}:{self._admin_gateway_port}/admin/api/v1/meta"
        )
        admin_healthy = admin_health_status == 200 and admin_meta_status == 200

        fallback_admin_port = None
        if not admin_port_available and not admin_healthy:
            fallback_admin_port = self._find_available_port(
                host=self._admin_gateway_host,
                start_port=self._admin_gateway_port + 1,
                max_attempts=25,
            )

        uvicorn_available = self._has_uvicorn_module()
        is_admin = self._is_running_as_admin()

        can_start_tab = tab_healthy or tab_port_available
        can_start_admin = (
            (not self._start_admin_gateway)
            or admin_healthy
            or admin_port_available
            or fallback_admin_port is not None
        )
        overall_healthy = tab_healthy and (admin_healthy or (not self._start_admin_gateway))

        diagnostics = {
            "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "runtime": {
                "tab_server": {
                    "host": self._tab_server_host,
                    "port": self._tab_server_port,
                    "port_available": tab_port_available,
                    "health_status": tab_status,
                    "health_payload": tab_payload,
                    "healthy": tab_healthy,
                },
                "admin_gateway": {
                    "host": self._admin_gateway_host,
                    "port": self._admin_gateway_port,
                    "port_available": admin_port_available,
                    "health_status": admin_health_status,
                    "health_payload": admin_health_payload,
                    "meta_status": admin_meta_status,
                    "meta_payload": admin_meta_payload,
                    "healthy": admin_healthy,
                    "fallback_port_candidate": fallback_admin_port,
                    "managed_start_enabled": self._start_admin_gateway,
                },
            },
            "environment": {
                "python_executable": sys.executable,
                "platform": platform.platform(),
                "uvicorn_module_available": uvicorn_available,
                "is_admin": is_admin,
                "startup_env": {
                    "FOCUS_GUARD_STRICT_RUNTIME_STARTUP": os.getenv(
                        "FOCUS_GUARD_STRICT_RUNTIME_STARTUP"
                    ),
                    "FOCUS_GUARD_START_ADMIN_GATEWAY": os.getenv(
                        "FOCUS_GUARD_START_ADMIN_GATEWAY"
                    ),
                    "FOCUS_GUARD_ADMIN_GATEWAY_HOST": os.getenv(
                        "FOCUS_GUARD_ADMIN_GATEWAY_HOST"
                    ),
                    "FOCUS_GUARD_ADMIN_GATEWAY_PORT": os.getenv(
                        "FOCUS_GUARD_ADMIN_GATEWAY_PORT"
                    ),
                    "FOCUS_GUARD_TAB_SERVER_BASE_URL": os.getenv(
                        "FOCUS_GUARD_TAB_SERVER_BASE_URL"
                    ),
                },
            },
            "readiness": {
                "overall_healthy": overall_healthy,
                "can_start_tab_server": can_start_tab,
                "can_start_admin_gateway": can_start_admin,
                "overall_ready": can_start_tab and can_start_admin and uvicorn_available,
            },
        }
        diagnostics["recommendations"] = self._build_recommendations(diagnostics)
        return diagnostics

    def stop(self, handles: RuntimeHandles) -> None:
        """Stop only the processes/runners started by this orchestrator."""
        if handles.admin_gateway_process is not None:
            proc = handles.admin_gateway_process
            if proc.poll() is None:
                self._logger.info(
                    "Stopping admin gateway process (pid=%s, port=%d)",
                    proc.pid,
                    handles.admin_gateway_port,
                )
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()

        if handles.tab_server_runner is not None:
            try:
                self._logger.info(
                    "Stopping managed tab server on %s:%d",
                    handles.tab_server_host,
                    handles.tab_server_port,
                )
                handles.tab_server_runner.stop()
            except Exception as exc:  # noqa: BLE001
                self._logger.warning("Failed to stop managed tab server cleanly: %s", exc)

    def _ensure_tab_server(self) -> Optional[object]:
        """Start tab server when needed, or attach if healthy instance exists."""
        if self._is_tab_server_healthy(self._tab_server_host, self._tab_server_port):
            self._logger.info(
                "Tab server already healthy on %s:%d",
                self._tab_server_host,
                self._tab_server_port,
            )
            return None

        if not self._is_port_available(self._tab_server_host, self._tab_server_port):
            raise RuntimeStartupError(
                f"Tab server port {self._tab_server_host}:{self._tab_server_port} is occupied "
                "by a non-tab-server process"
            )

        from focus_guard.core.browser_v2.tab_server.runner import TabServerRunner

        runner = TabServerRunner(host=self._tab_server_host, port=self._tab_server_port)
        started = runner.start()
        if not started:
            raise RuntimeStartupError(
                f"Failed to start tab server on {self._tab_server_host}:{self._tab_server_port}"
            )

        if not self._wait_for(
            lambda: self._is_tab_server_healthy(self._tab_server_host, self._tab_server_port),
            timeout_seconds=15,
        ):
            runner.stop()
            raise RuntimeStartupError(
                f"Tab server did not become healthy on {self._tab_server_host}:{self._tab_server_port}"
            )

        self._logger.info(
            "Managed tab server started on %s:%d",
            self._tab_server_host,
            self._tab_server_port,
        )
        return runner

    def _ensure_admin_gateway(self) -> Optional[subprocess.Popen]:
        """Start admin gateway when needed, or attach if healthy instance exists."""
        if not self._has_uvicorn_module():
            raise RuntimeStartupError(
                "uvicorn is not available in this Python environment. "
                "Install uvicorn or run with a Python environment that includes it."
            )

        if self._is_admin_gateway_healthy(self._admin_gateway_host, self._admin_gateway_port):
            self._logger.info(
                "Admin gateway already healthy on %s:%d",
                self._admin_gateway_host,
                self._admin_gateway_port,
            )
            return None

        if not self._is_port_available(self._admin_gateway_host, self._admin_gateway_port):
            fallback_port = self._find_available_port(
                host=self._admin_gateway_host,
                start_port=self._admin_gateway_port + 1,
                max_attempts=25,
            )
            if fallback_port is None:
                raise RuntimeStartupError(
                    f"Admin gateway port {self._admin_gateway_host}:{self._admin_gateway_port} "
                    "is occupied and no fallback port is available"
                )
            self._logger.warning(
                "Admin gateway port %d occupied; falling back to %d",
                self._admin_gateway_port,
                fallback_port,
            )
            self._admin_gateway_port = fallback_port

        command = self._build_admin_gateway_command(self._admin_gateway_port)
        env = os.environ.copy()
        env["FOCUS_GUARD_TAB_SERVER_BASE_URL"] = (
            f"http://{self._tab_server_host}:{self._tab_server_port}"
        )

        self._logger.info(
            "Starting managed admin gateway on %s:%d",
            self._admin_gateway_host,
            self._admin_gateway_port,
        )

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        proc = subprocess.Popen(  # noqa: S603
            command,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        healthy = self._wait_for(
            lambda: self._is_admin_gateway_healthy(
                self._admin_gateway_host,
                self._admin_gateway_port,
            ),
            timeout_seconds=20,
        )
        if not healthy:
            proc.terminate()
            raise RuntimeStartupError(
                f"Admin gateway did not become healthy on "
                f"{self._admin_gateway_host}:{self._admin_gateway_port}"
            )

        return proc

    def _build_admin_gateway_command(self, port: int) -> list[str]:
        python_bin = shutil.which("python") or shutil.which("python3") or sys.executable
        return [
            python_bin,
            "-m",
            "uvicorn",
            "focus_guard.core.admin_gateway.app:create_app",
            "--factory",
            "--host",
            self._admin_gateway_host,
            "--port",
            str(port),
        ]

    @staticmethod
    def _is_port_available(host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return True
            except OSError:
                return False

    @staticmethod
    def _find_available_port(host: str, start_port: int, max_attempts: int) -> Optional[int]:
        for offset in range(max_attempts):
            candidate = start_port + offset
            if RuntimeStartupOrchestrator._is_port_available(host, candidate):
                return candidate
        return None

    def _is_tab_server_healthy(self, host: str, port: int) -> bool:
        status, payload = self._fetch_json(f"http://{host}:{port}/api/health")
        return status == 200 and isinstance(payload, dict) and payload.get("status") == "healthy"

    def _is_admin_gateway_healthy(self, host: str, port: int) -> bool:
        health_status, _ = self._fetch_json(f"http://{host}:{port}/admin/health")
        if health_status != 200:
            return False

        meta_status, meta_payload = self._fetch_json(f"http://{host}:{port}/admin/api/v1/meta")
        if meta_status != 200:
            return False
        return isinstance(meta_payload, dict) and meta_payload.get("service") == "admin_gateway"

    @staticmethod
    def _wait_for(check, timeout_seconds: int) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                if check():
                    return True
            except Exception:
                pass
            time.sleep(0.4)
        return False

    @staticmethod
    def _fetch_json(url: str) -> tuple[int, dict]:
        req = request.Request(url=url, method="GET")
        try:
            with request.urlopen(req, timeout=2.0) as response:
                body = response.read().decode("utf-8", errors="replace")
                payload = json.loads(body) if body.strip() else {}
                return int(response.status), payload
        except HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
                payload = json.loads(body) if body.strip() else {}
            except Exception:
                payload = {}
            return int(exc.code), payload
        except (URLError, OSError, ValueError):
            return 0, {}

    @staticmethod
    def _has_uvicorn_module() -> bool:
        try:
            import importlib.util

            return importlib.util.find_spec("uvicorn") is not None
        except Exception:
            return False

    @staticmethod
    def _is_running_as_admin() -> Optional[bool]:
        if os.name != "nt":
            return None
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return None

    def _build_recommendations(self, diagnostics: dict) -> list[str]:
        recommendations: list[str] = []

        tab = diagnostics.get("runtime", {}).get("tab_server", {})
        admin = diagnostics.get("runtime", {}).get("admin_gateway", {})
        env = diagnostics.get("environment", {})

        if not tab.get("healthy") and not tab.get("port_available"):
            recommendations.append(
                "Tab-server port is occupied by another process and tab server is not healthy. "
                "Free the configured tab-server port or update deployment_config tab_server_port."
            )
        elif not tab.get("healthy"):
            recommendations.append(
                "Tab server is not healthy on configured endpoint. "
                "Run startup in strict mode to fail fast and review service logs."
            )

        if admin.get("managed_start_enabled"):
            if not admin.get("healthy") and not admin.get("port_available"):
                fallback = admin.get("fallback_port_candidate")
                if fallback is not None:
                    recommendations.append(
                        f"Admin gateway configured port is occupied; fallback candidate {fallback} is available."
                    )
                else:
                    recommendations.append(
                        "Admin gateway configured port is occupied and no fallback port was found."
                    )

        if not env.get("uvicorn_module_available"):
            recommendations.append(
                "uvicorn module is missing in current Python environment; admin gateway managed startup will fail."
            )

        if env.get("is_admin") is False:
            recommendations.append(
                "Process is not running as administrator; hosts/incognito policy operations may degrade."
            )

        if not recommendations:
            recommendations.append("Runtime diagnostics look healthy for managed startup.")

        return recommendations
