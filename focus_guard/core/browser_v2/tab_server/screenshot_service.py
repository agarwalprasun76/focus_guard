"""Screenshot service for accountability logging.

This module provides screenshot capture functionality for auditing override
requests on distracting content.
"""

from __future__ import annotations

import base64
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotRecord:
    """Record of a captured screenshot."""
    id: str
    timestamp: float
    domain: str
    url: str
    classification_category: str
    classification_usefulness: str
    override_id: Optional[str]
    file_path: Optional[Path] = None
    base64_data: Optional[str] = None  # For email attachment
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "domain": self.domain,
            "url": self.url,
            "classification_category": self.classification_category,
            "classification_usefulness": self.classification_usefulness,
            "override_id": self.override_id,
            "file_path": str(self.file_path) if self.file_path else None,
            "has_base64": self.base64_data is not None,
            "metadata": self.metadata,
        }


class ScreenshotService:
    """Service for capturing and managing screenshots for accountability.
    
    Features:
    - Captures screenshots on demand
    - Stores screenshots with metadata
    - Provides base64 encoding for email attachments
    - Manages storage and cleanup
    """
    
    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        max_screenshots_per_day: int = 50,
        keep_days: int = 7,
    ):
        """Initialize the screenshot service.
        
        Args:
            storage_dir: Directory to store screenshots
            max_screenshots_per_day: Maximum screenshots to keep per day
            keep_days: Number of days to keep screenshots
        """
        self._lock = threading.Lock()
        self._storage_dir = storage_dir or Path.home() / ".focus_guard" / "screenshots"
        self._max_per_day = max_screenshots_per_day
        self._keep_days = keep_days
        
        # Track screenshots taken today
        self._daily_count: int = 0
        self._daily_reset_date: str = ""
        
        # Recent screenshots for quick access
        self._recent_screenshots: List[ScreenshotRecord] = []
        self._max_recent = 10
        
        # Ensure storage directory exists
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("ScreenshotService initialized, storage: %s", self._storage_dir)
    
    def _reset_daily_if_needed(self) -> None:
        """Reset daily count if it's a new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._daily_reset_date != today:
            self._daily_count = 0
            self._daily_reset_date = today
            # Clean up old screenshots
            self._cleanup_old_screenshots()
    
    def _cleanup_old_screenshots(self) -> None:
        """Remove screenshots older than keep_days."""
        try:
            cutoff = time.time() - (self._keep_days * 24 * 60 * 60)
            for file_path in self._storage_dir.glob("screenshot_*.png"):
                if file_path.stat().st_mtime < cutoff:
                    file_path.unlink()
                    logger.debug("Deleted old screenshot: %s", file_path)
        except Exception as e:
            logger.warning("Error cleaning up old screenshots: %s", e)
    
    def capture(
        self,
        domain: str,
        url: str,
        classification_category: str,
        classification_usefulness: str,
        override_id: Optional[str] = None,
        save_to_file: bool = True,
        include_base64: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ScreenshotRecord]:
        """Capture a screenshot for accountability.
        
        Args:
            domain: Domain being accessed
            url: Full URL
            classification_category: Content category (EDUCATION, ENTERTAINMENT, etc.)
            classification_usefulness: Usefulness level (EDUCATIONAL, DISTRACTION, etc.)
            override_id: Associated override ID
            save_to_file: Whether to save to disk
            include_base64: Whether to include base64 data (for email)
            metadata: Additional metadata to store
            
        Returns:
            ScreenshotRecord if successful, None otherwise
        """
        with self._lock:
            self._reset_daily_if_needed()
            
            # Check daily limit
            if self._daily_count >= self._max_per_day:
                logger.warning("Daily screenshot limit reached (%d)", self._max_per_day)
                return None
            
            try:
                # Import PIL for screenshot
                from PIL import ImageGrab
                
                # Generate unique ID
                import uuid
                screenshot_id = str(uuid.uuid4())[:8]
                timestamp = time.time()
                
                # Capture the screen
                screenshot = ImageGrab.grab()
                
                # Prepare file path
                file_path = None
                if save_to_file:
                    date_str = datetime.now().strftime("%Y%m%d")
                    time_str = datetime.now().strftime("%H%M%S")
                    filename = f"screenshot_{date_str}_{time_str}_{screenshot_id}.png"
                    file_path = self._storage_dir / filename
                    screenshot.save(file_path)
                    logger.debug("Screenshot saved to %s", file_path)
                
                # Encode as base64 if requested
                base64_data = None
                if include_base64:
                    import io
                    buffer = io.BytesIO()
                    screenshot.save(buffer, format="PNG")
                    base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                # Create record
                record = ScreenshotRecord(
                    id=screenshot_id,
                    timestamp=timestamp,
                    domain=domain,
                    url=url,
                    classification_category=classification_category,
                    classification_usefulness=classification_usefulness,
                    override_id=override_id,
                    file_path=file_path,
                    base64_data=base64_data,
                    metadata=metadata or {},
                )
                
                # Update tracking
                self._daily_count += 1
                self._recent_screenshots.append(record)
                if len(self._recent_screenshots) > self._max_recent:
                    self._recent_screenshots.pop(0)
                
                logger.info(
                    "Screenshot captured: id=%s, domain=%s, category=%s, usefulness=%s",
                    screenshot_id, domain, classification_category, classification_usefulness
                )
                
                return record
                
            except ImportError:
                logger.error("PIL not available for screenshot capture")
                return None
            except Exception as e:
                logger.error("Failed to capture screenshot: %s", e)
                return None
    
    def get_recent_screenshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent screenshot records (without base64 data)."""
        with self._lock:
            return [
                {**s.to_dict(), "base64_data": None}  # Exclude base64 for listing
                for s in self._recent_screenshots[-limit:]
            ]
    
    def get_screenshot_by_id(self, screenshot_id: str) -> Optional[ScreenshotRecord]:
        """Get a specific screenshot by ID."""
        with self._lock:
            for record in self._recent_screenshots:
                if record.id == screenshot_id:
                    return record
        return None
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily screenshot statistics."""
        with self._lock:
            self._reset_daily_if_needed()
            return {
                "date": self._daily_reset_date,
                "count": self._daily_count,
                "limit": self._max_per_day,
                "remaining": self._max_per_day - self._daily_count,
            }


# Singleton instance
_screenshot_service: Optional[ScreenshotService] = None
_service_lock = threading.Lock()


def get_screenshot_service() -> ScreenshotService:
    """Get or create the singleton ScreenshotService instance."""
    global _screenshot_service
    with _service_lock:
        if _screenshot_service is None:
            _screenshot_service = ScreenshotService()
        return _screenshot_service


def reset_screenshot_service() -> None:
    """Reset the singleton (for testing)."""
    global _screenshot_service
    with _service_lock:
        _screenshot_service = None
