"""Tests for the tab blocker adapter."""

import time
import pytest
from unittest.mock import MagicMock, patch
from focus_guard.core.browser.adapters.tab_blocker import DefaultTabBlocker
from focus_guard.core.browser.models.tab import Tab

@pytest.fixture
def tab_blocker():
    """Fixture that provides a DefaultTabBlocker instance."""
    return DefaultTabBlocker()

@pytest.fixture
def test_tab():
    """Fixture that provides a test tab."""
    return Tab(
        id=1,
        window_id=1,
        url="https://example.com",
        title="Example",
        browser_id="test-browser",
        domain="example.com"
    )

def test_close_tab_success(tab_blocker, test_tab):
    """Test successfully closing a tab."""
    # In the default implementation, this just logs and returns True
    result = tab_blocker.close_tab(test_tab, "Test reason")
    assert result is True

def test_block_domain_permanent(tab_blocker):
    """Test blocking a domain permanently."""
    domain = "example.com"
    
    # Block the domain permanently
    result = tab_blocker.block_domain(domain)
    assert result is True
    
    # Check that the domain is blocked
    assert tab_blocker.is_domain_blocked(domain) is True
    
    # Check that the domain appears in the blocked domains list
    blocked = tab_blocker.get_blocked_domains()
    assert domain in blocked
    assert blocked[domain] is None  # No expiry for permanent blocks

def test_block_domain_temporary(tab_blocker):
    """Test blocking a domain temporarily."""
    domain = "example.org"
    duration = 60  # 60 seconds
    
    # Block the domain temporarily
    result = tab_blocker.block_domain(domain, duration_seconds=duration)
    assert result is True
    
    # Check that the domain is blocked
    assert tab_blocker.is_domain_blocked(domain) is True
    
    # Check that the domain appears in the blocked domains list with an expiry
    blocked = tab_blocker.get_blocked_domains()
    assert domain in blocked
    assert blocked[domain] is not None
    
    # Check that the expiry is roughly correct (within 1 second)
    expected_expiry = time.time() + duration
    assert abs(blocked[domain] - expected_expiry) < 1

def test_blocked_domain_expiry(tab_blocker):
    """Test that temporary blocks expire."""
    domain = "test.com"
    
    # Block the domain for a very short time
    tab_blocker.block_domain(domain, duration_seconds=0.1)
    
    # Should be blocked initially
    assert tab_blocker.is_domain_blocked(domain) is True
    
    # Wait for the block to expire
    time.sleep(0.2)
    
    # Should no longer be blocked
    assert tab_blocker.is_domain_blocked(domain) is False
    
    # Should be removed from the blocked domains list
    assert domain not in tab_blocker.get_blocked_domains()

def test_get_blocked_domains_cleanup(tab_blocker):
    """Test that expired domains are cleaned up when getting blocked domains."""
    # Add some test domains with different expiry times
    tab_blocker._blocked_domains = {
        "permanent.com": None,  # Never expires
        "expired.com": 1,  # Already expired
        "future.com": time.time() + 3600  # Expires in 1 hour
    }
    
    # Get the blocked domains (should clean up expired.com)
    blocked = tab_blocker.get_blocked_domains()
    
    # Check the results
    assert set(blocked.keys()) == {"permanent.com", "future.com"}
    assert blocked["permanent.com"] is None
    assert blocked["future.com"] > time.time()

def test_block_domain_invalid_duration(tab_blocker):
    """Test blocking a domain with an invalid duration."""
    # Negative duration should set expiry to current time - 1 second
    tab_blocker.block_domain("test1.com", duration_seconds=-1)
    expiry1 = tab_blocker._blocked_domains.get("test1.com")
    assert expiry1 is not None
    assert expiry1 < time.time()  # Should be in the past
    
    # Zero duration should set expiry to current time
    tab_blocker.block_domain("test2.com", duration_seconds=0)
    expiry2 = tab_blocker._blocked_domains.get("test2.com")
    assert expiry2 is not None
    assert abs(expiry2 - time.time()) < 1  # Should be very close to current time
    
    # Verify the domains are considered blocked (even though they might be expired)
    # This depends on the implementation of is_domain_blocked
    assert tab_blocker.is_domain_blocked("test1.com") == (expiry1 >= time.time())
    assert tab_blocker.is_domain_blocked("test2.com") == (expiry2 >= time.time())
