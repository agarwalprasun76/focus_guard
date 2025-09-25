"""
Standard implementation of the distraction detector.

This module provides the standard implementation of the distraction detector
interface, which coordinates rule evaluation and alert handling.
"""

from typing import Dict, List, Any, Optional, Set, TYPE_CHECKING
from datetime import datetime
import logging

from focus_guard.core.distraction.interfaces import DistractionRule, AlertHandler, DistractionDetector
from focus_guard.core.distraction.types import AlertLevel, DistractionAlert
from focus_guard.core.config.interfaces import ConfigurationManager

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from focus_guard.core.distraction.models import DistractionState

class StandardDistractionDetector(DistractionDetector):
    """
    Standard implementation of the distraction detector.
    
    This implementation uses a rule-based approach to detect distractions
    and delegates alert handling to registered handlers.
    """
    
    def __init__(
        self,
        config_manager: ConfigurationManager,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the distraction detector.
        
        Args:
            config_manager: The configuration manager.
            logger: Optional logger for logging.
        """
        self._config_manager = config_manager
        self._logger = logger or logging.getLogger(__name__)
        self._rules: List[DistractionRule] = []
        self._alert_handlers: List[AlertHandler] = []
        
        # Import here to avoid circular imports
        from focus_guard.core.distraction.models import DistractionState
        self._state = DistractionState()
        
        # Register for configuration changes
        # Register config change callback if supported
        if hasattr(self._config_manager, 'register_change_callback'):
            self._config_manager.register_change_callback(
                "distraction",
                self._on_config_changed
            )
        
        # Load initial configuration
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration settings."""
        # Handle different config manager interfaces
        if hasattr(self._config_manager, 'get_value'):
            config = self._config_manager.get_value("distraction", {})
        else:
            config = self._config_manager.get("distraction", {})
        
        # Load distraction thresholds
        self._distraction_thresholds = config.get("thresholds", {})
        
        # Load productive and distracting categories
        self._productive_categories = config.get("productive_categories", [
            "work", "education", "productivity", "development", "email"
        ])
        self._distracting_categories = config.get("distracting_categories", [
            "social", "entertainment", "shopping"
        ])
        
        # Load domain whitelist
        self._domain_whitelist = set(config.get("domain_whitelist", []))
    
    def _on_config_changed(self) -> None:
        """Handle configuration changes."""
        self._logger.info("Configuration changed, reloading settings")
        self._load_configuration()
    
    def add_rule(self, rule: DistractionRule) -> None:
        """
        Add a distraction rule.
        
        Args:
            rule: The rule to add.
        """
        self._rules.append(rule)
    
    def add_alert_handler(self, handler: AlertHandler) -> None:
        """
        Add an alert handler.
        
        Args:
            handler: The handler to add.
        """
        self._alert_handlers.append(handler)
    
    def update(self, active_window: Dict[str, Any], top_windows: List[Dict[str, Any]]) -> None:
        """
        Update the distraction detector with the current window state.
        
        Args:
            active_window: Information about the active window.
            top_windows: List of top windows.
        """
        # Update state
        self._state.update(active_window, top_windows)
        
        # Check for distractions
        alerts = self._check_for_distractions()
        
        # Handle alerts
        for alert in alerts:
            self._handle_alert(alert)
    
    def _check_for_distractions(self):
        """
        Check for distractions using all rules.
        
        Returns:
            A list of distraction alerts.
        """
        alerts = []
        
        # Apply each rule that should be applied
        for rule in self._rules:
            if rule.should_apply(self._state):
                try:
                    rule_alerts = rule.check(self._state)
                    alerts.extend(rule_alerts)
                except Exception as e:
                    self._logger.error(f"Error in rule {rule.name}: {e}")
        
        return alerts
    
    def _handle_alert(self, alert) -> None:
        """
        Handle a distraction alert.
        
        Args:
            alert: The distraction alert to handle.
        """
        # Log the alert
        self._logger.info(f"Distraction detected: {alert.message}")
        
        # Add to state history
        self._state.add_distraction_alert(alert)
        
        # Call all alert handlers that can handle this alert
        for handler in self._alert_handlers:
            if handler.can_handle(alert):
                try:
                    handler.handle(alert)
                except Exception as e:
                    self._logger.error(f"Error in alert handler {handler.name}: {e}")
    
    @property
    def is_distracted(self) -> bool:
        """
        Check if the user is currently distracted.
        
        Returns:
            True if the user is distracted, False otherwise.
        """
        return self._state.is_distracted
    
    def get_distraction_state(self):
        """
        Get the current distraction state.
        
        Returns:
            The current distraction state.
        """
        return self._state
