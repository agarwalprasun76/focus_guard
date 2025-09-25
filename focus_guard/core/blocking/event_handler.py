"""
Event handler for blocking-related events.

This module implements an event handler that processes blocking-related events
and takes appropriate actions based on the current policies.
"""

import logging
from typing import Dict, Any, Optional, Callable, List, Set

from .engine import PolicyEngine, BlockingDecision
from .events import (
    BlockingEvent, ResourceAccessEvent, PolicyEvent, OverrideEvent, EventType,
    create_event
)
from focus_guard.core.domain.models import Domain


class BlockingEventHandler:
    """
    Handles blocking-related events and takes appropriate actions.
    
    This class acts as the bridge between the activity monitoring system
    and the blocking system, ensuring that they remain decoupled.
    """
    
    def __init__(self, policy_engine: PolicyEngine):
        """
        Initialize the event handler.
        
        Args:
            policy_engine: The policy engine to use for making blocking decisions.
        """
        self.policy_engine = policy_engine
        self._event_handlers = {
            EventType.RESOURCE_ACCESS_ATTEMPT: self._handle_resource_access_attempt,
            EventType.RESOURCE_ACCESS_BLOCKED: self._handle_resource_access_blocked,
            EventType.RESOURCE_ACCESS_ALLOWED: self._handle_resource_access_allowed,
            EventType.POLICY_ADDED: self._handle_policy_added,
            EventType.POLICY_REMOVED: self._handle_policy_removed,
            EventType.POLICY_UPDATED: self._handle_policy_updated,
            EventType.OVERRIDE_REQUESTED: self._handle_override_requested,
            EventType.OVERRIDE_GRANTED: self._handle_override_granted,
            EventType.OVERRIDE_DENIED: self._handle_override_denied,
            EventType.BLOCKING_ENABLED: self._handle_blocking_enabled,
            EventType.BLOCKING_DISABLED: self._handle_blocking_disabled,
            EventType.TAB_NAVIGATION: self._handle_tab_navigation,
            EventType.TAB_CLOSED: self._handle_tab_closed,
            EventType.APPLICATION_LAUNCH: self._handle_application_launch,
            EventType.APPLICATION_TERMINATED: self._handle_application_terminated,
        }
        self._logger = logging.getLogger("core.blocking.event_handler")
        self._callbacks: Dict[EventType, List[Callable[[BlockingEvent], None]]] = {}
        self._active_overrides: Dict[str, float] = {}  # resource_id -> expiry_timestamp
    
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
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)
    
    def unregister_callback(
        self,
        event_type: EventType,
        callback: Callable[[BlockingEvent], None]
    ) -> None:
        """
        Unregister a callback for a specific event type.
        
        Args:
            event_type: The type of event to stop listening for.
            callback: The callback function to remove.
        """
        if event_type in self._callbacks:
            if callback in self._callbacks[event_type]:
                self._callbacks[event_type].remove(callback)
    
    def _notify_callbacks(self, event: BlockingEvent) -> None:
        """
        Notify all registered callbacks for the event's type.
        
        Args:
            event: The event to notify callbacks about.
        """
        for callback in self._callbacks.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                self._logger.error(
                    f"Error in callback for event {event.event_type}: {e}",
                    exc_info=True
                )
    
    def handle_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle an incoming event.
        
        Args:
            event_data: The event data as a dictionary.
        """
        try:
            event = create_event(event_data)
            self._logger.debug(f"Processing event: {event.event_type}")
            
            # Let the appropriate handler process the event
            handler = self._event_handlers.get(event.event_type)
            if handler:
                handler(event)
            
            # Notify any registered callbacks
            self._notify_callbacks(event)
            
        except Exception as e:
            self._logger.error(f"Error handling event: {e}", exc_info=True)
    
    def _handle_resource_access_attempt(self, event: ResourceAccessEvent) -> None:
        """
        Handle a resource access attempt event.
        
        Args:
            event: The resource access attempt event.
        """
        # Extract resource information from the event
        resource = event.resource_id  # Get the resource ID (domain string)
        context = event.metadata.get("context", {})
        
        # Make a decision based on the resource type
        if hasattr(event, 'resource') and isinstance(event.resource, Domain):
            domain = event.resource
            decision = self.policy_engine.evaluate_domain(domain, context=context)
        elif resource:
            # Try to parse as a domain
            try:
                domain = Domain(resource)
                decision = self.policy_engine.evaluate_domain(domain, context=context)
            except ValueError:
                # Not a valid domain, evaluate as a generic resource
                decision = self.policy_engine.evaluate_resource(resource, context=context)
        else:
            # Evaluate as a generic resource
            decision = self.policy_engine.evaluate_resource(resource, context=context)
        
        if decision.should_block:
            self._logger.info(
                f"Blocking access to {event.resource_id}: {decision.reason}"
            )
            # Create a blocked event
            blocked_event = ResourceAccessEvent(
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                action="block",
                reason=decision.reason,
                metadata={
                    "policy_name": decision.policy_name,
                    "policy_type": decision.policy_type.value,
                    **event.metadata
                }
            )
            self._notify_callbacks(blocked_event)
    
    def _handle_resource_access_blocked(self, event: ResourceAccessEvent) -> None:
        """Handle a resource access blocked event."""
        self._logger.info(
            f"Access to {event.resource_id} was blocked: {event.reason}"
        )
    
    def _handle_resource_access_allowed(self, event: ResourceAccessEvent) -> None:
        """Handle a resource access allowed event."""
        self._logger.debug(
            f"Access to {event.resource_id} was allowed: {event.reason}"
        )
    
    def _handle_policy_added(self, event: PolicyEvent) -> None:
        """Handle a policy added event."""
        self._logger.info(f"Policy added: {event.policy_name} ({event.policy_type})")
    
    def _handle_policy_removed(self, event: PolicyEvent) -> None:
        """Handle a policy removed event."""
        self._logger.info(f"Policy removed: {event.policy_name}")
    
    def _handle_policy_updated(self, event: PolicyEvent) -> None:
        """Handle a policy updated event."""
        self._logger.info(f"Policy updated: {event.policy_name}")
    
    def _handle_override_requested(self, event: OverrideEvent) -> None:
        """Handle an override requested event."""
        self._logger.info(
            f"Override requested for {event.resource_id}: {event.reason}"
        )
        # In a real implementation, this would trigger a user prompt
        # For now, we'll auto-approve with the requested duration
        self._approve_override(event)
    
    def _handle_override_granted(self, event: OverrideEvent) -> None:
        """Handle an override granted event."""
        expiry_time = event.timestamp + (event.duration_seconds or 0)
        self._active_overrides[event.resource_id] = expiry_time
        self._logger.info(
            f"Override granted for {event.resource_id} "
            f"until {expiry_time} (duration: {event.duration_seconds}s)"
        )
    
    def _handle_override_denied(self, event: OverrideEvent) -> None:
        """Handle an override denied event."""
        self._logger.info(f"Override denied for {event.resource_id}")
    
    def _handle_blocking_enabled(self, event: BlockingEvent) -> None:
        """Handle blocking enabled event."""
        self._logger.info("Blocking system enabled")
    
    def _handle_blocking_disabled(self, event: BlockingEvent) -> None:
        """Handle blocking disabled event."""
        self._logger.info("Blocking system disabled")
    
    def _handle_tab_navigation(self, event: BlockingEvent) -> None:
        """Handle tab navigation event."""
        domain = event.metadata.get("domain")
        if domain:
            self._logger.debug(f"Tab navigated to {domain}")
    
    def _handle_tab_closed(self, event: BlockingEvent) -> None:
        """Handle tab closed event."""
        domain = event.metadata.get("domain")
        if domain:
            self._logger.debug(f"Tab closed for {domain}")
    
    def _handle_application_launch(self, event: BlockingEvent) -> None:
        """Handle application launch event."""
        app_name = event.metadata.get("application_name")
        if app_name:
            self._logger.debug(f"Application launched: {app_name}")
    
    def _handle_application_terminated(self, event: BlockingEvent) -> None:
        """Handle application terminated event."""
        app_name = event.metadata.get("application_name")
        if app_name:
            self._logger.debug(f"Application terminated: {app_name}")
    
    def _approve_override(self, event: OverrideEvent) -> None:
        """
        Approve an override request.
        
        In a real implementation, this would involve user interaction.
        """
        approved_event = OverrideEvent(
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            duration_seconds=event.duration_seconds or 3600,  # Default to 1 hour
            reason="Auto-approved for testing",
            event_type=EventType.OVERRIDE_GRANTED,
            metadata=event.metadata
        )
        self._notify_callbacks(approved_event)
