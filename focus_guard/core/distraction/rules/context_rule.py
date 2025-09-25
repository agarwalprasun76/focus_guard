"""
Context switch distraction rule implementation.

This module provides a rule for detecting distractions based on frequent
context switching between applications, which can indicate distracted behavior.
"""

from typing import Dict, Any, List, Optional, Deque
from datetime import datetime, timedelta
from collections import deque

from focus_guard.core.distraction.rules.base import BaseDistractionRule
from focus_guard.core.distraction.models import DistractionAlert, DistractionState, AlertLevel


class ContextSwitchRule(BaseDistractionRule):
    """
    Rule for detecting distractions based on frequent context switching.
    
    This rule tracks application switches and triggers an alert if
    the user switches contexts too frequently within a time window.
    """
    
    def __init__(
        self,
        switch_threshold: int = 5,
        time_window_seconds: int = 60,
        rule_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the context switch rule.
        
        Args:
            switch_threshold: Number of context switches before triggering an alert.
            time_window_seconds: Time window in seconds for counting context switches.
            rule_config: Optional configuration for the rule.
        """
        super().__init__(rule_config)
        if rule_config is not None:
            self._switch_threshold = rule_config.get("switch_threshold", switch_threshold)
            self._time_window_seconds = rule_config.get("time_window_seconds", time_window_seconds)
        else:
            self._switch_threshold = switch_threshold
            self._time_window_seconds = time_window_seconds
        self._context_switches: Deque[Dict[str, Any]] = deque(maxlen=100)  # Store recent switches
        self._last_app: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Get the name of the rule."""
        return "Context Switch Rule"
    
    @property
    def description(self) -> str:
        """Get the description of the rule."""
        return "Detects distractions based on frequent context switching between applications."
    
    def should_apply(self, state: DistractionState) -> bool:
        """
        Determine if the rule should be applied to the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            True if the rule should be applied, False otherwise.
        """
        # Always apply this rule if we have an active window
        return state.active_window is not None
    
    def check(self, state: DistractionState) -> List[DistractionAlert]:
        """
        Check for distractions based on the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            A list of distraction alerts, or an empty list if no distractions are detected.
        """
        alerts = []
        active_window = state.active_window
        
        if not active_window:
            return alerts
        
        current_app = active_window.get("app_name")
        if not current_app:
            return alerts
        
        # Check if this is a context switch
        if self._last_app is not None and current_app != self._last_app:
            # Record the context switch
            self._context_switches.append({
                "from": self._last_app,
                "to": current_app,
                "timestamp": datetime.now()
            })
            
            # Check if we've exceeded the threshold
            if self._is_excessive_switching():
                alert = self.create_alert(
                    message=f"Excessive context switching detected ({len(self._recent_switches())} switches in {self._time_window_seconds} seconds)",
                    level=AlertLevel.WARNING,
                    metadata={
                        "switch_count": len(self._recent_switches()),
                        "time_window": self._time_window_seconds,
                        "threshold": self._switch_threshold,
                        "recent_switches": [
                            f"{switch['from']} -> {switch['to']}"
                            for switch in list(self._recent_switches())[-5:]
                        ]
                    }
                )
                alerts.append(alert)
        
        # Update last app
        self._last_app = current_app
        
        return alerts
    
    def _recent_switches(self) -> List[Dict[str, Any]]:
        """
        Get recent context switches within the time window.
        
        Returns:
            List of recent context switches.
        """
        cutoff_time = datetime.now() - timedelta(seconds=self._time_window_seconds)
        return [
            switch for switch in self._context_switches
            if switch["timestamp"] >= cutoff_time
        ]
    
    def _is_excessive_switching(self) -> bool:
        """
        Check if the user is switching contexts excessively.
        
        Returns:
            True if the user is switching contexts excessively, False otherwise.
        """
        recent_switches = self._recent_switches()
        return len(recent_switches) >= self._switch_threshold
