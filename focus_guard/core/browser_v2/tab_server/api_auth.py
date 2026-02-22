"""API authentication for the tab server.

Generates and validates bearer tokens for mutation endpoints.
The token is generated once at first run and persisted to a secure location.
The browser extension reads this token at install time to authenticate requests.

Security model:
- GET endpoints: No auth required (read-only, informational)
- POST/DELETE endpoints: Require valid bearer token
- Token stored in ProgramData (admin-writable, user-readable)
- All unauthorized attempts are logged to the audit trail
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Token length in bytes (32 bytes = 256 bits of entropy)
_TOKEN_BYTES = 32

# Default token file location
_DEFAULT_TOKEN_DIR = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "FocusGuard"
_TOKEN_FILENAME = "api_token.json"


class APIAuthManager:
    """Manages API authentication tokens for the tab server.
    
    The token is a random hex string generated on first run.
    It is stored in a JSON file alongside metadata (creation time, version).
    """

    def __init__(self, token_dir: Optional[Path] = None) -> None:
        self._token_dir = token_dir or _DEFAULT_TOKEN_DIR
        self._token_path = self._token_dir / _TOKEN_FILENAME
        self._token: Optional[str] = None
        self._token_hash: Optional[str] = None
        self._created_at: Optional[float] = None
        self._unauthorized_attempts: int = 0
        self._last_unauthorized_time: float = 0.0

    @property
    def token(self) -> str:
        """Get the current API token, generating one if needed."""
        if self._token is None:
            self._load_or_generate()
        return self._token

    @property
    def token_path(self) -> Path:
        """Path to the token file."""
        return self._token_path

    @property
    def unauthorized_attempts(self) -> int:
        """Number of unauthorized access attempts since startup."""
        return self._unauthorized_attempts

    def _load_or_generate(self) -> None:
        """Load existing token from disk or generate a new one."""
        if self._token_path.exists():
            try:
                with open(self._token_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._token = data["token"]
                self._token_hash = data.get("token_hash", "")
                self._created_at = data.get("created_at", 0)
                logger.info("Loaded API token from %s", self._token_path)
                return
            except (json.JSONDecodeError, KeyError, OSError) as e:
                logger.warning("Failed to load API token: %s — regenerating", e)

        self._generate_and_save()

    def _generate_and_save(self) -> None:
        """Generate a new random token and save to disk."""
        self._token = secrets.token_hex(_TOKEN_BYTES)
        self._token_hash = hashlib.sha256(self._token.encode()).hexdigest()
        self._created_at = time.time()

        data = {
            "token": self._token,
            "token_hash": self._token_hash,
            "created_at": self._created_at,
            "version": 1,
            "description": "FocusGuard API authentication token. "
                           "The browser extension needs this token to make changes.",
        }

        try:
            self._token_dir.mkdir(parents=True, exist_ok=True)
            with open(self._token_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Generated new API token at %s", self._token_path)
        except OSError as e:
            logger.error("Failed to save API token to %s: %s", self._token_path, e)

    def validate_token(self, provided_token: str) -> bool:
        """Validate a provided token against the stored token.
        
        Uses constant-time comparison to prevent timing attacks.
        
        Args:
            provided_token: The token string from the Authorization header.
            
        Returns:
            True if the token is valid.
        """
        if not provided_token:
            self._record_unauthorized("empty_token")
            return False

        expected = self.token
        is_valid = hmac.compare_digest(provided_token, expected)

        if not is_valid:
            self._record_unauthorized("invalid_token")

        return is_valid

    def validate_request(self, authorization_header: Optional[str]) -> bool:
        """Validate an HTTP Authorization header.
        
        Expected format: "Bearer <token>"
        
        Args:
            authorization_header: The full Authorization header value.
            
        Returns:
            True if the request is authorized.
        """
        if not authorization_header:
            self._record_unauthorized("missing_header")
            return False

        parts = authorization_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            self._record_unauthorized("malformed_header")
            return False

        return self.validate_token(parts[1])

    def _record_unauthorized(self, reason: str) -> None:
        """Record an unauthorized access attempt."""
        self._unauthorized_attempts += 1
        self._last_unauthorized_time = time.time()
        logger.warning(
            "Unauthorized API access attempt #%d: %s",
            self._unauthorized_attempts,
            reason,
        )

        # Log to audit trail
        try:
            from .audit_logger import get_audit_logger
            get_audit_logger().log_event(
                event_type="unauthorized_api_access",
                domain="",
                details={
                    "reason": reason,
                    "attempt_number": self._unauthorized_attempts,
                    "timestamp": self._last_unauthorized_time,
                },
            )
        except Exception:
            pass

    def get_status(self) -> dict:
        """Get auth manager status for diagnostics."""
        return {
            "token_path": str(self._token_path),
            "token_exists": self._token_path.exists(),
            "token_loaded": self._token is not None,
            "created_at": self._created_at,
            "unauthorized_attempts": self._unauthorized_attempts,
            "last_unauthorized_time": self._last_unauthorized_time,
        }

    def regenerate_token(self) -> str:
        """Regenerate the API token. Returns the new token.
        
        This invalidates all existing sessions/extensions until they
        receive the new token.
        """
        logger.info("Regenerating API token (old token invalidated)")
        self._generate_and_save()
        return self._token


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[APIAuthManager] = None


def get_api_auth_manager(token_dir: Optional[Path] = None) -> APIAuthManager:
    """Get or create the singleton APIAuthManager."""
    global _instance
    if _instance is None:
        _instance = APIAuthManager(token_dir=token_dir)
    return _instance


def reset_api_auth_manager() -> None:
    """Reset the singleton (for testing)."""
    global _instance
    _instance = None
