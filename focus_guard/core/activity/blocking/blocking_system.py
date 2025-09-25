"""
Integrated blocking system that combines all blocking components.

This module provides the BlockingSystem class that integrates the policy engine,
application blocker, and notification manager into a cohesive blocking system.
"""

import threading
import time
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import logging

from focus_guard.core.activity.blocking.models import (
    BlockingPolicy, BlockingDecision, BlockingEvent, OverrideRequest, BlockingAction
)
from focus_guard.core.activity.blocking.policy_engine import PolicyEngine
from focus_guard.core.activity.blocking.application_blocker import ApplicationBlocker
from focus_guard.core.activity.blocking.notification_manager import NotificationManager, NotificationConfig
from focus_guard.core.activity.models import WindowInfo

logger = logging.getLogger(__name__)


class BlockingSystem:
    """
    Integrated blocking system that manages application blocking policies and enforcement.
    
    This class combines the policy engine, application blocker, and notification manager
    to provide a complete blocking solution with user interaction capabilities.
    """
    
    def __init__(self, notification_config: Optional[NotificationConfig] = None):
        """
        Initialize the blocking system.
        
        Args:
            notification_config: Configuration for notifications
        """
        # Core components
        self.policy_engine = PolicyEngine()
        self.application_blocker = ApplicationBlocker(self.policy_engine)
        self.notification_manager = NotificationManager(notification_config)
        
        # State
        self._active = False
        self._lock = threading.Lock()
        
        # Notification deduplication
        self._recent_notifications = {}  # app_name -> last_notification_time
        self._notification_cooldown = 2.0  # seconds between notifications for same app
        
        # Statistics
        self.system_start_time: Optional[datetime] = None
        self.total_evaluations = 0
        self.total_blocks = 0
        self.total_warnings = 0
        self.total_overrides = 0
        
        # Setup component integration
        self._setup_integration()
    
    def _setup_integration(self):
        """Setup integration between components."""
        # Connect application blocker events to notification manager
        self.application_blocker.add_block_callback(self._on_blocking_event)
        self.application_blocker.add_warning_callback(self._on_blocking_event)
        
        # Connect notification manager override requests to policy engine
        self.notification_manager.add_override_request_callback(self._handle_override_request)
    
    def _on_blocking_event(self, event: BlockingEvent):
        """Handle blocking events from the application blocker."""
        # Check for duplicate notifications
        current_time = time.time()
        notification_key = f"{event.app_name}_{event.event_type}"
        
        with self._lock:
            last_notification = self._recent_notifications.get(notification_key, 0)
            if current_time - last_notification < self._notification_cooldown:
                # Skip duplicate notification
                return
            
            # Record this notification
            self._recent_notifications[notification_key] = current_time
            
            # Update statistics
            if event.event_type == "blocked":
                self.total_blocks += 1
            elif event.event_type == "warned":
                self.total_warnings += 1
        
        # Show notification (outside lock to avoid blocking)
        self.notification_manager.show_blocking_notification(event)
        
        logger.info(f"Blocking event: {event.event_type} for {event.app_name}")
    
    def _cleanup_old_notifications(self):
        """Clean up old notification records to prevent memory leaks."""
        current_time = time.time()
        cutoff_time = current_time - (self._notification_cooldown * 10)  # Keep 10x cooldown period
        
        with self._lock:
            keys_to_remove = [
                key for key, timestamp in self._recent_notifications.items()
                if timestamp < cutoff_time
            ]
            for key in keys_to_remove:
                del self._recent_notifications[key]
    
    def _handle_override_request(self, override_request: OverrideRequest) -> bool:
        """
        Handle override requests from the notification manager.
        
        Args:
            override_request: The override request to process
            
        Returns:
            bool: True if override was granted
        """
        success = self.policy_engine.request_override(override_request)
        
        if success:
            with self._lock:
                self.total_overrides += 1
            
            # Create override event
            event = BlockingEvent(
                event_type="overridden",
                app_name=override_request.app_name,
                domain=override_request.domain,
                policy_name=override_request.policy_name,
                reason="Override granted",
                override_reason=override_request.reason,
                override_duration_minutes=override_request.duration_minutes
            )
            
            # Check for duplicate notifications before showing
            current_time = time.time()
            notification_key = f"{event.app_name}_{event.event_type}"
            
            with self._lock:
                last_notification = self._recent_notifications.get(notification_key, 0)
                if current_time - last_notification >= self._notification_cooldown:
                    # Record this notification
                    self._recent_notifications[notification_key] = current_time
                    # Show notification (outside lock to avoid blocking)
                    self.notification_manager.show_blocking_notification(event)
                    logger.info(f"Override granted for {override_request.app_name}")
                else:
                    logger.debug(f"Skipped duplicate override notification for {override_request.app_name}")
        
        return success
    
    def start(self):
        """Start the blocking system."""
        if self._active:
            logger.warning("Blocking system is already active")
            return
        
        with self._lock:
            self._active = True
            self.system_start_time = datetime.now()
        
        # Start components
        self.application_blocker.start_monitoring()
        
        logger.info("Blocking system started")
    
    def stop(self):
        """Stop the blocking system."""
        if not self._active:
            return
        
        with self._lock:
            self._active = False
            # Clear notification deduplication cache
            self._recent_notifications.clear()
        
        # Stop components
        self.application_blocker.stop_monitoring()
        self.notification_manager.clear_notifications()
        
        logger.info("Blocking system stopped")
    
    def evaluate_application(self, window_info: WindowInfo) -> BlockingDecision:
        """
        Evaluate an application and apply blocking if necessary.
        
        Args:
            window_info: Information about the application window
            
        Returns:
            BlockingDecision: The decision made by the policy engine
        """
        with self._lock:
            self.total_evaluations += 1
        
        # Get decision from application blocker (which uses policy engine)
        decision = self.application_blocker.evaluate_and_block(window_info)
        
        # Handle override dialog for blocking decisions
        if decision.should_block() and decision.override_allowed:
            override_request = self.notification_manager.show_override_dialog(decision)
            if override_request:
                if self._handle_override_request(override_request):
                    # Override granted, return allow decision
                    return BlockingDecision(
                        policy_name="override",
                        action=decision.action.__class__.ALLOW,
                        reason="Override granted",
                        app_name=decision.app_name,
                        domain=decision.domain,
                        window_title=decision.window_title
                    )
        
        return decision
    
    def add_policy(self, policy: BlockingPolicy):
        """Add a blocking policy."""
        self.policy_engine.add_policy(policy)
        logger.info(f"Added policy: {policy.name}")
    
    def remove_policy(self, policy_name: str) -> bool:
        """Remove a blocking policy."""
        success = self.policy_engine.remove_policy(policy_name)
        if success:
            logger.info(f"Removed policy: {policy_name}")
        return success
    
    def get_policy(self, policy_name: str) -> Optional[BlockingPolicy]:
        """Get a policy by name."""
        return self.policy_engine.get_policy(policy_name)
    
    def update_policy(self, policy_name: str, updated_policy: BlockingPolicy) -> bool:
        """Update an existing policy."""
        success = self.policy_engine.update_policy(policy_name, updated_policy)
        if success:
            logger.info(f"Updated policy: {policy_name}")
        return success
    
    def list_policies(self) -> List[BlockingPolicy]:
        """Get all policies."""
        return self.policy_engine.policies.copy()
    
    def request_override(self, app_name: str, domain: Optional[str] = None, 
                        reason: str = "", duration_minutes: int = 15) -> bool:
        """
        Request an override for an application.
        
        Args:
            app_name: Name of the application
            domain: Domain (if applicable)
            reason: Reason for the override
            duration_minutes: Duration of the override
            
        Returns:
            bool: True if override was granted
        """
        override_request = OverrideRequest(
            app_name=app_name,
            domain=domain,
            reason=reason,
            duration_minutes=duration_minutes
        )
        
        return self._handle_override_request(override_request)
    
    def revoke_override(self, app_name: str, domain: Optional[str] = None) -> bool:
        """Revoke an active override."""
        return self.policy_engine.revoke_override(app_name, domain)
    
    def get_active_overrides(self) -> Dict[str, Dict[str, Any]]:
        """Get all active overrides."""
        return self.policy_engine.get_active_overrides()
    
    def force_terminate_application(self, app_name: str) -> bool:
        """Force terminate all instances of an application."""
        return self.application_blocker.force_terminate_process(app_name)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            Dict[str, Any]: System status information
        """
        # Clean up old notification records
        self._cleanup_old_notifications()
        
        with self._lock:
            uptime_seconds = 0
            if self.system_start_time:
                uptime_seconds = (datetime.now() - self.system_start_time).total_seconds()
            
            return {
                'active': self._active,
                'uptime_seconds': uptime_seconds,
                'system_statistics': {
                    'total_evaluations': self.total_evaluations,
                    'total_blocks': self.total_blocks,
                    'total_warnings': self.total_warnings,
                    'total_overrides': self.total_overrides,
                    'evaluations_per_hour': (self.total_evaluations / (uptime_seconds / 3600)) if uptime_seconds > 0 else 0
                },
                'policy_engine': self.policy_engine.get_usage_statistics(),
                'application_blocker': self.application_blocker.get_blocking_statistics(),
                'notification_manager': self.notification_manager.get_statistics(),
                'active_processes': self.application_blocker.get_active_processes(),
                'active_overrides': len(self.get_active_overrides())
            }
    
    def get_recent_events(self, hours: int = 24) -> List[BlockingEvent]:
        """Get recent blocking events."""
        return self.policy_engine.get_recent_events(hours)
    
    def get_notification_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get notification history."""
        return self.notification_manager.get_notification_history(hours)
    
    def export_configuration(self) -> Dict[str, Any]:
        """
        Export the complete blocking system configuration.
        
        Returns:
            Dict[str, Any]: Complete configuration
        """
        return {
            'policies': self.policy_engine.export_policies(),
            'notification_config': {
                'show_warnings': self.notification_manager.config.show_warnings,
                'show_blocks': self.notification_manager.config.show_blocks,
                'show_grace_periods': self.notification_manager.config.show_grace_periods,
                'show_overrides': self.notification_manager.config.show_overrides,
                'notification_timeout': self.notification_manager.config.notification_timeout,
                'sound_enabled': self.notification_manager.config.sound_enabled,
                'max_notifications_per_minute': self.notification_manager.config.max_notifications_per_minute
            },
            'export_timestamp': datetime.now().isoformat(),
            'version': '1.0'
        }
    
    def import_configuration(self, config_data: Dict[str, Any], replace_policies: bool = False):
        """
        Import blocking system configuration.
        
        Args:
            config_data: Configuration data to import
            replace_policies: If True, replace existing policies
        """
        # Import policies
        if 'policies' in config_data:
            self.policy_engine.import_policies(config_data['policies'], replace=replace_policies)
        
        # Import notification config
        if 'notification_config' in config_data:
            nc = config_data['notification_config']
            self.notification_manager.config.show_warnings = nc.get('show_warnings', True)
            self.notification_manager.config.show_blocks = nc.get('show_blocks', True)
            self.notification_manager.config.show_grace_periods = nc.get('show_grace_periods', True)
            self.notification_manager.config.show_overrides = nc.get('show_overrides', True)
            self.notification_manager.config.notification_timeout = nc.get('notification_timeout', 10)
            self.notification_manager.config.sound_enabled = nc.get('sound_enabled', True)
            self.notification_manager.config.max_notifications_per_minute = nc.get('max_notifications_per_minute', 5)
        
        logger.info("Configuration imported successfully")
    
    def create_default_policies(self):
        """Create a set of default blocking policies for common scenarios."""
        # Social media blocking policy
        social_media_policy = BlockingPolicy(
            name="Social Media Block",
            description="Block social media applications and websites during work hours",
            app_patterns=["facebook", "twitter", "instagram", "tiktok", "snapchat"],
            domain_patterns=["facebook.com", "twitter.com", "instagram.com", "tiktok.com", "snapchat.com"],
            action=BlockingAction.BLOCK,
            grace_period_seconds=30,
            warning_message="Social media is blocked during work hours to help you stay focused.",
            override_allowed=True,
            override_duration_minutes=10
        )
        
        # Entertainment blocking policy
        entertainment_policy = BlockingPolicy(
            name="Entertainment Block",
            description="Block entertainment applications and websites",
            app_patterns=["netflix", "youtube", "spotify", "steam", "discord"],
            domain_patterns=["netflix.com", "youtube.com", "spotify.com", "twitch.tv", "discord.com"],
            action=BlockingAction.WARN,
            grace_period_seconds=60,
            warning_message="Entertainment content may impact your productivity.",
            override_allowed=True,
            override_duration_minutes=30
        )
        
        # Gaming blocking policy
        gaming_policy = BlockingPolicy(
            name="Gaming Block",
            description="Block gaming applications",
            app_patterns=["steam", "origin", "uplay", "battlenet", "epicgames", "minecraft"],
            action=BlockingAction.BLOCK,
            grace_period_seconds=15,
            warning_message="Gaming applications are blocked to maintain focus.",
            override_allowed=True,
            override_duration_minutes=60
        )
        
        # Add the policies
        self.add_policy(social_media_policy)
        self.add_policy(entertainment_policy)
        self.add_policy(gaming_policy)
        
        logger.info("Default blocking policies created")
    
    def reset_statistics(self):
        """Reset all system statistics."""
        with self._lock:
            self.total_evaluations = 0
            self.total_blocks = 0
            self.total_warnings = 0
            self.total_overrides = 0
            if self._active:
                self.system_start_time = datetime.now()
        
        self.policy_engine.clear_statistics()
        logger.info("System statistics reset")
    
    def is_active(self) -> bool:
        """Check if the blocking system is active."""
        return self._active
