"""Registry-based policies to disable InPrivate/Incognito browsing.

Sets Windows registry keys that Chrome and Edge respect to disable
private browsing modes.  This prevents users from opening windows
where extensions are not loaded (or loaded in a separate context).

Addresses vulnerability **8.5.1** — Incognito/InPrivate bypass.

Requirements:
- Admin/elevated privileges to write to HKLM registry.
- Chrome respects: HKLM\\SOFTWARE\\Policies\\Google\\Chrome  IncognitoModeAvailability = 1
- Edge respects:   HKLM\\SOFTWARE\\Policies\\Microsoft\\Edge  InPrivateModeAvailability = 1
- Value 0 = enabled (default), 1 = disabled, 2 = forced

Usage:
    from focus_guard.core.browser_v2.tab_server.incognito_policy import get_incognito_policy_manager
    mgr = get_incognito_policy_manager()
    mgr.apply_policies()   # Disable incognito/inprivate
    mgr.remove_policies()  # Restore defaults
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Registry paths and values
_POLICIES = [
    {
        "browser": "Chrome",
        "key_path": r"SOFTWARE\Policies\Google\Chrome",
        "value_name": "IncognitoModeAvailability",
        "disable_value": 1,  # 0=enabled, 1=disabled, 2=forced
        "default_value": 0,
    },
    {
        "browser": "Edge",
        "key_path": r"SOFTWARE\Policies\Microsoft\Edge",
        "value_name": "InPrivateModeAvailability",
        "disable_value": 1,
        "default_value": 0,
    },
]


class IncognitoPolicyManager:
    """Manages registry policies to disable private browsing modes."""

    def __init__(self) -> None:
        self._applied: Dict[str, bool] = {}

    def apply_policies(self) -> List[Tuple[str, bool, str]]:
        """Disable Incognito/InPrivate for all supported browsers.

        Returns list of (browser, success, message) tuples.
        """
        results = []
        for policy in _POLICIES:
            success, msg = self._set_registry_value(
                policy["key_path"],
                policy["value_name"],
                policy["disable_value"],
            )
            self._applied[policy["browser"]] = success
            results.append((policy["browser"], success, msg))
            if success:
                logger.info(
                    "Disabled %s private browsing via registry policy", policy["browser"]
                )
            else:
                logger.warning(
                    "Could not disable %s private browsing: %s", policy["browser"], msg
                )

        # Audit log
        try:
            from .audit_logger import get_audit_logger
            get_audit_logger().log_event(
                event_type="incognito_policy_applied",
                domain="",
                details={
                    "results": [
                        {"browser": b, "success": s, "message": m}
                        for b, s, m in results
                    ]
                },
            )
        except Exception:
            pass

        return results

    def remove_policies(self) -> List[Tuple[str, bool, str]]:
        """Restore default Incognito/InPrivate settings.

        Returns list of (browser, success, message) tuples.
        """
        results = []
        for policy in _POLICIES:
            success, msg = self._delete_registry_value(
                policy["key_path"],
                policy["value_name"],
            )
            self._applied[policy["browser"]] = False
            results.append((policy["browser"], success, msg))
        return results

    def check_policies(self) -> Dict[str, dict]:
        """Check current state of private browsing policies.

        Returns dict of browser -> {applied, value, message}.
        """
        results = {}
        for policy in _POLICIES:
            value, msg = self._read_registry_value(
                policy["key_path"],
                policy["value_name"],
            )
            results[policy["browser"]] = {
                "applied": value == policy["disable_value"],
                "current_value": value,
                "expected_disable_value": policy["disable_value"],
                "message": msg,
            }
        return results

    def get_status(self) -> dict:
        """Get status for diagnostics."""
        return {
            "platform": sys.platform,
            "is_windows": os.name == "nt",
            "policies": self.check_policies(),
        }

    # ------------------------------------------------------------------
    # Registry helpers (Windows only)
    # ------------------------------------------------------------------

    @staticmethod
    def _set_registry_value(key_path: str, value_name: str, value: int) -> Tuple[bool, str]:
        """Set a DWORD registry value under HKLM."""
        if os.name != "nt":
            return False, "Not Windows — registry policies not applicable"
        try:
            import winreg
            key = winreg.CreateKeyEx(
                winreg.HKEY_LOCAL_MACHINE,
                key_path,
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
            )
            winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value)
            winreg.CloseKey(key)
            return True, f"Set {value_name}={value}"
        except PermissionError:
            return False, "Access denied — run as administrator"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _read_registry_value(key_path: str, value_name: str) -> Tuple[Optional[int], str]:
        """Read a DWORD registry value from HKLM."""
        if os.name != "nt":
            return None, "Not Windows"
        try:
            import winreg
            key = winreg.OpenKeyEx(
                winreg.HKEY_LOCAL_MACHINE,
                key_path,
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            )
            value, reg_type = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            return value, f"{value_name}={value}"
        except FileNotFoundError:
            return None, "Policy not set (key/value does not exist)"
        except PermissionError:
            return None, "Access denied"
        except Exception as e:
            return None, str(e)

    @staticmethod
    def _delete_registry_value(key_path: str, value_name: str) -> Tuple[bool, str]:
        """Delete a registry value from HKLM."""
        if os.name != "nt":
            return False, "Not Windows"
        try:
            import winreg
            key = winreg.OpenKeyEx(
                winreg.HKEY_LOCAL_MACHINE,
                key_path,
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
            )
            winreg.DeleteValue(key, value_name)
            winreg.CloseKey(key)
            return True, f"Deleted {value_name}"
        except FileNotFoundError:
            return True, "Already not set"
        except PermissionError:
            return False, "Access denied — run as administrator"
        except Exception as e:
            return False, str(e)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[IncognitoPolicyManager] = None


def get_incognito_policy_manager() -> IncognitoPolicyManager:
    """Get or create the singleton IncognitoPolicyManager."""
    global _instance
    if _instance is None:
        _instance = IncognitoPolicyManager()
    return _instance
