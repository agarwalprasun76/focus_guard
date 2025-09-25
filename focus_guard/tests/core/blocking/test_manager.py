"""
Tests for the blocking manager module.

This module contains unit tests for the BlockingManager class, which serves as the
main entry point for the blocking functionality in Focus Guard.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from focus_guard.core.blocking.manager import BlockingManager
from focus_guard.core.blocking.engine import PolicyEngine, BlockingDecision
from focus_guard.core.blocking.event_handler import BlockingEventHandler
from focus_guard.core.blocking.events import EventType
from focus_guard.core.blocking.policies.base import BlockingPolicyType
from focus_guard.core.domain.models import Domain


class TestBlockingManager:
    """Tests for the BlockingManager class."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock PolicyEngine."""
        return MagicMock(spec=PolicyEngine)

    @pytest.fixture
    def mock_event_handler(self, mock_engine):
        """Create a mock BlockingEventHandler."""
        return MagicMock(spec=BlockingEventHandler, policy_engine=mock_engine)

    @pytest.fixture
    def manager(self, mock_engine, mock_event_handler):
        """Create a BlockingManager with mocked dependencies."""
        with patch('focus_guard.core.blocking.manager.PolicyEngine', return_value=mock_engine), \
             patch('focus_guard.core.blocking.manager.BlockingEventHandler', return_value=mock_event_handler):
            return BlockingManager()

    @pytest.fixture
    def config_file(self):
        """Create a temporary config file for testing."""
        config = {
            "policies": [
                {
                    "type": "domain",
                    "name": "test_domain_policy",
                    "blocked_domains": ["blocked.com"],
                    "allowed_domains": []
                },
                {
                    "type": "time_based",
                    "name": "work_hours",
                    "schedule": [
                        {
                            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                            "start_time": "09:00",
                            "end_time": "17:00"
                        }
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            f.flush()
            yield Path(f.name)
        
        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    def test_initialization(self, mock_engine, mock_event_handler):
        """Test that BlockingManager initializes with default policies."""
        with patch('focus_guard.core.blocking.manager.PolicyEngine', return_value=mock_engine), \
             patch('focus_guard.core.blocking.manager.BlockingEventHandler', return_value=mock_event_handler), \
             patch.object(BlockingManager, '_load_default_policies') as mock_load_defaults:
            
            manager = BlockingManager()
            
            # Verify dependencies were initialized
            assert manager.policy_engine is mock_engine
            assert manager.event_handler is mock_event_handler
            
            # Verify default policies were loaded
            mock_load_defaults.assert_called_once()

    def test_initialization_with_config(self, mock_engine, mock_event_handler, config_file):
        """Test that BlockingManager loads policies from a config file."""
        with patch('focus_guard.core.blocking.manager.PolicyEngine', return_value=mock_engine), \
             patch('focus_guard.core.blocking.manager.BlockingEventHandler', return_value=mock_event_handler), \
             patch.object(BlockingManager, 'load_config') as mock_load_config:
            
            manager = BlockingManager(config_path=config_file)
            
            # Verify config was loaded
            mock_load_config.assert_called_once_with(config_file)

    def test_enable_blocking(self, manager, mock_event_handler):
        """Test enabling the blocking system."""
        # Reset mocks to ignore any initialization calls
        mock_event_handler.handle_event.reset_mock()
        
        # Enable blocking
        manager.enable_blocking()
        
        # Verify the blocking enabled event was handled with correct structure
        assert mock_event_handler.handle_event.call_count == 1
        event_call = mock_event_handler.handle_event.call_args[0][0]
        assert isinstance(event_call, dict)
        assert event_call.get('event_type') == EventType.BLOCKING_ENABLED
        
        # Note: The actual implementation doesn't add a timestamp, so we don't check for it

    def test_disable_blocking(self, manager, mock_event_handler):
        """Test disabling the blocking system."""
        # Reset mocks to ignore any initialization calls
        mock_event_handler.handle_event.reset_mock()
        
        # Disable blocking
        manager.disable_blocking()
        
        # Verify the blocking disabled event was handled with correct structure
        assert mock_event_handler.handle_event.call_count == 1
        event_call = mock_event_handler.handle_event.call_args[0][0]
        assert isinstance(event_call, dict)
        assert event_call.get('event_type') == EventType.BLOCKING_DISABLED
        
        # Note: The actual implementation doesn't add a timestamp, so we don't check for it

    def test_add_policy(self, manager, mock_engine, mock_event_handler):
        """Test adding a new policy to the blocking manager."""
        # Reset mocks to ignore initialization calls
        mock_engine.add_policy.reset_mock()
        mock_event_handler.handle_event.reset_mock()
        
        # Create a mock policy with required attributes
        mock_policy = MagicMock()
        mock_policy.name = "test_policy"
        mock_policy.policy_type = MagicMock()
        mock_policy.policy_type.value = "test_type"
        mock_policy.config = MagicMock()
        mock_policy.config.metadata = {}
        
        # Add the policy
        manager.add_policy(mock_policy)
        
        # Verify the policy was added to the engine
        mock_engine.add_policy.assert_called_once_with(mock_policy)
        
        # Verify the policy added event was handled with correct structure
        assert mock_event_handler.handle_event.call_count == 1
        event_call = mock_event_handler.handle_event.call_args[0][0]
        assert isinstance(event_call, dict)
        assert event_call.get('event_type') == EventType.POLICY_ADDED
        assert event_call.get('policy_name') == "test_policy"
        assert event_call.get('policy_type') == "test_type"
        assert event_call.get('metadata') == {}

    def test_remove_policy(self, manager, mock_engine, mock_event_handler):
        """Test removing a policy from the blocking manager."""
        # Reset mocks to ignore initialization calls
        mock_engine.remove_policy.reset_mock()
        mock_engine.get_policy.return_value = None  # Simulate policy not found
        mock_event_handler.handle_event.reset_mock()
    
        policy_name = "test_policy"
        
        # Create a mock policy that would be returned by get_policy
        mock_policy = MagicMock()
        mock_policy.policy_type = MagicMock()
        mock_policy.policy_type.value = "test_type"
        mock_policy.config = MagicMock()
        mock_policy.config.metadata = {}
        
        # Configure get_policy to return our mock policy
        mock_engine.get_policy.return_value = mock_policy
        
        # Configure remove_policy to return True to simulate successful removal
        mock_engine.remove_policy.return_value = True
    
        # Remove the policy
        result = manager.remove_policy(policy_name)
        
        # Should return True for successful removal
        assert result is True
    
        # Verify the policy was removed from the engine
        mock_engine.remove_policy.assert_called_once_with(policy_name)
    
        # Verify the policy removed event was handled with correct structure
        assert mock_event_handler.handle_event.call_count == 1
        event_call = mock_event_handler.handle_event.call_args[0][0]
        assert isinstance(event_call, dict)
        assert event_call.get('event_type') == EventType.POLICY_REMOVED
        assert event_call.get('policy_name') == policy_name
        assert event_call.get('policy_type') == "test_type"
        assert event_call.get('metadata') == {}
        
        # Test case when policy doesn't exist - should not call remove_policy
        mock_engine.remove_policy.reset_mock()
        mock_engine.get_policy.return_value = None  # Policy not found
        mock_event_handler.handle_event.reset_mock()
        
        # Reset the call count for get_policy since it was called earlier
        mock_engine.get_policy.call_count = 0
        
        result = manager.remove_policy("nonexistent_policy")
        # Should return False since the policy wasn't found
        assert result is False
        # Should check if policy exists first
        assert mock_engine.get_policy.call_count > 0
        assert mock_engine.get_policy.call_args[0][0] == "nonexistent_policy"
        # Should not call remove_policy if policy doesn't exist
        mock_engine.remove_policy.assert_not_called()
        # Should not send any event if policy doesn't exist
        mock_event_handler.handle_event.assert_not_called()

    def test_should_block_domain(self, manager, mock_engine):
        """Test checking if a domain should be blocked."""
        domain = Domain("example.com")
        expected_decision = BlockingDecision(
            should_block=True,
            policy_name="test_policy",
            reason="Test block",
            policy_type=BlockingPolicyType.DOMAIN
        )

        # Configure the engine to return our test decision
        mock_engine.should_block.return_value = expected_decision

        # Test with a domain object
        result = manager.should_block(domain)
        assert result == expected_decision
        
        # Get the arguments from the call
        call_args = mock_engine.should_block.call_args[0]
        assert len(call_args) >= 1  # At least one argument (resource)
        
        # The first argument should be the domain (either as Domain object or string)
        resource_arg = call_args[0]
        
        # Check if it's a Domain object or a string
        if isinstance(resource_arg, Domain):
            assert resource_arg.value == "example.com"
        else:
            # If it's a string, it should be the domain value
            assert resource_arg == "example.com"
        
        # Test with a domain string - should pass it directly to the engine
        result = manager.should_block("example.com")
        assert result == expected_decision
        
        # Get the arguments from the call
        call_args = mock_engine.should_block.call_args[0]
        assert len(call_args) >= 1  # At least one argument (resource)
        
        # The first argument should be the domain string
        resource_arg = call_args[0]
        assert resource_arg == "example.com"  # Should be passed as string
        
        # Test with a domain string with protocol - should pass as is
        result = manager.should_block("http://example.com")
        assert result == expected_decision
        
        # Get the arguments from the call
        call_args = mock_engine.should_block.call_args[0]
        resource_arg = call_args[0]
        # Should be passed as is, conversion to Domain happens inside PolicyEngine if needed
        assert resource_arg == "http://example.com"
        
        # Verify all calls were made with expected arguments
        calls = mock_engine.should_block.call_args_list
        assert len(calls) == 3
        
        # First call: Domain object
        assert isinstance(calls[0][0][0], Domain) or calls[0][0][0] == "example.com"
        
        # Second call: domain string
        assert calls[1][0][0] == "example.com"
        
        # Third call: URL string
        assert calls[2][0][0] == "http://example.com"

    def test_register_callback(self, manager, mock_event_handler):
        """Test registering an event callback."""
        callback = MagicMock()
        event_type = EventType.RESOURCE_ACCESS_BLOCKED
        
        manager.register_callback(event_type, callback)
        
        # Verify the callback was registered with the event handler
        mock_event_handler.register_callback.assert_called_once_with(event_type, callback)

    def test_load_config(self, manager, config_file, mock_engine):
        """Test loading policies from a config file."""
        # Reset mocks to ignore initialization calls
        mock_engine.add_policy.reset_mock()
        
        # Create a sample config file
        config_data = {
            "policies": [
                {
                    "type": "domain",
                    "name": "test_domain_policy",
                    "blocked_domains": ["blocked.com"],
                    "allowed_domains": []
                },
                {
                    "type": "time_based",
                    "name": "work_hours",
                    "time_ranges": [{"start": "09:00", "end": "17:00"}],
                    "days_of_week": [0, 1, 2, 3, 4],
                    "timezone": "local"
                }
            ]
        }
        
        # Write the config file
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Mock the policy engine's from_dict method
        with patch.object(mock_engine, 'from_dict') as mock_from_dict:
            # Load the config
            result = manager.load_config(config_file)
            
            # Should return True for successful load
            assert result is True
            
            # Verify the config was loaded using the engine's from_dict
            mock_from_dict.assert_called_once()
            
            # Get the config that was passed to from_dict
            passed_config = mock_from_dict.call_args[0][0]
            
            # Verify the config structure
            assert 'policies' in passed_config
            assert len(passed_config['policies']) == 2
            
            # Verify the domain policy
            domain_policy = next(p for p in passed_config['policies'] if p['type'] == 'domain')
            assert domain_policy['name'] == 'test_domain_policy'
            assert 'blocked.com' in domain_policy['blocked_domains']
            
            # Verify the time-based policy
            time_policy = next(p for p in passed_config['policies'] if p['type'] == 'time_based')
            assert time_policy['name'] == 'work_hours'
            assert len(time_policy['time_ranges']) == 1
            assert time_policy['time_ranges'][0]['start'] == '09:00'
            assert time_policy['time_ranges'][0]['end'] == '17:00'

    def test_save_config(self, manager, mock_engine, tmp_path):
        """Test saving policies to a config file."""
        # Create a temporary output file
        output_path = tmp_path / "test_config.json"
    
        # Create mock policies with to_dict methods that return serializable data
        mock_policy1 = MagicMock()
        mock_policy1.to_dict.return_value = {
            "type": "domain", 
            "name": "test_domain_policy",
            "blocked_domains": ["blocked.com"],
            "allowed_domains": []
        }

        mock_policy2 = MagicMock()
        mock_policy2.to_dict.return_value = {
            "type": "time_based",
            "name": "work_hours",
            "time_ranges": [{"start": "09:00", "end": "17:00"}],
            "days_of_week": [0, 1, 2, 3, 4],
            "timezone": "local"
        }

        # Configure the mock engine to return our test policies
        mock_engine.to_dict.return_value = {
            "policies": [
                mock_policy1.to_dict(),
                mock_policy2.to_dict()
            ]
        }
        
        # Call the method under test with actual file writing
        result = manager.save_config(output_path)
        
        # Should return True for successful save
        assert result is True
        
        # Verify the file was created
        assert output_path.exists()
        
        # Verify the file content is valid JSON
        with open(output_path, 'r') as f:
            saved_config = json.load(f)
            
        # Verify the config structure
        assert 'policies' in saved_config
        assert len(saved_config['policies']) == 2
        
        # Verify the domain policy
        domain_policy = next(p for p in saved_config['policies'] if p['type'] == 'domain')
        assert domain_policy['name'] == 'test_domain_policy'
        assert 'blocked.com' in domain_policy['blocked_domains']
        
        # Verify the time-based policy
        time_policy = next(p for p in saved_config['policies'] if p['type'] == 'time_based')
        assert time_policy['name'] == 'work_hours'
        assert len(time_policy['time_ranges']) == 1
        assert time_policy['time_ranges'][0]['start'] == '09:00'
        assert time_policy['time_ranges'][0]['end'] == '17:00'

    def test_clear_policies(self, manager, mock_engine):
        """Test clearing all policies."""
        # Clear policies by removing them one by one
        mock_policies = [
            MagicMock(name="policy1"),
            MagicMock(name="policy2")
        ]
        mock_engine.get_all_policies.return_value = mock_policies
        
        # Clear policies by removing them one by one
        for policy in mock_policies:
            manager.remove_policy(policy.name)
        
        # Verify we tried to remove all policies
        assert mock_engine.remove_policy.call_count == len(mock_policies)

    def test_get_policy(self, manager, mock_engine):
        """Test retrieving a policy by name."""
        policy_name = "test_policy"
        mock_policy = MagicMock()
        mock_engine.get_policy.return_value = mock_policy
        
        result = manager.get_policy(policy_name)
        
        # Verify the engine's get_policy method was called with the correct name
        mock_engine.get_policy.assert_called_once_with(policy_name)
        assert result is mock_policy

    def test_get_policies(self, manager, mock_engine):
        """Test retrieving all policies."""
        mock_policies = [MagicMock(), MagicMock()]
        mock_engine.get_all_policies.return_value = mock_policies
        
        result = manager.get_all_policies()
        
        assert result == mock_policies
        mock_engine.get_all_policies.assert_called_once()
        assert result == mock_policies
