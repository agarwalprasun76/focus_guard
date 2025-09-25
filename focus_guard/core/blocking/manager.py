"""
Blocking manager for the Focus Guard system.

This module provides the main interface for the blocking system,
coordinating between the policy engine and event handler.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Union

from .engine import PolicyEngine, BlockingDecision
from .event_handler import BlockingEventHandler, BlockingEvent, EventType
from .policies import (
    BlockingPolicy, BlockingPolicyConfig,
    TimeBasedBlockingPolicy, DomainBlockingPolicy
)
from focus_guard.core.domain.models import Domain, Category


class BlockingManager:
    """
    Manages the blocking system, including policies and event handling.
    
    This class serves as the main entry point for the blocking functionality,
    providing a high-level API for managing policies and handling events.
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize the blocking manager.
        
        Args:
            config_path: Optional path to a JSON configuration file.
        """
        self.policy_engine = PolicyEngine()
        self.event_handler = BlockingEventHandler(self.policy_engine)
        self._logger = logging.getLogger("core.blocking.manager")
        
        # Load default policies if no config is provided
        if config_path is None:
            self._load_default_policies()
        else:
            self.load_config(config_path)
    
    def _load_default_policies(self) -> None:
        """Load default blocking policies."""
        self._logger.info("Loading default blocking policies")
        
        # Example: Block social media during work hours
        work_hours_policy = TimeBasedBlockingPolicy.create(
            name="Work Hours - Block Social Media",
            time_ranges=[
                {"start": "09:00", "end": "17:00"}  # 9 AM to 5 PM
            ],
            days_of_week={0, 1, 2, 3, 4},  # Monday to Friday
            timezone="local",
            description="Blocks distracting websites during work hours",
            priority=10
        )
        
        # Example: Block adult content
        adult_content_policy = DomainBlockingPolicy.create(
            name="Block Adult Content",
            blocked_categories={
                Category.ADULT, Category.GAMING, Category.MALICIOUS
            },
            description="Blocks adult, gaming, and malicious content",
            priority=20
        )
        
        self.add_policy(work_hours_policy)
        self.add_policy(adult_content_policy)
    
    def add_policy(self, policy: BlockingPolicy) -> None:
        """
        Add a blocking policy.
        
        Args:
            policy: The policy to add.
        """
        self.policy_engine.add_policy(policy)
        self._logger.info(f"Added policy: {policy.name} ({policy.policy_type})")
        
        # Notify about the policy addition
        self.event_handler.handle_event({
            "event_type": EventType.POLICY_ADDED,
            "policy_name": policy.name,
            "policy_type": policy.policy_type.value,
            "metadata": policy.config.metadata
        })
    
    def remove_policy(self, policy_name: str) -> bool:
        """
        Remove a blocking policy.
        
        Args:
            policy_name: The name of the policy to remove.
            
        Returns:
            bool: True if the policy was removed, False if not found.
        """
        policy = self.policy_engine.get_policy(policy_name)
        if policy and self.policy_engine.remove_policy(policy_name):
            self._logger.info(f"Removed policy: {policy_name}")
            
            # Notify about the policy removal
            self.event_handler.handle_event({
                "event_type": EventType.POLICY_REMOVED,
                "policy_name": policy_name,
                "policy_type": policy.policy_type.value,
                "metadata": policy.config.metadata
            })
            return True
        return False
    
    def get_policy(self, name: str) -> Optional[BlockingPolicy]:
        """
        Get a policy by name.
        
        Args:
            name: The name of the policy to retrieve.
            
        Returns:
            Optional[BlockingPolicy]: The policy, or None if not found.
        """
        return self.policy_engine.get_policy(name)
    
    def get_all_policies(self) -> List[BlockingPolicy]:
        """
        Get all policies.
        
        Returns:
            List[BlockingPolicy]: A list of all policies, sorted by priority.
        """
        return self.policy_engine.get_all_policies()
    
    def should_block(self, resource: Union[Domain, str], context: Optional[Dict[str, Any]] = None) -> BlockingDecision:
        """
        Determine if a resource should be blocked.
        
        Args:
            resource: The resource to check (domain, application name, etc.)
            context: Additional context for the decision
            
        Returns:
            BlockingDecision: The blocking decision.
        """
        return self.policy_engine.should_block(resource, context)
    
    def handle_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle an incoming event.
        
        Args:
            event_data: The event data as a dictionary.
        """
        self.event_handler.handle_event(event_data)
    
    def register_callback(
        self,
        event_type: EventType,
        callback: Callable[[BlockingEvent], None]
    ) -> None:
        """
        Register a callback for a specific event type.
        
        Args:
            event_type: The type of event to listen for.
            callback: The function to call when the event occurs.
        """
        self.event_handler.register_callback(event_type, callback)
    
    def load_config(self, config_path: Union[str, Path]) -> bool:
        """
        Load blocking configuration from a file.
        
        Args:
            config_path: Path to the configuration file.
            
        Returns:
            bool: True if the configuration was loaded successfully, False otherwise.
        """
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                self._logger.warning(f"Config file not found: {config_path}")
                return False
                
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            self.policy_engine.from_dict(config_data)
            self._logger.info(f"Loaded blocking configuration from {config_path}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to load blocking config: {e}", exc_info=True)
            return False
    
    def save_config(self, config_path: Union[str, Path]) -> bool:
        """
        Save the current blocking configuration to a file.
        
        Args:
            config_path: Path to save the configuration to.
            
        Returns:
            bool: True if the configuration was saved successfully, False otherwise.
        """
        try:
            config_path = Path(config_path)
            config_data = self.policy_engine.to_dict()
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self._logger.info(f"Saved blocking configuration to {config_path}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to save blocking config: {e}", exc_info=True)
            return False
    
    def enable_blocking(self) -> None:
        """Enable the blocking system."""
        self._logger.info("Blocking system enabled")
        self.event_handler.handle_event({
            "event_type": EventType.BLOCKING_ENABLED
        })
    
    def disable_blocking(self) -> None:
        """Disable the blocking system."""
        self._logger.info("Blocking system disabled")
        self.event_handler.handle_event({
            "event_type": EventType.BLOCKING_DISABLED
        })
