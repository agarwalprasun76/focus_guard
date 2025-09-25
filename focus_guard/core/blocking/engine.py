"""
Blocking policy engine.

This module implements the core engine for evaluating blocking policies.
"""

import logging
from typing import Dict, List, Optional, Set, Type, TypeVar, Union, Any
from dataclasses import dataclass, field
from datetime import datetime

from .policies.base import BlockingPolicy, BlockingPolicyConfig, BlockingPolicyType
from .policies.time_based import TimeBasedBlockingPolicy, TimeBasedBlockingConfig
from .policies.domain import DomainBlockingPolicy, DomainBlockingConfig
from focus_guard.core.domain.models import Domain


@dataclass
class BlockingDecision:
    """The result of evaluating a blocking policy."""
    should_block: bool
    policy_name: str
    reason: str
    policy_type: BlockingPolicyType
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)


class PolicyEngine:
    """
    The core policy engine that evaluates blocking policies.
    
    This class manages a collection of blocking policies and provides methods
    to evaluate them against resources.
    """
    
    def __init__(self):
        """Initialize the policy engine."""
        self._policies: Dict[str, BlockingPolicy] = {}
        self._policy_types: Dict[BlockingPolicyType, Type[BlockingPolicy]] = {
            BlockingPolicyType.TIME_BASED: TimeBasedBlockingPolicy,
            BlockingPolicyType.DOMAIN: DomainBlockingPolicy,
        }
        self._config_types: Dict[BlockingPolicyType, Type[BlockingPolicyConfig]] = {
            BlockingPolicyType.TIME_BASED: TimeBasedBlockingConfig,
            BlockingPolicyType.DOMAIN: DomainBlockingConfig,
        }
        self._logger = logging.getLogger("core.blocking.engine")
    
    def add_policy(self, policy: BlockingPolicy) -> None:
        """
        Add a policy to the engine.

        Args:
            policy: The policy to add.

        Note:
            If a policy with the same name already exists, it will be replaced.
        """
        self._policies[policy.name] = policy
        self._logger.info(f"Added/Updated policy '{policy.name}' of type {policy.policy_type}")
        
    def remove_policy(self, policy_name: str) -> bool:
        """
        Remove a policy from the engine.

        Args:
            policy_name: The name of the policy to remove.
            
        Returns:
            bool: True if the policy was removed, False if it didn't exist.
        """
        if policy_name in self._policies:
            del self._policies[policy_name]
            self._logger.info(f"Removed policy '{policy_name}'")
            return True
        return False
        
    def clear_policies(self) -> None:
        """Remove all policies from the engine."""
        self._policies.clear()
        self._logger.info("Cleared all policies")
        
    def evaluate_resource(
        self, 
        resource: Union[Domain, str], 
        context: Optional[Dict[str, Any]] = None
    ) -> BlockingDecision:
        """
        Evaluate a resource against all policies.

        Args:
            resource: The resource to evaluate (domain, URL, etc.)
            context: Optional context for the evaluation.

        Returns:
            BlockingDecision: The result of the evaluation.
        """
        if not self._policies:
            return BlockingDecision(
                should_block=False,
                policy_name="",
                reason="No blocking policies configured",
                policy_type=BlockingPolicyType.CUSTOM
            )
            
        context = context or {}
        
        # Add timestamp if not provided
        if 'timestamp' not in context:
            context['timestamp'] = datetime.now()
            
        # Check each policy in priority order
        policies = sorted(
            [p for p in self._policies.values() if getattr(p, 'is_enabled', True)],
            key=lambda p: getattr(p, 'priority', 0),
            reverse=True
        )
            
        for policy in policies:
            try:
                # Check if policy implements evaluate() method
                if hasattr(policy, 'evaluate') and callable(policy.evaluate):
                    decision = policy.evaluate(resource, context=context)
                    
                    # If the policy returns a boolean, convert it to a BlockingDecision
                    if isinstance(decision, bool):
                        decision = BlockingDecision(
                            should_block=decision,
                            policy_name=getattr(policy, 'name', ''),
                            reason="Blocked by policy" if decision else "Allowed by policy",
                            policy_type=getattr(policy, 'policy_type', BlockingPolicyType.CUSTOM)
                        )
                    
                    # If we have a BlockingDecision, ensure it has the policy name
                    if isinstance(decision, BlockingDecision):
                        # Update the policy name if not set in the decision
                        if not getattr(decision, 'policy_name', ''):
                            decision.policy_name = getattr(policy, 'name', '')
                        # Update the policy type if not set in the decision
                        if not hasattr(decision, 'policy_type') or not decision.policy_type:
                            decision.policy_type = getattr(policy, 'policy_type', BlockingPolicyType.CUSTOM)
                        
                        if decision.should_block:
                            return decision
                        # Return the decision even if not blocking to preserve the policy name
                        return decision
                # Fall back to should_block()/get_block_reason() interface
                elif hasattr(policy, 'should_block') and callable(policy.should_block):
                    if policy.should_block(resource, context=context):
                        reason = ''
                        if hasattr(policy, 'get_block_reason') and callable(policy.get_block_reason):
                            reason = policy.get_block_reason(resource, context=context)
                        return BlockingDecision(
                            should_block=True,
                            policy_name=getattr(policy, 'name', ''),
                            reason=reason or 'Blocked by policy',
                            policy_type=getattr(policy, 'policy_type', BlockingPolicyType.CUSTOM),
                            metadata={}
                        )
                    else:
                        # Return a non-blocking decision with the policy name
                        return BlockingDecision(
                            should_block=False,
                            policy_name=getattr(policy, 'name', ''),
                            reason="Allowed by policy",
                            policy_type=getattr(policy, 'policy_type', BlockingPolicyType.CUSTOM),
                            metadata={}
                        )
            except Exception as e:
                self._logger.error(
                    f"Error evaluating policy '{getattr(policy, 'name', 'unknown')}': {e}",
                    exc_info=True
                )
        
        # Default to not blocking
        return BlockingDecision(
            should_block=False,
            policy_name="",
            reason="No matching blocking policies found.",
            policy_type=BlockingPolicyType.CUSTOM
        )
    
    def get_policy(self, name: str) -> Optional[BlockingPolicy]:
        """
        Get a policy by name.
        
        Args:
            name: The name of the policy to get.
            
        Returns:
            Optional[BlockingPolicy]: The policy, or None if not found.
        """
        # First try direct lookup
        if name in self._policies:
            return self._policies[name]
            
        # If not found, try case-insensitive search
        for policy_name, policy in self._policies.items():
            if policy_name.lower() == name.lower():
                return policy
                
        return None
    
    def get_all_policies(self) -> List[BlockingPolicy]:
        """
        Get all policies in the engine.
        
        Returns:
            List[BlockingPolicy]: A list of all policies, sorted by priority.
        """
        return sorted(
            self._policies.values(),
            key=lambda p: (p.config.priority, p.name),
            reverse=True
        )
    
    def should_block(
        self,
        resource: Union[Domain, str],
        context: Optional[Dict[str, Any]] = None
    ) -> BlockingDecision:
        """
        Determine if a resource should be blocked based on the current policies.
        
        This evaluates all enabled policies in order of priority until a blocking
        decision is made.
        
        Args:
            resource: The resource to check (domain, application name, etc.)
            context: Additional context for the decision
            
        Returns:
            BlockingDecision: The result of the evaluation.
        """
        context = context or {}
        
        # Add timestamp if not provided
        if 'timestamp' not in context:
            context['timestamp'] = datetime.now()
        
        # Check each policy in priority order
        for policy in self.get_all_policies():
            if not policy.is_enabled:
                continue
                
            try:
                if policy.should_block(resource, context):
                    reason = policy.get_block_reason(resource, context)
                    return BlockingDecision(
                        should_block=True,
                        policy_name=policy.name,
                        reason=reason,
                        policy_type=policy.policy_type,
                        metadata=policy.config.metadata
                    )
            except Exception as e:
                self._logger.error(
                    f"Error evaluating policy '{policy.name}': {e}",
                    exc_info=True
                )
        
        # Default to not blocking
        return BlockingDecision(
            should_block=False,
            policy_name="",
            reason="No matching blocking policies found.",
            policy_type=BlockingPolicyType.CUSTOM
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert all policies to a dictionary representation.
        
        Returns:
            Dict[str, Any]: A dictionary containing all policies' configurations.
        """
        return {
            "policies": [
                policy.config.to_dict()
                for policy in self.get_all_policies()
            ]
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load policies from a dictionary representation.
        
        Args:
            data: The dictionary containing policy configurations.
            
        Raises:
            ValueError: If a policy configuration is invalid.
        """
        if not isinstance(data, dict) or "policies" not in data:
            raise ValueError("Invalid policy configuration format.")
        
        self._policies.clear()
        
        for policy_data in data["policies"]:
            try:
                policy_type = BlockingPolicyType(policy_data["type"])
                config_class = self._config_types.get(policy_type)
                policy_class = self._policy_types.get(policy_type)
                
                if not config_class or not policy_class:
                    self._logger.warning(
                        f"Skipping unknown policy type: {policy_type}"
                    )
                    continue
                
                # Create config and policy instances
                config = config_class(**policy_data)
                policy = policy_class(config)
                self.add_policy(policy)
                
            except Exception as e:
                self._logger.error(
                    f"Failed to load policy: {policy_data.get('name', 'unknown')}",
                    exc_info=True
                )
                continue
