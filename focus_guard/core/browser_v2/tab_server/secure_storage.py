"""Secure storage utilities for FocusGuard data files.

Centralizes data directory management and provides:
1. Admin-protected storage location (ProgramData on Windows)
2. ACL enforcement to prevent standard users from deleting/modifying data
3. High-water mark tracking to detect if usage data is rolled back

Addresses vulnerability **8.6.1** — user deleting or modifying usage/audit data.

Usage:
    from focus_guard.core.browser_v2.tab_server.secure_storage import get_secure_data_dir, enforce_acls
    data_dir = get_secure_data_dir()
    enforce_acls(data_dir)
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Primary secure storage location
if os.name == "nt":
    _SECURE_DATA_DIR = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "FocusGuard"
else:
    _SECURE_DATA_DIR = Path("/var/lib/focusguard")

# Fallback (user-level, less secure)
_USER_DATA_DIR = Path.home() / ".focus_guard"

# High-water mark file
_HWM_FILENAME = "high_water_mark.json"


def get_secure_data_dir() -> Path:
    """Get the secure data directory, creating it if needed.
    
    Prefers ProgramData (admin-protected) on Windows.
    Falls back to ~/.focus_guard if ProgramData is not writable.
    """
    try:
        _SECURE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Test write access
        test_file = _SECURE_DATA_DIR / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        return _SECURE_DATA_DIR
    except (PermissionError, OSError):
        logger.warning(
            "Cannot write to secure dir %s, falling back to %s",
            _SECURE_DATA_DIR, _USER_DATA_DIR,
        )
        _USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        return _USER_DATA_DIR


def get_audit_dir() -> Path:
    """Get the directory for audit logs."""
    d = get_secure_data_dir() / "audit"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_usage_dir() -> Path:
    """Get the directory for usage tracking data."""
    d = get_secure_data_dir() / "usage"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_override_dir() -> Path:
    """Get the directory for override logs."""
    d = get_secure_data_dir() / "overrides"
    d.mkdir(parents=True, exist_ok=True)
    return d


def enforce_acls(directory: Path) -> bool:
    """Set Windows ACLs on a directory to prevent standard users from deleting files.
    
    Grants:
    - Administrators: Full control
    - SYSTEM: Full control  
    - Users: Read + Write (but NOT delete)
    
    Returns True if ACLs were set successfully.
    """
    if os.name != "nt":
        return False
    
    try:
        import subprocess
        dir_str = str(directory)
        
        # Use icacls to set permissions
        # /inheritance:r  — remove inherited permissions
        # /grant:r        — replace permissions
        commands = [
            # Remove inheritance
            ["icacls", dir_str, "/inheritance:r"],
            # Administrators: full control
            ["icacls", dir_str, "/grant:r", "Administrators:(OI)(CI)F"],
            # SYSTEM: full control
            ["icacls", dir_str, "/grant:r", "SYSTEM:(OI)(CI)F"],
            # Users: read, write, execute (but not delete children)
            ["icacls", dir_str, "/grant:r", "Users:(OI)(CI)(RX,W)"],
        ]
        
        for cmd in commands:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning("ACL command failed: %s — %s", " ".join(cmd), result.stderr.strip())
                return False
        
        logger.info("Set secure ACLs on %s", directory)
        return True
        
    except PermissionError:
        logger.warning("Cannot set ACLs (not admin): %s", directory)
        return False
    except Exception as e:
        logger.warning("Failed to set ACLs on %s: %s", directory, e)
        return False


# ---------------------------------------------------------------------------
# High-Water Mark — detects if usage data has been rolled back
# ---------------------------------------------------------------------------

class HighWaterMark:
    """Tracks monotonically increasing counters to detect data rollback.
    
    If a user deletes or replaces usage data files with older versions,
    the high-water mark will detect the discrepancy.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._dir = storage_dir or get_secure_data_dir()
        self._path = self._dir / _HWM_FILENAME
        self._data = self._load()
        self._tamper_count = 0
    
    def _load(self) -> dict:
        """Load high-water mark data from disk."""
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Could not load high-water mark: %s", e)
        return {"marks": {}, "last_updated": 0}
    
    def _save(self) -> None:
        """Save high-water mark data to disk."""
        try:
            self._data["last_updated"] = time.time()
            self._path.write_text(
                json.dumps(self._data, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Could not save high-water mark: %s", e)
    
    def update(self, key: str, value: float) -> bool:
        """Update a high-water mark. Returns False if rollback detected.
        
        Args:
            key: Identifier (e.g., "total_override_count", "total_active_seconds")
            value: Current value (must be monotonically increasing)
            
        Returns:
            True if value is >= stored mark (normal).
            False if value < stored mark (rollback detected).
        """
        marks = self._data.setdefault("marks", {})
        stored = marks.get(key, 0)
        
        if value < stored:
            # Rollback detected!
            self._tamper_count += 1
            logger.warning(
                "HIGH-WATER MARK ROLLBACK: key=%s, stored=%.1f, current=%.1f "
                "(data may have been tampered with)",
                key, stored, value,
            )
            self._fire_rollback_alert(key, stored, value)
            return False
        
        # Normal — update mark
        marks[key] = value
        self._save()
        return True
    
    def get(self, key: str) -> float:
        """Get the current high-water mark for a key."""
        return self._data.get("marks", {}).get(key, 0)
    
    def _fire_rollback_alert(self, key: str, stored: float, current: float) -> None:
        """Log audit event for data rollback."""
        try:
            from .audit_logger import get_audit_logger
            get_audit_logger().log_event(
                event_type="usage_data_rollback",
                domain="",
                details={
                    "key": key,
                    "stored_value": stored,
                    "current_value": current,
                    "message": f"Usage data for '{key}' decreased from {stored} to {current}. "
                               f"Data files may have been deleted or replaced.",
                },
            )
        except Exception:
            pass
    
    def get_status(self) -> dict:
        """Get status for diagnostics."""
        return {
            "path": str(self._path),
            "marks": dict(self._data.get("marks", {})),
            "tamper_count": self._tamper_count,
            "last_updated": self._data.get("last_updated", 0),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_hwm_instance: Optional[HighWaterMark] = None


def get_high_water_mark() -> HighWaterMark:
    """Get or create the singleton HighWaterMark."""
    global _hwm_instance
    if _hwm_instance is None:
        _hwm_instance = HighWaterMark()
    return _hwm_instance
