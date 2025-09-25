"""
Area increase distraction rule implementation.

This module provides a rule for detecting distractions based on
sudden increases in window area, which can indicate distracted behavior
such as maximizing video players or games.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from core_v2.distraction.rules.base import BaseDistractionRule
from core_v2.distraction.models import DistractionAlert, DistractionState, AlertLevel


class AreaIncreaseRule(BaseDistractionRule):
    """
    Rule for detecting distractions based on window area increases.
    
    This rule tracks window area changes and triggers an alert if
    the window area increases significantly, which can indicate
    distracted behavior such as maximizing video players or games.
    """
    
    def __init__(
        self,
        area_threshold: float = 50.0,  # 50% increase
        min_area: int = 100000,  # Minimum area in pixels
        rule_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the area increase rule.
        
        Args:
            area_threshold: Percentage increase in window area that triggers an alert.
            min_area: Minimum area in pixels before the rule applies.
            rule_config: Optional configuration for the rule.
        """
        super().__init__(rule_config)
        if rule_config is not None:
            self._area_threshold = rule_config.get("area_threshold", area_threshold)
            self._min_area = rule_config.get("min_area", min_area)
        else:
            self._area_threshold = area_threshold
            self._min_area = min_area
        self._last_window_area: Optional[int] = None
    
    @property
    def name(self) -> str:
        """Get the name of the rule."""
        return "Area Increase Rule"
    
    @property
    def description(self) -> str:
        """Get the description of the rule."""
        return "Detects distractions based on sudden increases in window area."
    
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
        
        # Calculate window area
        width = active_window.get("width", 0)
        height = active_window.get("height", 0)
        current_area = width * height
        
        # Skip if area is too small
        if current_area < self._min_area:
            self._last_window_area = current_area
            return alerts
        
        # Check if this is the first area calculation
        if self._last_window_area is None:
            self._last_window_area = current_area
            return alerts
        
        # Check if area has increased significantly
        if self._last_window_area > 0:
            area_increase_percent = ((current_area - self._last_window_area) / self._last_window_area) * 100
            
            if area_increase_percent >= self._area_threshold:
                alert = self.create_alert(
                    message=f"Window area increased by {area_increase_percent:.1f}% (from {self._last_window_area} to {current_area})",
                    level=AlertLevel.INFO,
                    metadata={
                        "previous_area": self._last_window_area,
                        "current_area": current_area,
                        "increase_percent": area_increase_percent,
                        "threshold": self._area_threshold,
                        "window_title": active_window.get("title", ""),
                        "app_name": active_window.get("app_name", "")
                    }
                )
                alerts.append(alert)
        
        # Update last area
        self._last_window_area = current_area
        
        return alerts
