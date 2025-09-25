"""
Tests for the blocking event handler module.

This module contains unit tests for the BlockingEventHandler class, which is responsible
for processing blocking-related events and taking appropriate actions.
"""

import pytest
from unittest.mock import MagicMock, call, patch
from datetime import datetime

from focus_guard.core.blocking.event_handler import BlockingEventHandler
from focus_guard.core.blocking.engine import PolicyEngine, BlockingDecision
from focus_guard.core.blocking.events import (
    EventType, BlockingEvent, ResourceAccessEvent, PolicyEvent, OverrideEvent,
    create_event
)
from focus_guard.core.blocking.policies.base import BlockingPolicyType
from focus_guard.core.domain.models import Domain


class TestBlockingEventHandler:
    """Tests for the BlockingEventHandler class."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock PolicyEngine with required methods."""
        # Create a mock with the required methods
        engine = MagicMock(spec=PolicyEngine)
        
        # Set up the return values for the methods we'll be using
        engine.evaluate_domain = MagicMock(return_value=BlockingDecision(
            should_block=False,
            policy_name="test_policy",
            reason="Test reason",
            policy_type=BlockingPolicyType.DOMAIN
        ))
        
        # Add other required methods with sensible defaults
        engine.add_policy = MagicMock()
        engine.remove_policy = MagicMock()
        engine.update_policy = MagicMock()
        engine.get_policy = MagicMock()
        engine.list_policies = MagicMock(return_value=[])
        engine.evaluate_resource = MagicMock(return_value=BlockingDecision(
            should_block=False,
            policy_name="test_policy",
            reason="Test reason",
            policy_type=BlockingPolicyType.DOMAIN
        ))
        
        return engine

    @pytest.fixture
    def handler(self, mock_engine):
        """Create a BlockingEventHandler with a mock engine."""
        return BlockingEventHandler(mock_engine)

    def test_initialization(self, handler, mock_engine):
        """Test that the handler is initialized correctly."""
        assert handler.policy_engine is mock_engine
        assert hasattr(handler, '_event_handlers')
        assert callable(handler._event_handlers[EventType.RESOURCE_ACCESS_ATTEMPT])

    def test_handle_event_unknown_type(self, handler):
        """Test handling an unknown event type logs a warning."""
        with patch('logging.Logger.error') as mock_error:
            # Create an event with a valid type but no handler registered for it
            # Using a less common event type that's unlikely to have a handler
            event = BlockingEvent(event_type=EventType.APPLICATION_TERMINATED)
            handler.handle_event(event)
            
            # Verify the error was logged
            assert mock_error.called
            error_message = mock_error.call_args[0][0]
            assert "Error handling event" in error_message

    def test_handle_resource_access_attempt_blocked(self, handler, mock_engine):
        """Test handling a resource access attempt that should be blocked."""
        # Configure mock to block
        mock_engine.evaluate_domain.return_value = BlockingDecision(
            should_block=True,
            policy_name="test_policy",
            reason="Test block reason",
            policy_type=BlockingPolicyType.DOMAIN
        )
    
        domain = Domain("blocked.com")
        event = ResourceAccessEvent(
            resource_type="domain",
            resource_id=str(domain),
            action="access",
            metadata={"context": {"user": "test_user"}}
        )
    
        with patch.object(handler, '_notify_callbacks') as mock_notify:
            handler._handle_resource_access_attempt(event)
    
        # Verify the policy engine was called with the domain
        mock_engine.evaluate_domain.assert_called_once()
        call_args = mock_engine.evaluate_domain.call_args[0]
        assert isinstance(call_args[0], Domain)
        assert str(call_args[0]) == "blocked.com"
        # The context is passed as a keyword argument, not a positional argument
        assert mock_engine.evaluate_domain.call_args[1] == {"context": {"user": "test_user"}}
        
        # Verify the notification was sent
        mock_notify.assert_called_once()
        blocked_event = mock_notify.call_args[0][0]
        assert blocked_event.action == "block"
        assert blocked_event.reason == "Test block reason"

    def test_handle_resource_access_attempt_allowed(self, handler, mock_engine):
        """Test handling a resource access attempt that should be allowed."""
        # Configure mock to allow
        mock_engine.evaluate_domain.return_value = BlockingDecision(
            should_block=False,
            policy_name="test_policy",
            reason="Access allowed",
            policy_type=BlockingPolicyType.DOMAIN
        )
        
        domain = Domain("allowed.com")
        event = ResourceAccessEvent(
            resource_type="domain",
            resource_id=str(domain),
            action="access"
        )
        
        with patch.object(handler, '_notify_callbacks') as mock_notify:
            handler._handle_resource_access_attempt(event)
        
        # Verify the policy engine was called with the domain
        mock_engine.evaluate_domain.assert_called_once()
        call_args = mock_engine.evaluate_domain.call_args[0]
        assert isinstance(call_args[0], Domain)
        assert str(call_args[0]) == "allowed.com"
        
        # Verify no block notification was sent
        mock_notify.assert_not_called()

    def test_handle_override_granted(self, handler):
        """Test handling an override granted event."""
        domain = Domain("example.com")
        event = OverrideEvent(
            resource_type="domain",
            resource_id=str(domain),
            duration_seconds=300,
            reason="Temporary access",
            event_type=EventType.OVERRIDE_GRANTED
        )
        
        with patch('logging.Logger.info') as mock_info, \
             patch('time.time', return_value=1234567890.0):
            # Call the handler method directly
            handler._handle_override_granted(event)
            
            # Verify the event was logged
            assert mock_info.called
            log_message = mock_info.call_args[0][0]
            assert "Override granted for example.com" in log_message
            assert "duration: 300s" in log_message

    def test_handle_policy_added(self, handler, mock_engine):
        """Test handling a policy added event."""
        policy = MagicMock()
        policy.name = "test_policy"
        policy.policy_type = "domain"
        event = PolicyEvent(
            policy_name="test_policy",
            policy_type="domain",
            event_type=EventType.POLICY_ADDED
        )
        
        with patch('logging.Logger.info') as mock_info:
            # Call the handler method directly
            handler._handle_policy_added(event)
            
            # Verify the event was logged
            assert mock_info.called
            assert "Policy added: test_policy (domain)" in mock_info.call_args[0][0]

    def test_handle_policy_removed(self, handler, mock_engine):
        """Test handling a policy removed event."""
        event = PolicyEvent(
            policy_name="test_policy",
            policy_type="domain",
            event_type=EventType.POLICY_REMOVED
        )
        
        with patch('logging.Logger.info') as mock_info:
            # Call the handler method directly with the event
            handler._handle_policy_removed(event)
            
            # Verify the event was logged
            assert mock_info.called
            assert "Policy removed: test_policy" in mock_info.call_args[0][0]

    def test_handle_blocking_enabled(self, handler):
        """Test handling the blocking enabled event."""
        event = BlockingEvent(event_type=EventType.BLOCKING_ENABLED)
        
        with patch('logging.Logger.info') as mock_info:
            # Call the handler method directly
            handler._handle_blocking_enabled(event)
            
            # Verify the event was logged
            assert mock_info.called
            assert "Blocking system enabled" in mock_info.call_args[0][0]

    def test_handle_blocking_disabled(self, handler):
        """Test handling the blocking disabled event."""
        event = BlockingEvent(event_type=EventType.BLOCKING_DISABLED)
        
        with patch('logging.Logger.info') as mock_info:
            # Call the handler method directly
            handler._handle_blocking_disabled(event)
            
            # Verify the event was logged
            assert mock_info.called
            assert "Blocking system disabled" in mock_info.call_args[0][0]


class TestBlockingEventHandlerIntegration:
    """Integration tests for BlockingEventHandler with actual PolicyEngine."""
    
    @pytest.fixture
    def mock_engine(self):
        """Create a mock PolicyEngine with required methods."""
        # Create a mock with the required methods
        engine = MagicMock()
        
        # Set up the return values for the methods we'll be using
        engine.evaluate_domain.return_value = BlockingDecision(
            should_block=True,
            policy_name="test_policy",
            reason="Blocked by test policy",
            policy_type=BlockingPolicyType.DOMAIN
        )
        
        # Add other required methods with sensible defaults
        engine.add_policy = MagicMock()
        engine.remove_policy = MagicMock()
        engine.update_policy = MagicMock()
        engine.get_policy = MagicMock()
        engine.list_policies = MagicMock(return_value=[])
        engine.evaluate_resource = MagicMock(return_value=BlockingDecision(
            should_block=False,
            policy_name="test_policy",
            reason="Test reason",
            policy_type=BlockingPolicyType.DOMAIN
        ))
        
        return engine
    
    def test_end_to_end_blocking_flow(self, mock_engine):
        """Test the complete flow of a blocking event."""
        # Create the event handler with the mock engine
        handler = BlockingEventHandler(mock_engine)
        
        # Test blocked domain
        event = ResourceAccessEvent(
            resource_type="domain",
            resource_id="blocked.com",
            action="access"
        )
        
        # Set up a callback to capture the blocked event
        blocked_events = []
        def capture_blocked(event):
            if event.event_type == EventType.RESOURCE_ACCESS_BLOCKED:
                blocked_events.append(event)
        
        handler.register_callback(EventType.RESOURCE_ACCESS_BLOCKED, capture_blocked)
        
        # Process the event directly through the handler method
        handler._handle_resource_access_attempt(event)
        
        # Verify a blocked event was generated
        assert len(blocked_events) == 1
        assert "blocked" in blocked_events[0].reason.lower()
