"""Tests for tab_server blocking module."""

import pytest
from ..tab_server.blocking import BlockingManager, BlockingRule, BlockingDecision


class TestBlockingManager:
    """Tests for BlockingManager class."""

    def test_init_creates_empty_manager(self):
        """Manager should start with no rules."""
        manager = BlockingManager()
        rules = manager.get_rules()
        assert len(rules) == 0

    def test_add_rule(self):
        """Adding a rule should store it."""
        manager = BlockingManager()
        rule = BlockingRule(domain="facebook.com", reason="social media")
        
        manager.add_rule(rule)
        rules = manager.get_rules()
        
        assert len(rules) == 1
        assert rules[0].domain == "facebook.com"

    def test_remove_rule(self):
        """Removing a rule should delete it."""
        manager = BlockingManager()
        rule = BlockingRule(domain="facebook.com", reason="social media")
        
        manager.add_rule(rule)
        result = manager.remove_rule("facebook.com")
        
        assert result is True
        assert len(manager.get_rules()) == 0

    def test_remove_nonexistent_rule(self):
        """Removing a nonexistent rule should return False."""
        manager = BlockingManager()
        result = manager.remove_rule("nonexistent.com")
        assert result is False

    def test_should_block_matching_domain(self):
        """Should block URLs matching a rule."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="facebook.com", reason="social media"))
        
        decision = manager.should_block("https://facebook.com/feed")
        
        assert decision.should_block is True
        assert decision.reason == "social media"

    def test_should_not_block_unmatched_domain(self):
        """Should not block URLs not matching any rule."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="facebook.com", reason="social media"))
        
        decision = manager.should_block("https://google.com/search")
        
        assert decision.should_block is False

    def test_should_block_subdomain(self):
        """Should block subdomains of a blocked domain."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="facebook.com", reason="social media"))
        
        decision = manager.should_block("https://www.facebook.com/feed")
        
        assert decision.should_block is True

    def test_should_block_deep_subdomain(self):
        """Should block deep subdomains."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="facebook.com", reason="social media"))
        
        decision = manager.should_block("https://m.www.facebook.com/feed")
        
        assert decision.should_block is True

    def test_disabled_rule_not_applied(self):
        """Disabled rules should not block."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="facebook.com", reason="social media", enabled=False))
        
        decision = manager.should_block("https://facebook.com/feed")
        
        assert decision.should_block is False

    def test_set_rules_replaces_all(self):
        """set_rules should replace all existing rules."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="old.com", reason="old"))
        
        manager.set_rules([
            BlockingRule(domain="new1.com", reason="new1"),
            BlockingRule(domain="new2.com", reason="new2"),
        ])
        
        rules = manager.get_rules()
        assert len(rules) == 2
        domains = {r.domain for r in rules}
        assert "new1.com" in domains
        assert "new2.com" in domains
        assert "old.com" not in domains

    def test_caching(self):
        """Decisions should be cached."""
        manager = BlockingManager(cache_ttl_seconds=60.0)
        manager.add_rule(BlockingRule(domain="facebook.com", reason="social media"))
        
        # First call
        decision1 = manager.should_block("https://facebook.com/feed")
        assert decision1.cached is False
        
        # Second call should be cached
        decision2 = manager.should_block("https://facebook.com/feed")
        assert decision2.cached is True
        assert decision2.should_block is True

    def test_clear_cache(self):
        """clear_cache should remove cached decisions."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="facebook.com", reason="social media"))
        
        # Populate cache
        manager.should_block("https://facebook.com/feed")
        
        # Clear cache
        manager.clear_cache()
        
        # Next call should not be cached
        decision = manager.should_block("https://facebook.com/feed")
        assert decision.cached is False

    def test_external_checker(self):
        """External checker should be called for blocking decisions."""
        manager = BlockingManager()
        
        def external_checker(url: str, domain: str) -> BlockingDecision:
            if "blocked" in domain:
                return BlockingDecision(should_block=True, reason="external")
            return BlockingDecision(should_block=False)
        
        manager.set_external_checker(external_checker)
        
        decision = manager.should_block("https://blocked-site.com/page")
        assert decision.should_block is True
        assert decision.reason == "external"

    def test_local_rules_take_precedence(self):
        """Local rules should be checked before external checker."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="facebook.com", reason="local rule"))
        
        def external_checker(url: str, domain: str) -> BlockingDecision:
            return BlockingDecision(should_block=False)
        
        manager.set_external_checker(external_checker)
        
        decision = manager.should_block("https://facebook.com/feed")
        assert decision.should_block is True
        assert decision.reason == "local rule"

    def test_empty_url_not_blocked(self):
        """Empty URL should not be blocked."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="facebook.com", reason="social media"))
        
        decision = manager.should_block("")
        assert decision.should_block is False

    def test_invalid_url_not_blocked(self):
        """Invalid URL should not be blocked."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="facebook.com", reason="social media"))
        
        decision = manager.should_block("not-a-valid-url")
        assert decision.should_block is False

    def test_case_insensitive_matching(self):
        """Domain matching should be case-insensitive."""
        manager = BlockingManager()
        manager.add_rule(BlockingRule(domain="Facebook.COM", reason="social media"))
        
        decision = manager.should_block("https://facebook.com/feed")
        assert decision.should_block is True


class TestBlockingRule:
    """Tests for BlockingRule dataclass."""

    def test_default_values(self):
        """Rule should have sensible defaults."""
        rule = BlockingRule(domain="test.com")
        
        assert rule.domain == "test.com"
        assert rule.reason == "blocked"
        assert rule.category is None
        assert rule.enabled is True

    def test_custom_values(self):
        """Rule should accept custom values."""
        rule = BlockingRule(
            domain="facebook.com",
            reason="social media distraction",
            category="social",
            enabled=False,
        )
        
        assert rule.domain == "facebook.com"
        assert rule.reason == "social media distraction"
        assert rule.category == "social"
        assert rule.enabled is False


class TestBlockingDecision:
    """Tests for BlockingDecision dataclass."""

    def test_default_values(self):
        """Decision should have sensible defaults."""
        decision = BlockingDecision(should_block=True)
        
        assert decision.should_block is True
        assert decision.reason is None
        assert decision.rule is None
        assert decision.cached is False

    def test_with_rule(self):
        """Decision should include rule reference."""
        rule = BlockingRule(domain="test.com", reason="test")
        decision = BlockingDecision(should_block=True, reason="test", rule=rule)
        
        assert decision.rule is rule
