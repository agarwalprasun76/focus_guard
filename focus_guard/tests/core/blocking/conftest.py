"""
Pytest configuration and fixtures for blocking module tests.
"""
import pytest
from unittest.mock import MagicMock, patch
from focus_guard.core.blocking.engine import PolicyEngine
from focus_guard.core.blocking.manager import BlockingManager
from focus_guard.core.blocking.event_handler import BlockingEventHandler
from focus_guard.core.domain.models import Domain


@pytest.fixture
def mock_domain():
    """Return a mock Domain object for testing."""
    return Domain("example.com")


@pytest.fixture
def policy_engine():
    """Return a PolicyEngine instance for testing."""
    return PolicyEngine()


@pytest.fixture
def blocking_event_handler(policy_engine):
    """Return a BlockingEventHandler instance for testing."""
    return BlockingEventHandler(policy_engine)


@pytest.fixture
def blocking_manager():
    """Return a BlockingManager instance for testing."""
    with patch('focus_guard.core.blocking.manager.PolicyEngine') as mock_engine:
        with patch('focus_guard.core.blocking.manager.BlockingEventHandler') as mock_handler:
            manager = BlockingManager()
            manager.policy_engine = mock_engine
            manager.event_handler = mock_handler
            return manager


@pytest.fixture
def blocking_decision():
    """Return a BlockingDecision instance for testing."""
    from focus_guard.core.blocking.engine import BlockingDecision
    from focus_guard.core.blocking.policies.base import BlockingPolicyType
    
    return BlockingDecision(
        should_block=True,
        policy_name="test_policy",
        reason="Test reason",
        policy_type=BlockingPolicyType.DOMAIN,
        metadata={"test_key": "test_value"}
    )
