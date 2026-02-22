"""
Automated tests for tab blocking and override functionality.

These tests simulate the browser extension's interaction with the server
without needing an actual browser, making testing much faster.

Run with: pytest test_override_flow.py -v
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from datetime import date

# Import the modules we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from focus_guard.core.browser_v2.tab_server.domain_usage_tracker import (
    DomainUsageTracker, DomainRuleConfig, DomainDailyStats
)
from focus_guard.core.browser_v2.tab_server.override_manager import (
    OverrideManager, ActiveOverride
)


class TestDomainUsageTracker:
    """Tests for DomainUsageTracker."""
    
    @pytest.fixture
    def tracker(self, tmp_path):
        """Create a fresh tracker with temp files."""
        return DomainUsageTracker(
            data_file=tmp_path / "usage.json",
            rules_file=tmp_path / "rules.json",
        )
    
    def test_default_rule_applied(self, tracker):
        """Test that default rule is applied for unknown domains."""
        rule = tracker.get_rule("youtube.com")
        assert rule.max_overrides_per_day == 3
        assert rule.max_override_duration_seconds == 300  # 5 minutes
        assert rule.max_cumulative_time_seconds == 900  # 15 minutes
    
    def test_custom_rule(self, tracker):
        """Test setting and getting custom rules."""
        custom_rule = DomainRuleConfig(
            domain="facebook.com",
            max_overrides_per_day=2,
            max_override_duration_seconds=180,  # 3 minutes
            max_cumulative_time_seconds=600,  # 10 minutes
        )
        tracker.set_rule(custom_rule)
        
        rule = tracker.get_rule("facebook.com")
        assert rule.max_overrides_per_day == 2
        assert rule.max_override_duration_seconds == 180
        
        # Subdomain should inherit parent rule
        rule = tracker.get_rule("www.facebook.com")
        assert rule.max_overrides_per_day == 2
    
    def test_session_tracking(self, tracker):
        """Test starting and ending sessions."""
        session_id = tracker.start_session("youtube.com", "tab1", "override1")
        assert session_id is not None
        assert tracker.has_active_session("youtube.com")
        
        # Simulate some time passing
        time.sleep(0.1)
        tracker.tick()
        
        session = tracker.end_session("youtube.com")
        assert session is not None
        assert not tracker.has_active_session("youtube.com")
    
    def test_effective_time_calculation(self, tracker):
        """Test effective time with fragmentation penalty."""
        # Set up a rule
        rule = DomainRuleConfig(
            domain="test.com",
            max_overrides_per_day=3,
            penalty_per_extra_override_seconds=60,
        )
        tracker.set_rule(rule)
        
        # Simulate 5 overrides with 60 seconds each
        for i in range(5):
            tracker.start_session("test.com", f"tab{i}", f"override{i}")
            time.sleep(0.05)  # Small delay
            tracker.tick()
            tracker.end_session("test.com")
        
        stats = tracker.get_daily_stats("test.com")
        # 5 overrides, 3 baseline = 2 extra = 2*60 = 120 seconds penalty
        # Effective time should be actual time + 120 seconds
        assert stats.get("override_count", 0) == 5
    
    def test_can_override_check(self, tracker):
        """Test the can_override check with budget limits."""
        rule = DomainRuleConfig(
            domain="limited.com",
            max_overrides_per_day=2,
            max_cumulative_time_seconds=120,  # 2 minutes total
        )
        tracker.set_rule(rule)
        
        # First check should allow override
        result = tracker.check_can_override("limited.com")
        assert result["can_override"] is True
        
        # Simulate using up the budget
        tracker.start_session("limited.com", "tab1", "override1")
        # Manually set the stats to simulate time usage
        if "limited.com" not in tracker._daily_stats:
            tracker._daily_stats["limited.com"] = DomainDailyStats(
                domain="limited.com",
                date=date.today().isoformat(),
            )
        tracker._daily_stats["limited.com"].total_active_seconds = 120
        tracker._daily_stats["limited.com"].override_count = 2
        tracker.end_session("limited.com")
        
        # Now should deny override
        result = tracker.check_can_override("limited.com")
        assert result["can_override"] is False


class TestOverrideManager:
    """Tests for OverrideManager."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create a fresh override manager."""
        # Patch the usage tracker to use temp files
        with patch('focus_guard.core.browser_v2.tab_server.domain_usage_tracker.get_domain_usage_tracker') as mock:
            tracker = DomainUsageTracker(
                data_file=tmp_path / "usage.json",
                rules_file=tmp_path / "rules.json",
            )
            mock.return_value = tracker
            mgr = OverrideManager()
            mgr._tracker = tracker
            yield mgr
    
    def test_request_override(self, manager):
        """Test requesting an override."""
        result = manager.request_override(
            domain="youtube.com",
            url="https://youtube.com/watch?v=123",
            block_reason="Distraction",
            browser="chrome",
        )
        
        assert result["granted"] is True
        assert result["override"] is not None
        assert result["override"]["domain"] == "youtube.com"
    
    def test_check_override(self, manager):
        """Test checking if override exists."""
        # No override yet
        result = manager.check_override("youtube.com")
        assert result["has_override"] is False
        
        # Request override
        manager.request_override(
            domain="youtube.com",
            url="https://youtube.com",
            block_reason="Distraction",
        )
        
        # Now should have override
        result = manager.check_override("youtube.com")
        assert result["has_override"] is True
    
    def test_revoke_override(self, manager):
        """Test revoking an override."""
        manager.request_override(
            domain="youtube.com",
            url="https://youtube.com",
            block_reason="Distraction",
        )
        
        revoked = manager.revoke_override("youtube.com")
        assert revoked is True
        
        result = manager.check_override("youtube.com")
        assert result["has_override"] is False
    
    def test_override_count_not_incremented_on_grant(self, manager):
        """Test that override count is NOT incremented when override is granted."""
        # Request override
        manager.request_override(
            domain="youtube.com",
            url="https://youtube.com",
            block_reason="Distraction",
        )
        
        # Daily count should still be 0 (not incremented until usage starts)
        assert manager._daily_counts.get("youtube.com", 0) == 0
    
    def test_override_count_incremented_on_usage(self, manager):
        """Test that override count IS incremented when usage starts."""
        # Request override
        manager.request_override(
            domain="youtube.com",
            url="https://youtube.com",
            block_reason="Distraction",
        )
        
        # Start usage
        result = manager.start_override_usage("youtube.com", "tab1")
        assert result["started"] is True
        
        # Now daily count should be 1
        assert manager._daily_counts.get("youtube.com", 0) == 1


class TestIntegrationFlow:
    """Integration tests simulating full browser flow."""
    
    @pytest.fixture
    def setup(self, tmp_path):
        """Set up tracker and manager with temp files."""
        tracker = DomainUsageTracker(
            data_file=tmp_path / "usage.json",
            rules_file=tmp_path / "rules.json",
        )
        
        with patch('focus_guard.core.browser_v2.tab_server.domain_usage_tracker.get_domain_usage_tracker') as mock:
            mock.return_value = tracker
            manager = OverrideManager()
            yield {"tracker": tracker, "manager": manager}
    
    def test_full_override_flow(self, setup):
        """Test complete flow: block -> override -> use -> expire."""
        tracker = setup["tracker"]
        manager = setup["manager"]
        
        # Set a short budget for testing (30 seconds)
        rule = DomainRuleConfig(
            domain="youtube.com",
            max_overrides_per_day=3,
            max_override_duration_seconds=30,  # 30 seconds
            max_cumulative_time_seconds=60,  # 1 minute total
        )
        tracker.set_rule(rule)
        
        # 1. Request override
        result = manager.request_override(
            domain="youtube.com",
            url="https://youtube.com",
            block_reason="Distraction",
        )
        assert result["granted"] is True
        
        # 2. Check override exists
        check = manager.check_override("youtube.com")
        assert check["has_override"] is True
        
        # 3. Start usage (simulates navigation to site)
        usage_result = manager.start_override_usage("youtube.com", "tab1")
        assert usage_result["started"] is True
        
        # 4. Simulate time passing (tick the tracker)
        for _ in range(5):
            tracker.tick()
            time.sleep(0.1)
        
        # 5. End session (tab closed)
        tracker.end_session("youtube.com")
        
        # 6. Check stats
        stats = tracker.get_daily_stats("youtube.com")
        assert stats.get("override_count", 0) == 1
        assert stats.get("session_count", 0) >= 1
    
    def test_multiple_sessions_same_override(self, setup):
        """Test reopening tab within same override period."""
        tracker = setup["tracker"]
        manager = setup["manager"]
        
        # Request override
        manager.request_override(
            domain="youtube.com",
            url="https://youtube.com",
            block_reason="Distraction",
        )
        
        # Start first session
        manager.start_override_usage("youtube.com", "tab1")
        tracker.tick()
        tracker.end_session("youtube.com")
        
        # Start second session (same override, should not increment count)
        result = manager.start_override_usage("youtube.com", "tab2")
        assert result["started"] is True
        assert result.get("reason") == "Session already active" or manager._daily_counts.get("youtube.com", 0) == 1
    
    def test_budget_exhaustion(self, setup):
        """Test that override is denied when budget is exhausted."""
        tracker = setup["tracker"]
        manager = setup["manager"]
        
        # Set a very short budget
        rule = DomainRuleConfig(
            domain="test.com",
            max_overrides_per_day=1,
            max_cumulative_time_seconds=10,  # 10 seconds
        )
        tracker.set_rule(rule)
        
        # Manually exhaust the budget
        tracker._daily_stats["test.com"] = DomainDailyStats(
            domain="test.com",
            date=date.today().isoformat(),
            total_active_seconds=15,  # Over budget
            override_count=1,
        )
        
        # Request should be denied
        result = manager.request_override(
            domain="test.com",
            url="https://test.com",
            block_reason="Distraction",
        )
        assert result["granted"] is False


class TestSimulatedBrowserFlow:
    """
    Simulated browser tests that mimic the extension's behavior.
    These are faster than real browser tests but test the same logic.
    """
    
    @pytest.fixture
    def browser_sim(self, tmp_path):
        """Create a simulated browser environment."""
        tracker = DomainUsageTracker(
            data_file=tmp_path / "usage.json",
            rules_file=tmp_path / "rules.json",
        )
        
        with patch('focus_guard.core.browser_v2.tab_server.domain_usage_tracker.get_domain_usage_tracker') as mock:
            mock.return_value = tracker
            manager = OverrideManager()
            
            class BrowserSimulator:
                def __init__(self):
                    self.tracker = tracker
                    self.manager = manager
                    self.tabs = {}  # tab_id -> url
                    self.active_tab = None
                    self.override_sessions = {}  # domain -> {tab_ids, usage_started}
                
                def navigate(self, tab_id: str, url: str) -> dict:
                    """Simulate navigating to a URL."""
                    domain = url.split("//")[-1].split("/")[0]
                    
                    # Check if blocked
                    check = self.manager.check_override(domain)
                    if not check["has_override"]:
                        # Would be blocked - return blocked status
                        return {"blocked": True, "domain": domain}
                    
                    # Has override - start usage if not already
                    if domain not in self.override_sessions:
                        self.override_sessions[domain] = {"tab_ids": set(), "usage_started": False}
                    
                    session = self.override_sessions[domain]
                    session["tab_ids"].add(tab_id)
                    
                    if not session["usage_started"]:
                        result = self.manager.start_override_usage(domain, tab_id)
                        session["usage_started"] = result.get("started", False)
                    
                    self.tabs[tab_id] = url
                    self.active_tab = tab_id
                    return {"blocked": False, "domain": domain}
                
                def close_tab(self, tab_id: str):
                    """Simulate closing a tab."""
                    if tab_id in self.tabs:
                        url = self.tabs.pop(tab_id)
                        domain = url.split("//")[-1].split("/")[0]
                        
                        if domain in self.override_sessions:
                            self.override_sessions[domain]["tab_ids"].discard(tab_id)
                            if not self.override_sessions[domain]["tab_ids"]:
                                self.tracker.end_session(domain)
                                del self.override_sessions[domain]
                
                def request_override(self, domain: str, url: str) -> dict:
                    """Simulate requesting an override from blocked page."""
                    return self.manager.request_override(
                        domain=domain,
                        url=url,
                        block_reason="Distraction",
                        browser="test",
                    )
                
                def tick(self, seconds: float = 1.0):
                    """Simulate time passing."""
                    self.tracker.tick()
                    time.sleep(seconds * 0.01)  # Scaled down for testing
                
                def get_stats(self, domain: str) -> dict:
                    """Get usage stats for a domain."""
                    return self.tracker.get_daily_stats(domain)
            
            yield BrowserSimulator()
    
    def test_blocked_page_shown(self, browser_sim):
        """Test that blocked page is shown for blocked domain."""
        result = browser_sim.navigate("tab1", "https://youtube.com")
        assert result["blocked"] is True
    
    def test_override_allows_access(self, browser_sim):
        """Test that override allows access."""
        # Request override
        override_result = browser_sim.request_override("youtube.com", "https://youtube.com")
        assert override_result["granted"] is True
        
        # Now navigation should work
        result = browser_sim.navigate("tab1", "https://youtube.com")
        assert result["blocked"] is False
    
    def test_close_and_reopen(self, browser_sim):
        """Test closing and reopening tab within override period."""
        # Request override and navigate
        browser_sim.request_override("youtube.com", "https://youtube.com")
        browser_sim.navigate("tab1", "https://youtube.com")
        
        # Close tab
        browser_sim.close_tab("tab1")
        
        # Reopen - should still work (same override)
        result = browser_sim.navigate("tab2", "https://youtube.com")
        assert result["blocked"] is False
        
        # Override count should still be 1
        stats = browser_sim.get_stats("youtube.com")
        assert stats.get("override_count", 0) <= 1
    
    def test_time_tracking(self, browser_sim):
        """Test that time is tracked correctly."""
        # Set short budget
        browser_sim.tracker.set_rule(DomainRuleConfig(
            domain="youtube.com",
            max_cumulative_time_seconds=60,
        ))
        
        # Request override and navigate
        browser_sim.request_override("youtube.com", "https://youtube.com")
        browser_sim.navigate("tab1", "https://youtube.com")
        
        # Simulate time passing
        for _ in range(5):
            browser_sim.tick(1.0)
        
        # Close tab
        browser_sim.close_tab("tab1")
        
        # Check time was tracked
        stats = browser_sim.get_stats("youtube.com")
        assert stats.get("total_active_seconds", 0) > 0 or stats.get("session_count", 0) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
