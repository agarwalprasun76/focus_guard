"""Unified domain configuration manager.

Single source of truth for all domain categories, whitelists, blocking rules,
and budget configurations. Replaces the fragmented domain config that was
previously spread across constants.py, app_config.json, loader.py,
classification_blocker.py, and domain_usage_tracker.py.

Usage:
    from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
    mgr = get_domain_config_manager()
    cats = mgr.get_domain_categories()
    mgr.add_domain_to_category("example.com", "social_media")
"""

from __future__ import annotations

import atexit
import hashlib
import json
import logging
import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default data — used to seed domain_config.json on first run
# ---------------------------------------------------------------------------

_DEFAULT_DOMAIN_CATEGORIES: Dict[str, List[str]] = {
    "social_media": [
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "reddit.com", "pinterest.com", "tiktok.com", "snapchat.com",
        "whatsapp.com", "telegram.org", "discord.com", "pronto.io",
    ],
    "entertainment": [
        "youtube.com", "netflix.com", "hulu.com", "disneyplus.com",
        "hbomax.com", "primevideo.com", "twitch.tv", "spotify.com",
        "soundcloud.com",
    ],
    "gaming": [
        "store.steampowered.com", "steampowered.com", "epicgames.com",
        "roblox.com", "minecraft.net",
    ],
    "shopping": [
        "amazon.com", "ebay.com", "etsy.com", "walmart.com",
        "target.com", "bestbuy.com", "newegg.com", "aliexpress.com",
    ],
    "news": [
        "nytimes.com", "wsj.com", "washingtonpost.com", "theguardian.com",
        "bbc.com", "cnn.com", "reuters.com", "bloomberg.com",
    ],
    "email": [
        "gmail.com", "outlook.com", "yahoo.com", "protonmail.com",
        "zoho.com", "icloud.com", "mail.com",
    ],
    "work": [
        "office.com", "slack.com", "zoom.us", "teams.microsoft.com",
        "atlassian.com", "jira.com", "confluence.com",
    ],
    "development": [
        "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
        "stackexchange.com", "dev.to", "medium.com", "devdocs.io",
    ],
    "productivity": [
        "notion.so", "trello.com", "asana.com", "todoist.com",
        "evernote.com", "bear.app", "obsidian.md",
    ],
    "education": [
        "khanacademy.org", "coursera.org", "edx.org", "udemy.com",
        "wikipedia.org", "artofproblemsolving.com",
    ],
    "adult": [
        # Common adult sites - blocked immediately without classification
        "pornhub.com", "xvideos.com", "xnxx.com", "xhamster.com",
        "redtube.com", "youporn.com", "tube8.com", "spankbang.com",
        "eporner.com", "porn.com", "brazzers.com", "bangbros.com",
        "realitykings.com", "naughtyamerica.com", "mofos.com",
        "onlyfans.com", "fansly.com", "chaturbate.com", "stripchat.com",
        "livejasmin.com", "cam4.com", "bongacams.com", "myfreecams.com",
    ],
}

_DEFAULT_ALWAYS_ALLOWED_DOMAINS: List[str] = sorted({
    # Email
    "mail.google.com", "outlook.live.com", "outlook.office.com",
    "outlook.office365.com", "mail.yahoo.com", "mail.proton.me",
    "mail.zoho.com",
    # Productivity suites
    "calendar.google.com", "docs.google.com", "sheets.google.com",
    "slides.google.com", "meet.google.com", "teams.microsoft.com",
    "notion.so", "www.notion.so",
    # Developer tools
    "github.com", "www.github.com", "gitlab.com", "www.gitlab.com",
    "stackoverflow.com", "www.stackoverflow.com",
})

_DEFAULT_ALWAYS_ALLOWED_CATEGORIES: List[str] = ["EDUCATION", "PRODUCTIVITY"]

_DEFAULT_BLOCKED_CATEGORIES: List[str] = [
    "ENTERTAINMENT", "GAMING", "SOCIAL_MEDIA", "ADULT",
]

_DEFAULT_SYSTEM_WHITELIST: List[str] = sorted({
    # System domains
    "google.com", "gstatic.com", "googleapis.com", "microsoft.com",
    "apple.com", "mozilla.org", "mozilla.com", "mozilla.net",
    "windowsupdate.com", "microsoftonline.com", "live.com",
    # CDNs
    "cloudfront.net", "akamaihd.net", "akamaized.net", "cloudflare.com",
    "fastly.net", "cloudflare.net", "amazonaws.com",
    # Security / Updates
    "windows.com", "office.com", "office.net", "office365.com",
})

_DEFAULT_CLASSIFICATION_BUDGETS: Dict[str, Dict[str, Any]] = {
    "EDUCATION:EDUCATIONAL": {
        "max_cumulative_time_seconds": 3600,
        "max_overrides_per_day": 10,
        "max_override_duration_seconds": 600,
        "penalty_per_extra_override_seconds": 0,
        "require_screenshot": False,
        "notify_parent": False,
    },
    "EDUCATION:ENRICHMENT": {
        "max_cumulative_time_seconds": 1800,
        "max_overrides_per_day": 5,
        "max_override_duration_seconds": 600,
        "penalty_per_extra_override_seconds": 30,
        "require_screenshot": False,
        "notify_parent": False,
    },
    "PRODUCTIVITY:EDUCATIONAL": {
        "max_cumulative_time_seconds": 3600,
        "max_overrides_per_day": 10,
        "max_override_duration_seconds": 600,
        "penalty_per_extra_override_seconds": 0,
        "require_screenshot": False,
        "notify_parent": False,
    },
    "ENTERTAINMENT:NEUTRAL": {
        "max_cumulative_time_seconds": 900,
        "max_overrides_per_day": 3,
        "max_override_duration_seconds": 300,
        "penalty_per_extra_override_seconds": 60,
        "require_screenshot": False,
        "notify_parent": False,
    },
    "ENTERTAINMENT:DISTRACTION": {
        "max_cumulative_time_seconds": 600,
        "max_overrides_per_day": 2,
        "max_override_duration_seconds": 300,
        "penalty_per_extra_override_seconds": 120,
        "require_screenshot": True,
        "notify_parent": True,
    },
    "GAMING:NEUTRAL": {
        "max_cumulative_time_seconds": 600,
        "max_overrides_per_day": 2,
        "max_override_duration_seconds": 300,
        "penalty_per_extra_override_seconds": 90,
        "require_screenshot": False,
        "notify_parent": False,
    },
    "GAMING:DISTRACTION": {
        "max_cumulative_time_seconds": 300,
        "max_overrides_per_day": 1,
        "max_override_duration_seconds": 300,
        "penalty_per_extra_override_seconds": 180,
        "require_screenshot": True,
        "notify_parent": True,
    },
    "SOCIAL_MEDIA:DISTRACTION": {
        "max_cumulative_time_seconds": 600,
        "max_overrides_per_day": 2,
        "max_override_duration_seconds": 300,
        "penalty_per_extra_override_seconds": 120,
        "require_screenshot": True,
        "notify_parent": True,
    },
    "UNKNOWN:NEUTRAL": {
        "max_cumulative_time_seconds": 900,
        "max_overrides_per_day": 3,
        "max_override_duration_seconds": 300,
        "penalty_per_extra_override_seconds": 60,
        "require_screenshot": False,
        "notify_parent": False,
    },
}

_DEFAULT_MASTER_BUDGET: Dict[str, Any] = {
    "max_total_distraction_seconds": 2700,
    "warning_threshold_percent": 70.0,
    "categories_to_track": ["ENTERTAINMENT", "GAMING", "SOCIAL_MEDIA", "ADULT"],
    "usefulness_to_track": ["DISTRACTION", "NEUTRAL"],
}

_DEFAULT_PER_DOMAIN_RULES: Dict[str, Dict[str, Any]] = {}

# Category name normalisation map (old fragmented names → canonical)
CATEGORY_NORMALIZE: Dict[str, str] = {
    "social": "social_media",
    "SOCIAL_MEDIA": "social_media",
    "ENTERTAINMENT": "entertainment",
    "GAMING": "gaming",
    "SHOPPING": "shopping",
    "NEWS": "news",
    "EDUCATION": "education",
    "PRODUCTIVITY": "productivity",
    "TECHNOLOGY": "development",
    "ADULT": "adult",
}

# Map from lowercase category key → uppercase enum used by classifier
CATEGORY_TO_ENUM: Dict[str, str] = {
    "work": "PRODUCTIVITY",
    "social_media": "SOCIAL_MEDIA",
    "entertainment": "ENTERTAINMENT",
    "gaming": "GAMING",
    "shopping": "SHOPPING",
    "news": "NEWS",
    "email": "PRODUCTIVITY",
    "development": "TECHNOLOGY",
    "productivity": "PRODUCTIVITY",
    "education": "EDUCATION",
    "adult": "ADULT",
}


def _posix_domain_config_default() -> Path:
    return Path.home() / ".focus_guard" / "domain_config.json"


def _programdata_domain_config_path() -> Path:
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "FocusGuard" / "domain_config.json"


def _localappdata_domain_config_path() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip()
    if base:
        return Path(base) / "FocusGuard" / "domain_config.json"
    return Path.home() / "AppData" / "Local" / "FocusGuard" / "domain_config.json"


def _use_localappdata_marker_path() -> Path:
    """When present, newer runs always use LOCALAPPDATA domain_config.json."""

    return _localappdata_domain_config_path().parent / ".domain_config_use_localappdata"


def _windows_domain_file_user_can_modify(path: Path) -> bool:
    """True if this account can persist config the same way :meth:`_save` does.

    Opening an existing JSON with ``r+b`` is not sufficient: saves use a new
    sibling ``*.tmp`` plus ``os.replace``. Some ProgramData ACLs allow read/write
    on the existing file but deny **creating** new files in the folder, which
    yields WinError 5 on ``domain_config.tmp``.
    """
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            probe = parent / "__fg_domain_write_probe.tmp"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
            return True
        with open(path, "r+b"):
            pass
        probe = parent / f"__fg_atomic_write_probe_{os.getpid()}.tmp"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _copy_domain_config_fallback(src: Path, dst: Path) -> None:
    try:
        shutil.copyfile(src, dst)
        return
    except OSError:
        pass
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _default_config_path() -> Path:
    """Return writable domain_config.json path.

    Prefer ProgramData for shared installs when ACL allows writes. When an
    existing ProgramData JSON is Administrator-locked against normal users,
    mirror to LOCALAPPDATA and pin that choice via a marker file.
    """
    if os.name != "nt":
        return _posix_domain_config_default()

    prog = _programdata_domain_config_path()
    loc = _localappdata_domain_config_path()
    marker = _use_localappdata_marker_path()

    if marker.exists():
        loc.parent.mkdir(parents=True, exist_ok=True)
        if loc.exists():
            return loc
        if prog.exists():
            try:
                _copy_domain_config_fallback(prog, loc)
            except OSError as e:
                logger.error(
                    "LOCALAPPDATA domain mirror missing and could not be created (%s)",
                    e,
                )
        if loc.exists():
            return loc
        marker.unlink(missing_ok=True)

    if prog.exists():
        if _windows_domain_file_user_can_modify(prog):
            prog.parent.mkdir(parents=True, exist_ok=True)
            return prog
        loc.parent.mkdir(parents=True, exist_ok=True)
        if not loc.exists():
            try:
                _copy_domain_config_fallback(prog, loc)
            except OSError as e:
                logger.error(
                    "ProgramData domain config is not writable (%s); could not mirror to %s: %s",
                    prog,
                    loc,
                    e,
                )
                return prog
        try:
            marker.write_text("", encoding="utf-8")
        except OSError:
            pass
        logger.warning(
            "Using per-user domain config at %s (ProgramData copy is restricted for this account).",
            loc,
        )
        return loc

    try:
        prog.parent.mkdir(parents=True, exist_ok=True)
        probe = prog.parent / "__fg_progdata_probe.tmp"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return prog
    except OSError:
        loc.parent.mkdir(parents=True, exist_ok=True)
        try:
            marker.write_text("", encoding="utf-8")
        except OSError:
            pass
        logger.warning(
            "ProgramData is not writable; using per-user domain config at %s",
            loc,
        )
        return loc


def _build_default_data() -> Dict[str, Any]:
    """Build the full default config dict."""
    return {
        "version": 1,
        "domain_categories": {k: list(v) for k, v in _DEFAULT_DOMAIN_CATEGORIES.items()},
        "always_allowed_domains": list(_DEFAULT_ALWAYS_ALLOWED_DOMAINS),
        "always_allowed_categories": list(_DEFAULT_ALWAYS_ALLOWED_CATEGORIES),
        "blocked_categories": list(_DEFAULT_BLOCKED_CATEGORIES),
        "system_whitelist": list(_DEFAULT_SYSTEM_WHITELIST),
        "per_domain_rules": dict(_DEFAULT_PER_DOMAIN_RULES),
        "classification_budgets": {k: dict(v) for k, v in _DEFAULT_CLASSIFICATION_BUDGETS.items()},
        "master_budget": dict(_DEFAULT_MASTER_BUDGET),
    }


# ---------------------------------------------------------------------------
# Subdomain-aware domain matching utilities
# ---------------------------------------------------------------------------

def matches_domain(query: str, known: str) -> bool:
    """Check if *query* matches *known* exactly or is a subdomain of it.

    Examples:
        matches_domain("stanfordohs.pronto.io", "pronto.io")  -> True
        matches_domain("pronto.io", "pronto.io")              -> True
        matches_domain("notpronto.io", "pronto.io")           -> False
        matches_domain("mail.google.com", "google.com")       -> True
        matches_domain("google.com", "mail.google.com")       -> False
    """
    query = query.lower()
    known = known.lower()
    if query == known:
        return True
    return query.endswith("." + known)


def find_matching_domain(query: str, domain_set) -> Optional[str]:
    """Return the first entry in *domain_set* that *query* matches (exact or subdomain).

    Returns None if no match.
    """
    query = query.lower()
    for d in domain_set:
        if matches_domain(query, d):
            return d
    return None


# ---------------------------------------------------------------------------
# DomainConfigManager
# ---------------------------------------------------------------------------

class DomainConfigManager:
    """Thread-safe singleton that owns all domain configuration.

    Reads/writes ``domain_config.json`` and exposes helpers used by every
    component that previously had its own hardcoded domain lists.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._config_path = config_path or _default_config_path()
        self._hash_path = self._config_path.with_suffix(".hash")
        self._data: Dict[str, Any] = {}
        self._last_mtime: float = 0.0
        self._dirty: bool = False
        self._change_callbacks: List[Callable[[], None]] = []
        self._last_known_good: Optional[Dict[str, Any]] = None
        self._tamper_count: int = 0

        # Ensure parent dir exists
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create
        self._load_or_create()

        # Register atexit flush
        atexit.register(self._flush_if_dirty)

        logger.info(
            "DomainConfigManager initialised from %s (%d categories, %d always-allowed)",
            self._config_path,
            len(self._data.get("domain_categories", {})),
            len(self._data.get("always_allowed_domains", [])),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_or_create(self) -> None:
        """Load from disk or create with defaults."""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                self._last_mtime = self._config_path.stat().st_mtime
                logger.debug("Loaded domain config from %s", self._config_path)
                # Ensure all keys present (forward-compat)
                defaults = _build_default_data()
                for key, val in defaults.items():
                    if key not in self._data:
                        self._data[key] = val
                        self._dirty = True
                if self._dirty:
                    self._save()
                return
            except Exception as e:
                logger.warning("Failed to load domain config, recreating: %s", e)

        # Create with defaults
        self._data = _build_default_data()
        self._save()

    def _compute_hash(self, data_bytes: bytes) -> str:
        """Compute SHA-256 hash of config content."""
        return hashlib.sha256(data_bytes).hexdigest()

    def _save_hash(self, content_bytes: bytes) -> None:
        """Save integrity hash to sibling .hash file."""
        try:
            h = self._compute_hash(content_bytes)
            self._hash_path.write_text(h, encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save config hash: %s", e)

    def _verify_integrity(self, content_bytes: bytes) -> bool:
        """Verify config content against stored hash.

        Returns True if hash matches or no hash file exists yet.
        Returns False if tampered (hash mismatch).
        """
        if not self._hash_path.exists():
            return True  # First run, no hash yet
        try:
            stored_hash = self._hash_path.read_text(encoding="utf-8").strip()
            actual_hash = self._compute_hash(content_bytes)
            if stored_hash == actual_hash:
                return True
            # Tamper detected!
            self._tamper_count += 1
            logger.warning(
                "CONFIG TAMPER DETECTED: domain_config.json hash mismatch "
                "(stored=%s, actual=%s, tamper_count=%d)",
                stored_hash[:12], actual_hash[:12], self._tamper_count,
            )
            self._fire_tamper_alert(stored_hash, actual_hash)
            return False
        except Exception as e:
            logger.warning("Could not verify config integrity: %s", e)
            return True  # Don't block on read errors

    def _config_is_under_system_temp(self) -> bool:
        """True when config lives under a system temp directory.

        Pytest and ``scripts/test_section8_mitigations.py`` intentionally tamper with a
        temp ``domain_config.json``; we must not send real SMTP alerts for that path.

        Checks ``tempfile.gettempdir()`` plus ``TEMP`` / ``TMP`` / ``TMPDIR`` and uses
        ``Path.is_relative_to`` so Windows short paths and alternate env layouts still
        resolve under the same logical temp root.
        """
        try:
            p = self._config_path.resolve()
            roots: List[Path] = []
            roots.append(Path(tempfile.gettempdir()).resolve())
            for key in ("TEMP", "TMP", "TMPDIR"):
                raw = os.environ.get(key)
                if raw:
                    try:
                        roots.append(Path(raw).resolve())
                    except Exception:
                        continue
            seen: Set[str] = set()
            unique_roots: List[Path] = []
            for r in roots:
                key = str(r).casefold()
                if key not in seen:
                    seen.add(key)
                    unique_roots.append(r)
            for root in unique_roots:
                try:
                    if p == root or p.is_relative_to(root):
                        return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def _fire_tamper_alert(self, expected_hash: str, actual_hash: str) -> None:
        """Log audit event and send email alert on config tampering."""
        if self._config_is_under_system_temp():
            logger.debug(
                "Tamper alert skipped for temp-dir domain config (typical of tests): %s",
                self._config_path,
            )
            return

        try:
            from focus_guard.core.browser_v2.tab_server.audit_logger import get_audit_logger
            get_audit_logger().log_event(
                event_type="config_tamper_detected",
                domain="",
                details={
                    "file": str(self._config_path),
                    "expected_hash": expected_hash[:16],
                    "actual_hash": actual_hash[:16],
                    "tamper_count": self._tamper_count,
                    "message": "domain_config.json was modified outside of FocusGuard. "
                               "This may indicate an attempt to bypass blocking rules.",
                },
            )
        except Exception:
            pass

        # Email alert (best-effort)
        try:
            from focus_guard.deployment.config import DeploymentConfig
            import smtplib
            from email.mime.text import MIMEText

            config = DeploymentConfig.load()
            if not config.email.is_configured():
                return

            subject = "[FocusGuard ALERT] Config file tampered"
            body = (
                f"The FocusGuard domain configuration file was modified outside of "
                f"the application.\n\n"
                f"File: {self._config_path}\n"
                f"Expected hash: {expected_hash[:16]}...\n"
                f"Actual hash:   {actual_hash[:16]}...\n"
                f"Tamper count:  {self._tamper_count}\n"
                f"Machine: {config.machine_name}\n"
                f"User: {config.user_name}\n"
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"The previous known-good configuration has been restored."
            )

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = config.email.sender_email
            msg["To"] = ", ".join(config.email.recipients)

            with smtplib.SMTP(config.email.smtp_server, config.email.smtp_port) as server:
                if config.email.use_tls:
                    server.starttls()
                server.login(config.email.smtp_username, config.email.smtp_password)
                server.send_message(msg)
            logger.info("Sent config tamper email alert")
        except Exception as e:
            logger.debug("Could not send tamper email alert: %s", e)

    def _save(self) -> None:
        """Atomic save via temp file + replace, with in-place fallback for strict ACL."""
        try:
            content_bytes = json.dumps(self._data, indent=2, sort_keys=False).encode("utf-8")
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._config_path.with_suffix(".tmp")
            tmp_path.write_bytes(content_bytes)
            try:
                os.replace(tmp_path, self._config_path)
            except OSError:
                with open(self._config_path, "wb") as fp:
                    fp.write(content_bytes)
                tmp_path.unlink(missing_ok=True)
            self._last_mtime = self._config_path.stat().st_mtime
            self._dirty = False
            self._save_hash(content_bytes)
            self._last_known_good = json.loads(content_bytes)
            logger.debug("Saved domain config to %s", self._config_path)
        except Exception as e:
            logger.error("Failed to save domain config: %s", e)

    def _flush_if_dirty(self) -> None:
        """Flush pending changes (called by atexit)."""
        with self._lock:
            if self._dirty:
                self._save()

    def reload_if_changed(self) -> bool:
        """Reload from disk if the file was modified externally. Returns True if reloaded.

        Verifies integrity hash before accepting the new content.  If the
        hash does not match (tamper detected), the last known good config
        is restored and an alert is fired.
        """
        with self._lock:
            try:
                if not self._config_path.exists():
                    return False
                mtime = self._config_path.stat().st_mtime
                if mtime > self._last_mtime:
                    content_bytes = self._config_path.read_bytes()
                    if not self._verify_integrity(content_bytes):
                        # Tamper detected — revert to last known good
                        if self._last_known_good is not None:
                            logger.warning("Reverting to last known good config")
                            self._data = json.loads(json.dumps(self._last_known_good))
                            self._save()  # Re-save the good config + update hash
                            return True
                        # No known good — accept but warn
                        logger.warning("No last-known-good config to revert to")
                    self._data = json.loads(content_bytes)
                    self._last_mtime = mtime
                    self._dirty = False
                    self._last_known_good = json.loads(json.dumps(self._data))
                    logger.info("Reloaded domain config (external change detected)")
                    self._notify_change()
                    return True
            except Exception as e:
                logger.warning("Failed to reload domain config: %s", e)
            return False

    def save(self) -> None:
        """Explicitly save current state to disk."""
        with self._lock:
            self._save()

    # ------------------------------------------------------------------
    # Change notification
    # ------------------------------------------------------------------

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register a callback for config changes."""
        self._change_callbacks.append(callback)

    def _notify_change(self) -> None:
        for cb in self._change_callbacks:
            try:
                cb()
            except Exception as e:
                logger.warning("Change callback error: %s", e)

    def _mark_dirty_and_save(self) -> None:
        """Mark dirty, save, and notify."""
        self._dirty = True
        self._save()
        self._notify_change()

    # ------------------------------------------------------------------
    # Domain Categories
    # ------------------------------------------------------------------

    def get_domain_categories(self) -> Dict[str, List[str]]:
        """Return all domain categories."""
        with self._lock:
            return {k: list(v) for k, v in self._data.get("domain_categories", {}).items()}

    def get_domains_for_category(self, category: str) -> List[str]:
        with self._lock:
            return list(self._data.get("domain_categories", {}).get(category, []))

    def get_category_for_domain(self, domain: str) -> Optional[str]:
        """Return the category a domain belongs to, or None.

        Uses subdomain-aware matching so that e.g.
        ``stanfordohs.pronto.io`` matches the ``pronto.io`` entry.
        """
        domain = domain.lower()
        with self._lock:
            for cat, domains in self._data.get("domain_categories", {}).items():
                if find_matching_domain(domain, domains) is not None:
                    return cat
        return None

    def add_domain_to_category(self, domain: str, category: str) -> None:
        """Add a domain to a category (removes from any other category first)."""
        domain = domain.lower()
        with self._lock:
            cats = self._data.setdefault("domain_categories", {})
            # Remove from any existing category
            for cat, domains in cats.items():
                if domain in domains:
                    domains.remove(domain)
            # Add to target
            cats.setdefault(category, [])
            if domain not in cats[category]:
                cats[category].append(domain)
            self._mark_dirty_and_save()

    def remove_domain_from_category(self, domain: str, category: str) -> bool:
        domain = domain.lower()
        with self._lock:
            cats = self._data.get("domain_categories", {})
            if category in cats and domain in cats[category]:
                cats[category].remove(domain)
                self._mark_dirty_and_save()
                return True
            return False

    def move_domains_to_category(self, domains: List[str], category: str) -> None:
        """Move multiple domains to a category."""
        for d in domains:
            self.add_domain_to_category(d, category)

    # ------------------------------------------------------------------
    # Always-allowed domains
    # ------------------------------------------------------------------

    def get_always_allowed_domains(self) -> Set[str]:
        with self._lock:
            return set(self._data.get("always_allowed_domains", []))

    def add_always_allowed_domain(self, domain: str) -> None:
        domain = domain.lower()
        with self._lock:
            lst = self._data.setdefault("always_allowed_domains", [])
            if domain not in lst:
                lst.append(domain)
                self._mark_dirty_and_save()

    def remove_always_allowed_domain(self, domain: str) -> bool:
        domain = domain.lower()
        with self._lock:
            lst = self._data.get("always_allowed_domains", [])
            if domain in lst:
                lst.remove(domain)
                self._mark_dirty_and_save()
                return True
            return False

    # ------------------------------------------------------------------
    # Blocked / allowed categories
    # ------------------------------------------------------------------

    def get_blocked_categories(self) -> Set[str]:
        with self._lock:
            return set(self._data.get("blocked_categories", []))

    def get_always_allowed_categories(self) -> Set[str]:
        with self._lock:
            return set(self._data.get("always_allowed_categories", []))

    # ------------------------------------------------------------------
    # System whitelist (CDNs, OS domains)
    # ------------------------------------------------------------------

    def get_system_whitelist(self) -> Set[str]:
        with self._lock:
            return set(self._data.get("system_whitelist", []))

    # ------------------------------------------------------------------
    # Per-domain rules
    # ------------------------------------------------------------------

    def get_per_domain_rules(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._data.get("per_domain_rules", {}))

    def get_per_domain_rule(self, domain: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._data.get("per_domain_rules", {}).get(domain.lower())

    def set_per_domain_rule(self, domain: str, rule: Dict[str, Any]) -> None:
        domain = domain.lower()
        with self._lock:
            self._data.setdefault("per_domain_rules", {})[domain] = rule
            self._mark_dirty_and_save()

    def remove_per_domain_rule(self, domain: str) -> bool:
        domain = domain.lower()
        with self._lock:
            rules = self._data.get("per_domain_rules", {})
            if domain in rules:
                del rules[domain]
                self._mark_dirty_and_save()
                return True
            return False

    # ------------------------------------------------------------------
    # Classification budgets
    # ------------------------------------------------------------------

    def get_classification_budgets(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._data.get("classification_budgets", {}))

    def get_classification_budget(self, key: str) -> Optional[Dict[str, Any]]:
        """Get budget for a key like 'ENTERTAINMENT:DISTRACTION'."""
        with self._lock:
            return self._data.get("classification_budgets", {}).get(key)

    def set_classification_budget(self, key: str, budget: Dict[str, Any]) -> None:
        with self._lock:
            self._data.setdefault("classification_budgets", {})[key] = budget
            self._mark_dirty_and_save()

    # ------------------------------------------------------------------
    # Master budget
    # ------------------------------------------------------------------

    def get_master_budget(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data.get("master_budget", _DEFAULT_MASTER_BUDGET))

    def set_master_budget(self, budget: Dict[str, Any]) -> None:
        with self._lock:
            self._data["master_budget"] = budget
            self._mark_dirty_and_save()

    # ------------------------------------------------------------------
    # Convenience: full snapshot for API
    # ------------------------------------------------------------------

    def get_full_config(self) -> Dict[str, Any]:
        """Return the entire config as a dict (deep copy)."""
        with self._lock:
            return json.loads(json.dumps(self._data))

    # ------------------------------------------------------------------
    # Convenience: domain status helpers
    # ------------------------------------------------------------------

    def get_domain_status(self, domain: str) -> str:
        """Return 'allowed', 'blocked', or 'budgeted' for a domain.

        Uses subdomain-aware matching.
        """
        domain = domain.lower()
        if find_matching_domain(domain, self.get_always_allowed_domains()):
            return "allowed"
        if find_matching_domain(domain, self.get_system_whitelist()):
            return "allowed"
        cat = self.get_category_for_domain(domain)
        if cat:
            enum_cat = CATEGORY_TO_ENUM.get(cat, cat.upper())
            if enum_cat in self.get_blocked_categories():
                return "blocked"
            if enum_cat in self.get_always_allowed_categories():
                return "allowed"
        if self.get_per_domain_rule(domain):
            return "budgeted"
        return "unknown"

    def get_all_known_domains(self) -> List[Dict[str, Any]]:
        """Return a list of all known domains with their metadata."""
        result: Dict[str, Dict[str, Any]] = {}

        # From categories
        for cat, domains in self.get_domain_categories().items():
            for d in domains:
                result[d] = {
                    "domain": d,
                    "category": cat,
                    "category_enum": CATEGORY_TO_ENUM.get(cat, cat.upper()),
                    "status": self.get_domain_status(d),
                }

        # From always-allowed
        for d in self.get_always_allowed_domains():
            if d not in result:
                result[d] = {
                    "domain": d,
                    "category": self.get_category_for_domain(d) or "unknown",
                    "category_enum": "PRODUCTIVITY",
                    "status": "allowed",
                }

        # Add per-domain rule info
        for d, rule in self.get_per_domain_rules().items():
            if d in result:
                result[d]["per_domain_rule"] = rule
            else:
                result[d] = {
                    "domain": d,
                    "category": self.get_category_for_domain(d) or "unknown",
                    "category_enum": "UNKNOWN",
                    "status": "budgeted",
                    "per_domain_rule": rule,
                }

        return sorted(result.values(), key=lambda x: (x["category"], x["domain"]))


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: Optional[DomainConfigManager] = None
_instance_lock = threading.Lock()


def get_domain_config_manager(
    config_path: Optional[Path] = None,
) -> DomainConfigManager:
    """Get or create the singleton DomainConfigManager."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = DomainConfigManager(config_path)
        return _instance


def reset_domain_config_manager() -> None:
    """Reset the singleton (for testing)."""
    global _instance
    with _instance_lock:
        _instance = None
