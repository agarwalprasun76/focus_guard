"""
Unit tests for the TabBlocker class.

This module contains tests for the TabBlocker class in core.browser.adapter.
"""

import unittest
import time
from unittest.mock import patch, MagicMock, call
import pytest
from datetime import datetime, timedelta

from focus_guard.core.browser.adapter import TabBlocker
from focus_guard.core.browser.models.tab import Tab


class TestTabBlocker:
    """Test cases for the TabBlocker class."""

    @pytest.fixture
    def tab_blocker(self):
        """Create a TabBlocker instance for testing."""
        return TabBlocker()

    @pytest.fixture
    def mock_tab(self):
        """Create a mock tab for testing."""
        return Tab(
            id=1,
            window_id=1,
            url="https://example.com",
            title="Example Domain",
            browser_id="chrome-12345",
            domain="example.com",
            is_active=True,
            created_at=datetime.now()
        )

    def test_block_domain_permanent(self, tab_blocker):
        """Test blocking a domain permanently."""
        # Block a domain permanently
        domain = "example.com"
        tab_blocker.block_domain(domain)
        
        # Verify the domain is blocked
        assert tab_blocker.is_domain_blocked(domain)
        
        # Verify the domain is in the blocked domains
        assert domain.lower() in tab_blocker._blocked_domains
        # Verify it's a permanent block (expiry time is None)
        assert tab_blocker._blocked_domains[domain.lower()] is None

    def test_block_domain_temporary(self, tab_blocker):
        """Test blocking a domain temporarily."""
        # Block a domain temporarily
        domain = "example.com"
        duration = 60  # seconds
        tab_blocker.block_domain(domain, duration)
        
        # Verify the domain is blocked
        assert tab_blocker.is_domain_blocked(domain)
        
        # Verify the domain is in the blocked domains
        assert domain.lower() in tab_blocker._blocked_domains
        
        # Verify the expiry time is set
        assert tab_blocker._blocked_domains[domain.lower()] is not None
        assert tab_blocker._blocked_domains[domain.lower()] > time.time()

    def test_unblock_domain_permanent(self, tab_blocker):
        """Test unblocking a permanently blocked domain."""
        # Block a domain permanently
        domain = "example.com"
        tab_blocker.block_domain(domain)
        
        # Verify the domain is blocked
        assert tab_blocker.is_domain_blocked(domain)
        
        # Unblock the domain by removing it from the dictionary
        if domain.lower() in tab_blocker._blocked_domains:
            del tab_blocker._blocked_domains[domain.lower()]
        
        # Verify the domain is no longer blocked
        assert not tab_blocker.is_domain_blocked(domain)
        
        # Verify the domain is not in the blocked domains
        assert domain.lower() not in tab_blocker._blocked_domains

    def test_unblock_domain_temporary(self, tab_blocker):
        """Test unblocking a temporarily blocked domain."""
        # Block a domain temporarily
        domain = "example.com"
        tab_blocker.block_domain(domain, 3600)  # 1 hour
        
        # Verify the domain is blocked
        assert tab_blocker.is_domain_blocked(domain)
        
        # Unblock the domain by removing it from the dictionary
        if domain.lower() in tab_blocker._blocked_domains:
            del tab_blocker._blocked_domains[domain.lower()]
        
        # Verify the domain is unblocked
        assert not tab_blocker.is_domain_blocked(domain)
        
        # Verify the domain is not in the blocked domains
        assert domain.lower() not in tab_blocker._blocked_domains

    def test_unblock_domain_not_blocked(self, tab_blocker):
        """Test unblocking a domain that is not blocked."""
        # Try to unblock a domain that is not blocked
        domain = "example.com"
        
        # Verify the domain is not blocked before
        assert not tab_blocker.is_domain_blocked(domain)
        
        # Try to remove it from the dictionary (should not raise an error)
        if domain.lower() in tab_blocker._blocked_domains:
            del tab_blocker._blocked_domains[domain.lower()]
        
        # Verify the domain is still not blocked
        assert not tab_blocker.is_domain_blocked(domain)

    def test_is_domain_blocked_permanent(self, tab_blocker):
        """Test is_domain_blocked with a permanently blocked domain."""
        # Block a domain permanently
        domain = "example.com"
        tab_blocker.block_domain(domain)
        
        # Verify the domain is blocked
        assert tab_blocker.is_domain_blocked(domain)

    def test_is_domain_blocked_temporary_active(self, tab_blocker):
        """Test is_domain_blocked with a temporarily blocked domain that is still active."""
        # Block a domain temporarily
        domain = "example.com"
        tab_blocker.block_domain(domain, 3600)  # 1 hour
        
        # Verify the domain is blocked
        assert tab_blocker.is_domain_blocked(domain)

    def test_is_domain_blocked_temporary_expired(self, tab_blocker):
        """Test is_domain_blocked with a temporarily blocked domain that has expired."""
        # Block a domain temporarily with a very short duration
        domain = "example.com"
        tab_blocker.block_domain(domain, 0.1)  # 100 ms
        
        # Verify the domain is blocked initially
        assert tab_blocker.is_domain_blocked(domain)
        
        # Wait for the block to expire
        time.sleep(0.2)
        
        # Verify the domain is no longer blocked
        assert not tab_blocker.is_domain_blocked(domain)
        
        # Verify the domain is not in the blocked domains (should be cleaned up)
        assert domain.lower() not in tab_blocker._blocked_domains

    def test_is_domain_blocked_not_blocked(self, tab_blocker):
        """Test is_domain_blocked with a domain that is not blocked."""
        # Verify a non-blocked domain is not blocked
        assert not tab_blocker.is_domain_blocked("example.com")

    def test_close_tab(self, tab_blocker, mock_tab):
        """Test closing a tab."""
        # Close the tab
        result = tab_blocker.close_tab(mock_tab, "Testing tab closure")
        
        # Verify the result
        assert result is True

    def test_close_tab_none(self, tab_blocker):
        """Test closing a None tab."""
        # Close a None tab should raise AttributeError
        with pytest.raises(AttributeError):
            tab_blocker.close_tab(None)

    def test_cleanup_expired_blocks(self, tab_blocker):
        """Test cleaning up expired temporary blocks."""
        # Add some temporary blocks with different expiration times
        current_time = time.time()
        
        # Expired block
        tab_blocker._blocked_domains["expired.com"] = current_time - 10
        
        # Non-expired block
        tab_blocker._blocked_domains["active.com"] = current_time + 3600
        
        # Permanent block
        tab_blocker._blocked_domains["permanent.com"] = None
        
        # Call get_blocked_domains which cleans up expired blocks
        tab_blocker.get_blocked_domains()
        
        # Verify expired blocks were removed
        assert "expired.com" not in tab_blocker._blocked_domains
        
        # Verify non-expired blocks were kept
        assert "active.com" in tab_blocker._blocked_domains
        assert "permanent.com" in tab_blocker._blocked_domains

    def test_block_multiple_domains(self, tab_blocker):
        """Test blocking multiple domains with different durations."""
        # Block multiple domains
        tab_blocker.block_domain("permanent.com")  # Permanent
        tab_blocker.block_domain("short.com", 1)   # Short duration
        tab_blocker.block_domain("long.com", 3600) # Long duration
        
        # Verify all domains are blocked
        assert tab_blocker.is_domain_blocked("permanent.com")
        assert tab_blocker.is_domain_blocked("short.com")
        assert tab_blocker.is_domain_blocked("long.com")
        
        # Wait for the short duration block to expire
        time.sleep(1.1)
        
        # Verify short duration block is expired
        assert not tab_blocker.is_domain_blocked("short.com")
        
        # Verify other blocks are still active
        assert tab_blocker.is_domain_blocked("permanent.com")
        assert tab_blocker.is_domain_blocked("long.com")

    def test_block_domain_case_insensitive(self, tab_blocker):
        """Test domain blocking is case insensitive."""
        # Block a domain with mixed case
        tab_blocker.block_domain("ExAmPlE.CoM")
        
        # Verify the domain is blocked regardless of case
        assert tab_blocker.is_domain_blocked("example.com")
        assert tab_blocker.is_domain_blocked("EXAMPLE.COM")
        assert tab_blocker.is_domain_blocked("Example.Com")

    def test_block_domain_with_subdomain(self, tab_blocker):
        """Test blocking a domain with a subdomain."""
        # Block a domain with a subdomain
        tab_blocker.block_domain("sub.example.com")
        
        # Verify the specific subdomain is blocked
        assert tab_blocker.is_domain_blocked("sub.example.com")
        
        # Verify the parent domain is not blocked
        assert not tab_blocker.is_domain_blocked("example.com")
        
        # Verify other subdomains are not blocked
        assert not tab_blocker.is_domain_blocked("other.example.com")


if __name__ == "__main__":
    pytest.main(["-v", "test_tab_blocker.py"])
