"""
Base implementation for distraction rules.

This module provides a base implementation for distraction rules
that can be extended for specific rule types.
"""

from abc import abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from core_v2.distraction.interfaces import DistractionRule
from core_v2.distraction.models import DistractionAlert, DistractionState, AlertLevel


class BaseDistractionRule(DistractionRule):
    """
    Base implementation for distraction rules.
    
    This class provides common functionality for all distraction rules,
    including configuration handling and alert creation.
    """
    
    def __init__(self, rule_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the rule.
        
        Args:
            rule_config: Optional configuration for the rule.
        """
        self._config = rule_config or {}
        self._enabled = self._config.get("enabled", True)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the rule."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the description of the rule."""
        pass
    
    @abstractmethod
    def should_apply(self, state: DistractionState) -> bool:
        """
        Determine if the rule should be applied to the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            True if the rule should be applied, False otherwise.
        """
        pass
    
    @abstractmethod
    def check(self, state: DistractionState) -> List[DistractionAlert]:
        """
        Check for distractions based on the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            A list of distraction alerts, or an empty list if no distractions are detected.
        """
        pass
    
    def is_enabled(self) -> bool:
        """
        Check if the rule is enabled.
        
        Returns:
            True if the rule is enabled, False otherwise.
        """
        return self._enabled
    
    def create_alert(
        self,
        message: str,
        level: AlertLevel = AlertLevel.WARNING,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DistractionAlert:
        """
        Create a distraction alert.
        
        Args:
            message: The alert message.
            level: The alert level.
            metadata: Additional metadata about the alert.
            
        Returns:
            A distraction alert.
        """
        return DistractionAlert(
            rule_name=self.name,
            level=level,
            message=message,
            metadata=metadata or {},
            timestamp=datetime.now()
        )
