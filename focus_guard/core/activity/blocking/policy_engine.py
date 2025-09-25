"""
Policy engine for evaluating blocking rules and making blocking decisions.

This module provides the PolicyEngine class that evaluates blocking policies
against applications and domains to make blocking decisions.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from focus_guard.core.activity.blocking.models import (
    BlockingPolicy, BlockingDecision, BlockingAction, BlockingEvent, OverrideRequest
)
from focus_guard.core.activity.models import WindowInfo

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Engine for evaluating blocking policies and making blocking decisions.
    
    This class manages blocking policies, evaluates them against applications
    and domains, and makes decisions about whether to block, warn, or allow access.
    """
    
    def __init__(self):
        """Initialize the policy engine."""
        self.policies: List[BlockingPolicy] = []
        self.active_overrides: Dict[str, Dict[str, Any]] = {}  # app_name -> override_info
        self.usage_tracking: Dict[str, Dict[str, Any]] = defaultdict(dict)  # app_name -> usage_data
        self.blocking_events: List[BlockingEvent] = []
        
    def add_policy(self, policy: BlockingPolicy):
        """
        Add a blocking policy to the engine.
        
        Args:
            policy: The blocking policy to add
        """
        self.policies.append(policy)
        self._sort_policies_by_priority()
        logger.info(f"Added blocking policy: {policy.name}")
    
    def remove_policy(self, policy_name: str) -> bool:
        """
        Remove a blocking policy by name.
        
        Args:
            policy_name: Name of the policy to remove
            
        Returns:
            bool: True if policy was found and removed, False otherwise
        """
        for i, policy in enumerate(self.policies):
            if policy.name == policy_name:
                removed_policy = self.policies.pop(i)
                logger.info(f"Removed blocking policy: {removed_policy.name}")
                return True
        return False
    
    def get_policy(self, policy_name: str) -> Optional[BlockingPolicy]:
        """
        Get a policy by name.
        
        Args:
            policy_name: Name of the policy to retrieve
            
        Returns:
            Optional[BlockingPolicy]: The policy if found, None otherwise
        """
        for policy in self.policies:
            if policy.name == policy_name:
                return policy
        return None
    
    def update_policy(self, policy_name: str, updated_policy: BlockingPolicy) -> bool:
        """
        Update an existing policy.
        
        Args:
            policy_name: Name of the policy to update
            updated_policy: The updated policy
            
        Returns:
            bool: True if policy was found and updated, False otherwise
        """
        for i, policy in enumerate(self.policies):
            if policy.name == policy_name:
                updated_policy.updated_at = datetime.now()
                self.policies[i] = updated_policy
                self._sort_policies_by_priority()
                logger.info(f"Updated blocking policy: {policy_name}")
                return True
        return False
    
    def _sort_policies_by_priority(self):
        """Sort policies by priority (higher priority first)."""
        self.policies.sort(key=lambda p: p.priority, reverse=True)
    
    def evaluate_application(self, window_info: WindowInfo) -> BlockingDecision:
        """
        Evaluate an application against all policies and make a blocking decision.
        
        Args:
            window_info: Information about the application window
            
        Returns:
            BlockingDecision: The decision made by the policy engine
        """
        app_name = window_info.app_name
        domain = str(window_info.domain) if window_info.domain else None
        
        # Check for active overrides first
        if self._has_active_override(app_name, domain):
            return BlockingDecision(
                policy_name="override",
                action=BlockingAction.ALLOW,
                reason="Active override in effect",
                app_name=app_name,
                domain=domain,
                window_title=window_info.window_title
            )
        
        # Evaluate policies in priority order
        for policy in self.policies:
            if not policy.enabled:
                continue
            
            decision = self._evaluate_policy(policy, window_info)
            if decision:
                # Update usage tracking
                self._update_usage_tracking(app_name, domain, decision)
                
                # Log the decision
                self._log_decision(decision)
                
                return decision
        
        # No matching policy - allow by default
        return BlockingDecision(
            policy_name="default",
            action=BlockingAction.ALLOW,
            reason="No matching policy found",
            app_name=app_name,
            domain=domain,
            window_title=window_info.window_title
        )
    
    def _evaluate_policy(self, policy: BlockingPolicy, window_info: WindowInfo) -> Optional[BlockingDecision]:
        """
        Evaluate a single policy against the window information.
        
        Args:
            policy: The policy to evaluate
            window_info: Information about the application window
            
        Returns:
            Optional[BlockingDecision]: Decision if policy matches, None otherwise
        """
        app_name = window_info.app_name
        domain = str(window_info.domain) if window_info.domain else None
        
        # Check if policy matches this application or domain
        app_matches = policy.matches_application(app_name)
        domain_matches = policy.matches_domain(domain) if domain else False
        
        if not (app_matches or domain_matches):
            return None
        
        # Check time restrictions
        if policy.is_time_restricted():
            return BlockingDecision(
                policy_name=policy.name,
                action=policy.action,
                reason=f"Time restriction active: {policy.name}",
                app_name=app_name,
                domain=domain,
                window_title=window_info.window_title,
                grace_period_seconds=policy.grace_period_seconds,
                warning_message=policy.warning_message,
                redirect_url=policy.redirect_url,
                override_allowed=policy.override_allowed
            )
        
        # Check usage limits (if implemented)
        if self._exceeds_usage_limits(policy, app_name, domain):
            return BlockingDecision(
                policy_name=policy.name,
                action=policy.action,
                reason=f"Usage limit exceeded: {policy.name}",
                app_name=app_name,
                domain=domain,
                window_title=window_info.window_title,
                grace_period_seconds=policy.grace_period_seconds,
                warning_message=policy.warning_message,
                redirect_url=policy.redirect_url,
                override_allowed=policy.override_allowed
            )
        
        # Policy matches but no restrictions are active
        if policy.action != BlockingAction.ALLOW:
            return BlockingDecision(
                policy_name=policy.name,
                action=policy.action,
                reason=f"Blocked by policy: {policy.name}",
                app_name=app_name,
                domain=domain,
                window_title=window_info.window_title,
                grace_period_seconds=policy.grace_period_seconds,
                warning_message=policy.warning_message,
                redirect_url=policy.redirect_url,
                override_allowed=policy.override_allowed
            )
        
        return None
    
    def _exceeds_usage_limits(self, policy: BlockingPolicy, app_name: str, domain: Optional[str]) -> bool:
        """
        Check if the application exceeds usage limits defined in the policy.
        
        Args:
            policy: The policy to check
            app_name: Name of the application
            domain: Domain (if applicable)
            
        Returns:
            bool: True if usage limits are exceeded
        """
        # This is a placeholder for usage limit checking
        # In a full implementation, this would check against time restrictions
        # and usage tracking data
        return False
    
    def _has_active_override(self, app_name: str, domain: Optional[str]) -> bool:
        """
        Check if there's an active override for the application/domain.
        
        Args:
            app_name: Name of the application
            domain: Domain (if applicable)
            
        Returns:
            bool: True if there's an active override
        """
        key = f"{app_name}:{domain or ''}"
        if key in self.active_overrides:
            override_info = self.active_overrides[key]
            expiry = override_info['expiry']
            if datetime.now() < expiry:
                return True
            else:
                # Override has expired, remove it
                del self.active_overrides[key]
                logger.info(f"Override expired for {app_name}")
        
        return False
    
    def _update_usage_tracking(self, app_name: str, domain: Optional[str], decision: BlockingDecision):
        """
        Update usage tracking information.
        
        Args:
            app_name: Name of the application
            domain: Domain (if applicable)
            decision: The blocking decision made
        """
        key = f"{app_name}:{domain or ''}"
        now = datetime.now()
        
        if key not in self.usage_tracking:
            self.usage_tracking[key] = {
                'first_seen': now,
                'last_seen': now,
                'decision_count': 0,
                'blocked_count': 0,
                'warned_count': 0,
                'allowed_count': 0
            }
        
        usage = self.usage_tracking[key]
        usage['last_seen'] = now
        usage['decision_count'] += 1
        
        if decision.action == BlockingAction.BLOCK:
            usage['blocked_count'] += 1
        elif decision.action == BlockingAction.WARN:
            usage['warned_count'] += 1
        elif decision.action == BlockingAction.ALLOW:
            usage['allowed_count'] += 1
    
    def _log_decision(self, decision: BlockingDecision):
        """
        Log a blocking decision as an event.
        
        Args:
            decision: The blocking decision to log
        """
        event = BlockingEvent(
            event_type=decision.action.value,
            app_name=decision.app_name,
            domain=decision.domain,
            window_title=decision.window_title,
            policy_name=decision.policy_name,
            reason=decision.reason
        )
        
        self.blocking_events.append(event)
        
        # Keep only recent events (last 1000)
        if len(self.blocking_events) > 1000:
            self.blocking_events = self.blocking_events[-1000:]
        
        logger.debug(f"Logged blocking decision: {decision.action.value} for {decision.app_name}")
    
    def request_override(self, override_request: OverrideRequest) -> bool:
        """
        Request an override for a blocked application.
        
        Args:
            override_request: The override request
            
        Returns:
            bool: True if override was granted, False otherwise
        """
        # Find the policy that would block this application
        matching_policy = None
        for policy in self.policies:
            if not policy.enabled:
                continue
            
            if (policy.matches_application(override_request.app_name) or 
                (override_request.domain and policy.matches_domain(override_request.domain))):
                matching_policy = policy
                break
        
        if not matching_policy:
            logger.warning(f"No matching policy found for override request: {override_request.app_name}")
            return False
        
        if not matching_policy.override_allowed:
            logger.warning(f"Override not allowed by policy: {matching_policy.name}")
            return False
        
        # Check password if required
        if matching_policy.override_password:
            if override_request.password != matching_policy.override_password:
                logger.warning(f"Invalid override password for {override_request.app_name}")
                return False
        
        # Grant the override
        key = f"{override_request.app_name}:{override_request.domain or ''}"
        expiry = datetime.now() + timedelta(minutes=override_request.duration_minutes)
        
        self.active_overrides[key] = {
            'policy_name': matching_policy.name,
            'reason': override_request.reason,
            'duration_minutes': override_request.duration_minutes,
            'expiry': expiry,
            'granted_at': datetime.now()
        }
        
        # Log the override event
        event = BlockingEvent(
            event_type="overridden",
            app_name=override_request.app_name,
            domain=override_request.domain,
            policy_name=matching_policy.name,
            reason="Override granted",
            override_reason=override_request.reason,
            override_duration_minutes=override_request.duration_minutes
        )
        self.blocking_events.append(event)
        
        logger.info(f"Override granted for {override_request.app_name} for {override_request.duration_minutes} minutes")
        return True
    
    def get_active_overrides(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all currently active overrides.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of active overrides
        """
        # Clean up expired overrides
        now = datetime.now()
        expired_keys = [
            key for key, override_info in self.active_overrides.items()
            if now >= override_info['expiry']
        ]
        
        for key in expired_keys:
            del self.active_overrides[key]
        
        return self.active_overrides.copy()
    
    def revoke_override(self, app_name: str, domain: Optional[str] = None) -> bool:
        """
        Revoke an active override.
        
        Args:
            app_name: Name of the application
            domain: Domain (if applicable)
            
        Returns:
            bool: True if override was found and revoked, False otherwise
        """
        key = f"{app_name}:{domain or ''}"
        if key in self.active_overrides:
            del self.active_overrides[key]
            logger.info(f"Override revoked for {app_name}")
            return True
        return False
    
    def get_recent_events(self, hours: int = 24) -> List[BlockingEvent]:
        """
        Get recent blocking events.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List[BlockingEvent]: List of recent blocking events
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            event for event in self.blocking_events
            if event.timestamp >= cutoff_time
        ]
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics for all tracked applications.
        
        Returns:
            Dict[str, Any]: Usage statistics
        """
        total_decisions = sum(usage['decision_count'] for usage in self.usage_tracking.values())
        total_blocked = sum(usage['blocked_count'] for usage in self.usage_tracking.values())
        total_warned = sum(usage['warned_count'] for usage in self.usage_tracking.values())
        total_allowed = sum(usage['allowed_count'] for usage in self.usage_tracking.values())
        
        return {
            'total_applications': len(self.usage_tracking),
            'total_decisions': total_decisions,
            'total_blocked': total_blocked,
            'total_warned': total_warned,
            'total_allowed': total_allowed,
            'active_policies': len([p for p in self.policies if p.enabled]),
            'total_policies': len(self.policies),
            'active_overrides': len(self.get_active_overrides()),
            'recent_events': len(self.get_recent_events(hours=1))
        }
    
    def clear_statistics(self):
        """Clear all usage statistics and events."""
        self.usage_tracking.clear()
        self.blocking_events.clear()
        logger.info("Policy engine statistics cleared")
    
    def export_policies(self) -> List[Dict[str, Any]]:
        """
        Export all policies to a list of dictionaries.
        
        Returns:
            List[Dict[str, Any]]: List of policy dictionaries
        """
        return [policy.to_dict() for policy in self.policies]
    
    def import_policies(self, policies_data: List[Dict[str, Any]], replace: bool = False):
        """
        Import policies from a list of dictionaries.
        
        Args:
            policies_data: List of policy dictionaries
            replace: If True, replace existing policies; if False, add to existing
        """
        if replace:
            self.policies.clear()
        
        for policy_data in policies_data:
            try:
                policy = BlockingPolicy.from_dict(policy_data)
                self.add_policy(policy)
            except Exception as e:
                logger.error(f"Error importing policy {policy_data.get('name', 'unknown')}: {e}")
        
        logger.info(f"Imported {len(policies_data)} policies (replace={replace})")
