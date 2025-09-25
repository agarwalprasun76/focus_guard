"""
Tests for the blocking engine module.

This module contains unit tests for the PolicyEngine class, which is responsible for
evaluating blocking policies against resources.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from focus_guard.core.blocking.engine import PolicyEngine, BlockingDecision
from focus_guard.core.blocking.policies.base import BlockingPolicyType
from focus_guard.core.domain.models import Domain


class TestBlockingDecision:
    """Tests for the BlockingDecision class."""

    def test_blocking_decision_creation(self):
        """Test creating a BlockingDecision with all fields."""
        decision = BlockingDecision(
            should_block=True,
            policy_name="test_policy",
            reason="Test reason",
            policy_type=BlockingPolicyType.DOMAIN,
            timestamp=1234567890.0,
            metadata={"key": "value"}
        )
        
        assert decision.should_block is True
        assert decision.policy_name == "test_policy"
        assert decision.reason == "Test reason"
        assert decision.policy_type == BlockingPolicyType.DOMAIN
        assert decision.timestamp == 1234567890.0
        assert decision.metadata == {"key": "value"}

    def test_blocking_decision_defaults(self):
        """Test BlockingDecision with default values."""
        decision = BlockingDecision(
            should_block=False,
            policy_name="default_policy",
            reason="Default reason",
            policy_type=BlockingPolicyType.TIME_BASED
        )
        
        assert decision.should_block is False
        assert decision.timestamp is not None
        assert isinstance(decision.timestamp, float)
        assert decision.metadata == {}


class TestPolicyEngine:
    """Tests for the PolicyEngine class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.engine = PolicyEngine()
        self.domain = Domain("example.com")
        self.now = datetime.now()
        
        # Configure mock policy with required attributes
        self.mock_policy = MagicMock()
        self.mock_policy.name = "mock_policy"
        self.mock_policy.is_enabled = True
        self.mock_policy.priority = 0
        self.mock_policy.policy_type = BlockingPolicyType.CUSTOM
        self.mock_policy.evaluate.return_value = BlockingDecision(
            should_block=False,
            policy_name="mock_policy",
            reason="Not blocked",
            policy_type=BlockingPolicyType.CUSTOM
        )
        
        # Patch the policy registry
        self.patcher = patch.object(self.engine, '_policies', {})
        self.mock_policies = self.patcher.start()
        
        yield
        
        # Cleanup
        self.patcher.stop()
    
    def test_add_policy(self):
        """Test adding a policy to the engine."""
        self.engine.add_policy(self.mock_policy)
        assert len(self.engine._policies) == 1
        assert self.mock_policy in self.engine._policies.values()
    
    def test_remove_policy(self):
        """Test removing a policy from the engine."""
        self.engine.add_policy(self.mock_policy)
        self.engine.remove_policy("mock_policy")
        assert len(self.engine._policies) == 0
    
    def test_evaluate_resource_no_policies(self):
        """Test evaluating a resource with no policies."""
        result = self.engine.evaluate_resource(self.domain)
        assert result.should_block is False
        assert result.reason == "No blocking policies configured"
    
    def test_evaluate_resource_blocking_policy(self):
        """Test evaluating a resource with a blocking policy."""
        # Configure mock to block
        self.mock_policy.evaluate.return_value = BlockingDecision(
            should_block=True,
            policy_name="blocking_policy",
            reason="Blocked by policy",
            policy_type=BlockingPolicyType.DOMAIN
        )
        self.engine.add_policy(self.mock_policy)
        
        result = self.engine.evaluate_resource(self.domain)
        assert result.should_block is True
        assert result.policy_name == "blocking_policy"
    
    def test_evaluate_resource_multiple_policies(self):
        """Test evaluating a resource with multiple policies."""
        # First policy allows
        policy1 = MagicMock()
        policy1.priority = 1  # Add priority for sorting
        policy1.name = "allow_policy"  # Add name
        policy1.evaluate.return_value = BlockingDecision(
            should_block=False,
            policy_name="allow_policy",
            reason="Allowed",
            policy_type=BlockingPolicyType.DOMAIN
        )
        
        # Second policy blocks
        policy2 = MagicMock()
        policy2.priority = 2  # Add priority for sorting
        policy2.name = "block_policy"  # Add name
        policy2.evaluate.return_value = BlockingDecision(
            should_block=True,
            policy_name="block_policy",
            reason="Blocked",
            policy_type=BlockingPolicyType.TIME_BASED
        )
        
        self.engine.add_policy(policy1)
        self.engine.add_policy(policy2)
        
        result = self.engine.evaluate_resource(self.domain)
        assert result.should_block is True
        assert result.policy_name == "block_policy"
    
    def test_clear_policies(self):
        """Test clearing all policies from the engine."""
        self.engine.add_policy(self.mock_policy)
        self.engine.clear_policies()
        assert len(self.engine._policies) == 0
    
    def test_get_policy(self):
        """Test retrieving a policy by name."""
        self.engine.add_policy(self.mock_policy)
        policy = self.engine.get_policy("mock_policy")
        assert policy == self.mock_policy
    
    def test_get_policy_nonexistent(self):
        """Test retrieving a non-existent policy returns None."""
        policy = self.engine.get_policy("nonexistent")
        assert policy is None


class TestPolicyEngineEdgeCases:
    """Edge case tests for PolicyEngine."""
    
    def test_evaluate_resource_with_context(self):
        """Test evaluating a resource with additional context."""
        engine = PolicyEngine()
        mock_policy = MagicMock()
        mock_policy.name = "context_policy"  # Add name attribute
        mock_policy.policy_type = BlockingPolicyType.DOMAIN  # Add policy type
        mock_policy.priority = 1  # Add priority for sorting
        mock_policy.evaluate.return_value = BlockingDecision(
            should_block=False,
            policy_name="context_policy",
            reason="Context evaluated",
            policy_type=BlockingPolicyType.DOMAIN
        )
        
        engine.add_policy(mock_policy)
        context = {"user": "test_user", "time_of_day": "morning"}
        
        result = engine.evaluate_resource("example.com", context=context)
        
        # Verify the policy's evaluate method was called with the context
        mock_policy.evaluate.assert_called_once_with("example.com", context=context)
        assert result.policy_name == "context_policy"
    
    def test_duplicate_policy_name(self):
        """Test that adding a policy with a duplicate name replaces the existing one."""
        engine = PolicyEngine()
        policy1 = MagicMock()
        policy1.name = "duplicate_policy"
        policy2 = MagicMock()
        policy2.name = "duplicate_policy"
        
        engine.add_policy(policy1)
        engine.add_policy(policy2)
        
        assert len(engine._policies) == 1
        assert engine._policies["duplicate_policy"] == policy2


class TestPolicyEngineIntegration:
    """Integration tests for PolicyEngine with actual policy implementations."""
    
    def test_with_domain_policy(self):
        """Test the engine with a real DomainBlockingPolicy."""
        from focus_guard.core.blocking.policies.domain import DomainBlockingPolicy, DomainBlockingConfig
        
        # Create a domain blocking policy
        config = DomainBlockingConfig(
            name="test_domain_policy",
            policy_type=BlockingPolicyType.DOMAIN,
            blocked_domains={"blocked.com", "restricted.org"},
            blocked_categories=set(),
            allowlist={"allowed.blocked.com"}
        )
        policy = DomainBlockingPolicy(config)
        
        # Set up the engine
        engine = PolicyEngine()
        engine.add_policy(policy)
        
        # Test blocked domain
        result = engine.evaluate_resource("blocked.com")
        assert result.should_block is True
        assert "domain 'blocked.com' is in the blocked domains list" in result.reason.lower()
        
        # Test allowed subdomain
        result = engine.evaluate_resource("allowed.blocked.com")
        assert result.should_block is False
        
        # Test unlisted domain
        result = engine.evaluate_resource("example.com")
        assert result.should_block is False
