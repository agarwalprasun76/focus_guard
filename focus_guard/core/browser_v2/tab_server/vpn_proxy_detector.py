"""VPN and proxy detection for bypass prevention.

Detects common indicators that the user may be routing traffic through
a VPN or proxy to circumvent DNS-level or hosts-file blocking.

Addresses vulnerability **8.8.1** — VPN/proxy bypass.

Detection methods:
1. Check Windows proxy settings (registry + system settings)
2. Check for known VPN adapter names in network interfaces
3. Check for proxy environment variables
4. Periodic monitoring with alerts

Usage:
    from focus_guard.core.browser_v2.tab_server.vpn_proxy_detector import get_vpn_proxy_detector
    detector = get_vpn_proxy_detector()
    status = detector.check()
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Known VPN adapter name patterns (case-insensitive)
_VPN_ADAPTER_PATTERNS = [
    r"tap-windows",
    r"nordlynx",
    r"wintun",
    r"wireguard",
    r"openvpn",
    r"expressvpn",
    r"surfshark",
    r"proton",
    r"mullvad",
    r"cyberghost",
    r"pia\b",
    r"private internet access",
    r"windscribe",
    r"hotspot\s*shield",
    r"tunnelbear",
    r"vpn",
]

# Proxy-related environment variables
_PROXY_ENV_VARS = [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "SOCKS_PROXY", "socks_proxy",
]


class VPNProxyDetector:
    """Detects VPN and proxy usage that could bypass blocking."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_check_time: float = 0.0
        self._last_result: Optional[Dict] = None
        self._alert_count: int = 0
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def check(self) -> Dict:
        """Run all detection checks and return a combined result.
        
        Returns dict with:
            vpn_detected: bool
            proxy_detected: bool
            details: list of findings
            timestamp: float
        """
        findings: List[Dict] = []

        # 1. Check proxy environment variables
        for var in _PROXY_ENV_VARS:
            val = os.environ.get(var, "")
            if val:
                findings.append({
                    "type": "proxy_env_var",
                    "detail": f"Environment variable {var}={val}",
                    "severity": "high",
                })

        # 2. Check Windows proxy settings
        if os.name == "nt":
            findings.extend(self._check_windows_proxy())

        # 3. Check network adapters for VPN indicators
        findings.extend(self._check_vpn_adapters())

        vpn_detected = any(f["type"].startswith("vpn") for f in findings)
        proxy_detected = any(f["type"].startswith("proxy") for f in findings)

        result = {
            "vpn_detected": vpn_detected,
            "proxy_detected": proxy_detected,
            "bypass_risk": vpn_detected or proxy_detected,
            "findings": findings,
            "finding_count": len(findings),
            "timestamp": time.time(),
        }

        with self._lock:
            self._last_check_time = time.time()
            self._last_result = result

        return result

    def _check_windows_proxy(self) -> List[Dict]:
        """Check Windows registry for proxy settings."""
        findings = []
        try:
            import winreg
            key = winreg.OpenKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0,
                winreg.KEY_READ,
            )
            try:
                proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                if proxy_enable:
                    proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                    findings.append({
                        "type": "proxy_windows_registry",
                        "detail": f"Windows proxy enabled: {proxy_server}",
                        "severity": "high",
                    })
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.debug("Could not check Windows proxy settings: %s", e)
        return findings

    def _check_vpn_adapters(self) -> List[Dict]:
        """Check network adapters for VPN indicators."""
        findings = []
        try:
            import subprocess
            result = subprocess.run(
                ["ipconfig", "/all"] if os.name == "nt" else ["ip", "link", "show"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = result.stdout.lower()
            for pattern in _VPN_ADAPTER_PATTERNS:
                if re.search(pattern, output, re.IGNORECASE):
                    findings.append({
                        "type": "vpn_adapter",
                        "detail": f"VPN adapter pattern detected: {pattern}",
                        "severity": "medium",
                    })
        except Exception as e:
            logger.debug("Could not check network adapters: %s", e)
        return findings

    # ------------------------------------------------------------------
    # Periodic monitoring
    # ------------------------------------------------------------------

    def start_monitoring(self, interval_seconds: float = 120) -> None:
        """Start periodic VPN/proxy monitoring."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            name="VPNProxyMonitor",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info("VPN/proxy monitoring started (interval=%ss)", interval_seconds)

    def stop_monitoring(self) -> None:
        """Stop periodic monitoring."""
        self._stop_event.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None

    def _monitor_loop(self, interval: float) -> None:
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            try:
                result = self.check()
                if result["bypass_risk"]:
                    self._alert_count += 1
                    logger.warning(
                        "VPN/proxy bypass risk detected: %d findings",
                        result["finding_count"],
                    )
                    self._fire_alert(result)
            except Exception:
                logger.exception("Error in VPN/proxy check")
            self._stop_event.wait(interval)

    def _fire_alert(self, result: Dict) -> None:
        """Fire an audit alert for VPN/proxy detection."""
        try:
            from .audit_logger import get_audit_logger
            get_audit_logger().log_event(
                event_type="vpn_proxy_detected",
                domain="",
                details={
                    "vpn_detected": result["vpn_detected"],
                    "proxy_detected": result["proxy_detected"],
                    "findings": result["findings"][:5],  # Cap to avoid huge logs
                    "alert_count": self._alert_count,
                },
            )
        except Exception:
            pass

    def get_status(self) -> Dict:
        """Get detector status for diagnostics."""
        with self._lock:
            return {
                "last_check_time": self._last_check_time,
                "last_result": self._last_result,
                "alert_count": self._alert_count,
                "monitoring_active": (
                    self._monitor_thread is not None and self._monitor_thread.is_alive()
                ),
            }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[VPNProxyDetector] = None


def get_vpn_proxy_detector() -> VPNProxyDetector:
    """Get or create the singleton VPNProxyDetector."""
    global _instance
    if _instance is None:
        _instance = VPNProxyDetector()
    return _instance


def reset_vpn_proxy_detector() -> None:
    """Stop and reset the singleton (for testing)."""
    global _instance
    if _instance is not None:
        _instance.stop_monitoring()
    _instance = None
