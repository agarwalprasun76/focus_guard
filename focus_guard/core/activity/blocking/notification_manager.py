"""
Notification manager for blocking events and warnings.

This module provides the NotificationManager class that handles user notifications
for blocking events, warnings, and override requests.
"""

import sys
import threading
import time
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from focus_guard.core.activity.blocking.models import BlockingEvent, BlockingDecision, OverrideRequest

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for notification behavior."""
    show_warnings: bool = True
    show_blocks: bool = True
    show_grace_periods: bool = True
    show_overrides: bool = True
    notification_timeout: int = 10  # seconds
    sound_enabled: bool = True
    persistent_notifications: bool = False
    max_notifications_per_minute: int = 5


class NotificationManager:
    """
    Manager for blocking-related notifications and user interactions.
    
    This class handles displaying notifications to users about blocking events,
    warnings, grace periods, and override requests.
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        """
        Initialize the notification manager.
        
        Args:
            config: Configuration for notification behavior
        """
        self.config = config or NotificationConfig()
        
        # Notification tracking
        self.active_notifications: Dict[str, Dict[str, Any]] = {}
        self.notification_history: List[Dict[str, Any]] = []
        self.rate_limit_tracker: List[datetime] = []
        
        # Deduplication tracking
        self._recent_notifications: Dict[str, float] = {}  # notification_key -> timestamp
        self._dedup_cooldown = 1.0  # seconds between same notifications
        
        # Callbacks
        self.override_request_callbacks: List[Callable[[OverrideRequest], bool]] = []
        
        # Threading
        self._lock = threading.Lock()
        
        # Platform-specific notification system
        self._notification_system = self._get_notification_system()
    
    def _get_notification_system(self):
        """Get the appropriate notification system for the current platform."""
        if sys.platform == "win32":
            return WindowsNotificationSystem()
        elif sys.platform == "darwin":
            return MacOSNotificationSystem()
        else:
            return LinuxNotificationSystem()
    
    def show_blocking_notification(self, event: BlockingEvent) -> bool:
        """
        Show a notification for a blocking event.
        
        Args:
            event: The blocking event to notify about
            
        Returns:
            bool: True if notification was shown successfully
        """
        if not self._should_show_notification(event.event_type):
            return False
        
        if not self._check_rate_limit():
            logger.warning("Notification rate limit exceeded, skipping notification")
            return False
        
        # Check for duplicate notifications
        dedup_key = f"{event.event_type}_{event.app_name}"
        current_time = time.time()
        
        with self._lock:
            last_notification = self._recent_notifications.get(dedup_key, 0)
            if current_time - last_notification < self._dedup_cooldown:
                logger.debug(f"Skipped duplicate notification: {dedup_key}")
                return False
            
            # Record this notification
            self._recent_notifications[dedup_key] = current_time
        
        notification_id = f"{event.event_type}_{event.app_name}_{int(time.time() * 1000000)}"
        
        # Create notification content based on event type
        if event.event_type == "blocked":
            title = "Application Blocked"
            message = f"{event.app_name} has been blocked by Focus Guard"
            if event.policy_name:
                message += f" (Policy: {event.policy_name})"
            icon = "block"
            
        elif event.event_type == "warned":
            title = "Application Warning"
            message = f"Warning: {event.app_name} is restricted"
            if event.reason:
                message += f"\nReason: {event.reason}"
            icon = "warning"
            
        elif event.event_type == "grace_period":
            title = "Grace Period Active"
            message = f"{event.app_name} will be blocked soon"
            if event.reason and "remaining" in event.reason:
                message += f"\n{event.reason}"
            icon = "timer"
            
        elif event.event_type == "overridden":
            title = "Override Granted"
            message = f"Temporary access granted for {event.app_name}"
            if event.override_duration_minutes:
                message += f" ({event.override_duration_minutes} minutes)"
            icon = "unlock"
            
        else:
            title = "Focus Guard"
            message = f"{event.app_name}: {event.event_type}"
            icon = "info"
        
        # Show the notification
        success = self._notification_system.show_notification(
            notification_id=notification_id,
            title=title,
            message=message,
            icon=icon,
            timeout=self.config.notification_timeout,
            actions=self._get_notification_actions(event)
        )
        
        if success:
            with self._lock:
                self.active_notifications[notification_id] = {
                    'event': event,
                    'title': title,
                    'message': message,
                    'timestamp': datetime.now()
                }
                
                # Add to history
                self.notification_history.append({
                    'id': notification_id,
                    'event_type': event.event_type,
                    'app_name': event.app_name,
                    'title': title,
                    'message': message,
                    'timestamp': datetime.now()
                })
                
                # Keep history limited
                if len(self.notification_history) > 100:
                    self.notification_history = self.notification_history[-100:]
        
        return success
    
    def show_override_dialog(self, decision: BlockingDecision) -> Optional[OverrideRequest]:
        """
        Show an override request dialog to the user.
        
        Args:
            decision: The blocking decision to potentially override
            
        Returns:
            Optional[OverrideRequest]: Override request if user approved, None otherwise
        """
        if not decision.override_allowed:
            return None
        
        # Show override dialog
        override_data = self._notification_system.show_override_dialog(
            app_name=decision.app_name,
            policy_name=decision.policy_name,
            reason=decision.reason,
            warning_message=decision.warning_message,
            requires_password=bool(decision.override_allowed),
            default_duration=15
        )
        
        if override_data:
            override_request = OverrideRequest(
                app_name=decision.app_name,
                domain=decision.domain,
                policy_name=decision.policy_name,
                reason=override_data.get('reason', ''),
                duration_minutes=override_data.get('duration_minutes', 15),
                password=override_data.get('password')
            )
            
            # Notify callbacks
            for callback in self.override_request_callbacks:
                try:
                    if callback(override_request):
                        return override_request
                except Exception as e:
                    logger.error(f"Error in override request callback: {e}")
            
            return override_request
        
        return None
    
    def _should_show_notification(self, event_type: str) -> bool:
        """Check if notifications should be shown for this event type."""
        if event_type == "blocked" and not self.config.show_blocks:
            return False
        elif event_type == "warned" and not self.config.show_warnings:
            return False
        elif event_type == "grace_period" and not self.config.show_grace_periods:
            return False
        elif event_type == "overridden" and not self.config.show_overrides:
            return False
        
        return True
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within the notification rate limit."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Remove old entries
        self.rate_limit_tracker = [
            timestamp for timestamp in self.rate_limit_tracker
            if timestamp > cutoff
        ]
        
        # Check if we're under the limit
        if len(self.rate_limit_tracker) >= self.config.max_notifications_per_minute:
            return False
        
        # Add current timestamp
        self.rate_limit_tracker.append(now)
        return True
    
    def _get_notification_actions(self, event: BlockingEvent) -> List[Dict[str, str]]:
        """Get available actions for a notification."""
        actions = []
        
        if event.event_type in ["blocked", "warned", "grace_period"]:
            actions.append({"id": "override", "text": "Request Override"})
            actions.append({"id": "dismiss", "text": "Dismiss"})
        elif event.event_type == "overridden":
            actions.append({"id": "revoke", "text": "Revoke Override"})
            actions.append({"id": "dismiss", "text": "OK"})
        
        return actions
    
    def handle_notification_action(self, notification_id: str, action_id: str):
        """
        Handle user action on a notification.
        
        Args:
            notification_id: ID of the notification
            action_id: ID of the action taken
        """
        with self._lock:
            if notification_id in self.active_notifications:
                event = self.active_notifications[notification_id]['event']
                
                if action_id == "override":
                    # This would typically trigger an override dialog
                    logger.info(f"Override requested for {event.app_name}")
                elif action_id == "revoke":
                    logger.info(f"Override revoke requested for {event.app_name}")
                elif action_id == "dismiss":
                    logger.debug(f"Notification dismissed for {event.app_name}")
                
                # Remove from active notifications
                del self.active_notifications[notification_id]
    
    def add_override_request_callback(self, callback: Callable[[OverrideRequest], bool]):
        """Add a callback for override requests."""
        self.override_request_callbacks.append(callback)
    
    def remove_override_request_callback(self, callback: Callable[[OverrideRequest], bool]):
        """Remove an override request callback."""
        if callback in self.override_request_callbacks:
            self.override_request_callbacks.remove(callback)
    
    def get_notification_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get notification history for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List[Dict[str, Any]]: List of notification history entries
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            entry for entry in self.notification_history
            if entry['timestamp'] >= cutoff_time
        ]
    
    def clear_notifications(self):
        """Clear all active notifications."""
        with self._lock:
            for notification_id in list(self.active_notifications.keys()):
                self._notification_system.dismiss_notification(notification_id)
            self.active_notifications.clear()
            # Also clear deduplication cache
            self._recent_notifications.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get notification statistics."""
        with self._lock:
            return {
                'active_notifications': len(self.active_notifications),
                'total_notifications': len(self.notification_history),
                'notifications_last_hour': len(self.get_notification_history(hours=1)),
                'rate_limit_count': len(self.rate_limit_tracker),
                'config': {
                    'show_warnings': self.config.show_warnings,
                    'show_blocks': self.config.show_blocks,
                    'show_grace_periods': self.config.show_grace_periods,
                    'notification_timeout': self.config.notification_timeout,
                    'max_per_minute': self.config.max_notifications_per_minute
                }
            }


class BaseNotificationSystem:
    """Base class for platform-specific notification systems."""
    
    def show_notification(self, notification_id: str, title: str, message: str, 
                         icon: str = "info", timeout: int = 10, 
                         actions: List[Dict[str, str]] = None) -> bool:
        """Show a notification."""
        raise NotImplementedError
    
    def show_override_dialog(self, app_name: str, policy_name: str, reason: str,
                           warning_message: str, requires_password: bool = False,
                           default_duration: int = 15) -> Optional[Dict[str, Any]]:
        """Show an override request dialog."""
        raise NotImplementedError
    
    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss a notification."""
        raise NotImplementedError


class WindowsNotificationSystem(BaseNotificationSystem):
    """Windows-specific notification system using toast notifications."""
    
    def show_notification(self, notification_id: str, title: str, message: str,
                         icon: str = "info", timeout: int = 10,
                         actions: List[Dict[str, str]] = None) -> bool:
        """Show a Windows toast notification."""
        try:
            # Try using win10toast for Windows toast notifications
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    title=title,
                    msg=message,
                    duration=timeout,
                    threaded=True
                )
                return True
            except ImportError:
                pass
            
            # Fallback to simple message box
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)  # MB_ICONINFORMATION
            return True
            
        except Exception as e:
            logger.error(f"Error showing Windows notification: {e}")
            return False
    
    def show_override_dialog(self, app_name: str, policy_name: str, reason: str,
                           warning_message: str, requires_password: bool = False,
                           default_duration: int = 15) -> Optional[Dict[str, Any]]:
        """Show Windows override dialog."""
        try:
            import tkinter as tk
            from tkinter import messagebox, simpledialog
            
            # Simple dialog for now - in a full implementation this would be a custom dialog
            result = messagebox.askyesno(
                "Override Request",
                f"Application: {app_name}\nPolicy: {policy_name}\n\n{warning_message}\n\nRequest override?"
            )
            
            if result:
                duration = simpledialog.askinteger(
                    "Override Duration",
                    "Override duration (minutes):",
                    initialvalue=default_duration,
                    minvalue=1,
                    maxvalue=480
                )
                
                if duration:
                    return {
                        'reason': 'User requested override',
                        'duration_minutes': duration,
                        'password': None
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error showing Windows override dialog: {e}")
            return None
    
    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss a Windows notification."""
        # Toast notifications auto-dismiss, so this is a no-op
        return True


class LinuxNotificationSystem(BaseNotificationSystem):
    """Linux notification system using libnotify."""
    
    def show_notification(self, notification_id: str, title: str, message: str,
                         icon: str = "info", timeout: int = 10,
                         actions: List[Dict[str, str]] = None) -> bool:
        """Show a Linux notification using notify-send."""
        try:
            import subprocess
            
            # Use notify-send command
            cmd = [
                'notify-send',
                '--expire-time', str(timeout * 1000),  # Convert to milliseconds
                '--icon', icon,
                title,
                message
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error showing Linux notification: {e}")
            return False
    
    def show_override_dialog(self, app_name: str, policy_name: str, reason: str,
                           warning_message: str, requires_password: bool = False,
                           default_duration: int = 15) -> Optional[Dict[str, Any]]:
        """Show Linux override dialog using zenity."""
        try:
            import subprocess
            
            # Use zenity for dialog
            result = subprocess.run([
                'zenity', '--question',
                '--title', 'Override Request',
                '--text', f'Application: {app_name}\nPolicy: {policy_name}\n\n{warning_message}\n\nRequest override?'
            ], capture_output=True)
            
            if result.returncode == 0:
                # Get duration
                duration_result = subprocess.run([
                    'zenity', '--entry',
                    '--title', 'Override Duration',
                    '--text', 'Override duration (minutes):',
                    '--entry-text', str(default_duration)
                ], capture_output=True, text=True)
                
                if duration_result.returncode == 0:
                    try:
                        duration = int(duration_result.stdout.strip())
                        return {
                            'reason': 'User requested override',
                            'duration_minutes': duration,
                            'password': None
                        }
                    except ValueError:
                        pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error showing Linux override dialog: {e}")
            return None
    
    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss a Linux notification."""
        # Most Linux notifications auto-dismiss
        return True


class MacOSNotificationSystem(BaseNotificationSystem):
    """macOS notification system using osascript."""
    
    def show_notification(self, notification_id: str, title: str, message: str,
                         icon: str = "info", timeout: int = 10,
                         actions: List[Dict[str, str]] = None) -> bool:
        """Show a macOS notification using osascript."""
        try:
            import subprocess
            
            script = f'''
            display notification "{message}" with title "{title}"
            '''
            
            result = subprocess.run([
                'osascript', '-e', script
            ], capture_output=True, timeout=5)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error showing macOS notification: {e}")
            return False
    
    def show_override_dialog(self, app_name: str, policy_name: str, reason: str,
                           warning_message: str, requires_password: bool = False,
                           default_duration: int = 15) -> Optional[Dict[str, Any]]:
        """Show macOS override dialog using osascript."""
        try:
            import subprocess
            
            script = f'''
            set response to display dialog "Application: {app_name}\\nPolicy: {policy_name}\\n\\n{warning_message}\\n\\nRequest override?" buttons {{"Cancel", "Override"}} default button "Override"
            if button returned of response is "Override" then
                set duration to text returned of (display dialog "Override duration (minutes):" default answer "{default_duration}")
                return duration
            else
                return "cancelled"
            end if
            '''
            
            result = subprocess.run([
                'osascript', '-e', script
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip() != "cancelled":
                try:
                    duration = int(result.stdout.strip())
                    return {
                        'reason': 'User requested override',
                        'duration_minutes': duration,
                        'password': None
                    }
                except ValueError:
                    pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error showing macOS override dialog: {e}")
            return None
    
    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss a macOS notification."""
        # macOS notifications auto-dismiss
        return True
