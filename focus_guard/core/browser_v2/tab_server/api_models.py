"""Typed data models for browser_v2 tab server APIs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class BrowserFamily(str, Enum):
    """Supported browser families for v2 integration."""

    CHROME = "chrome"
    EDGE = "edge"
    # Placeholder for macOS Phase 2 expansion
    SAFARI = "safari"


@dataclass(slots=True)
class TabInfo:
    """Represents a browser tab snapshot reported by the extension."""

    id: str
    url: str
    title: str
    browser: BrowserFamily
    window_id: Optional[str] = None
    active: bool = False
    audible: bool = False
    muted: bool = False
    incognito: bool = False
    last_updated: Optional[float] = None
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BrowserStatus:
    """Health information for a connected browser instance."""

    browser: BrowserFamily
    connected: bool
    last_heartbeat: Optional[float] = None
    extension_version: Optional[str] = None
    errors: List[str] = field(default_factory=list)


@dataclass(slots=True)
class TabsSnapshot:
    """Aggregate payload returned by `/api/tabs`."""

    tabs: List[TabInfo]
    browsers: List[BrowserStatus]
    generated_at: float


@dataclass(slots=True)
class CommandRequest:
    """Command payload delivered to the browser extension."""

    action: str
    tab_id: Optional[str] = None
    window_id: Optional[str] = None
    browser: Optional[BrowserFamily] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CommandResult:
    """Result of executing a command."""

    success: bool
    action: str
    tab_id: Optional[str] = None
    browser: Optional[BrowserFamily] = None
    message: Optional[str] = None
