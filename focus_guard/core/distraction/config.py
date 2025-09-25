"""
Configuration schemas for the distraction detection module.

This module defines the configuration schemas used by the distraction detector,
including rule configurations, thresholds, and general settings.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from focus_guard.core.config.models import ConfigurationSection


@dataclass
class DistractionRuleConfig(ConfigurationSection):
    """
    Configuration for a distraction rule.
    
    Attributes:
        enabled: Whether the rule is enabled.
        parameters: Rule-specific parameters.
    """
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class URLRuleConfig(DistractionRuleConfig):
    """
    Configuration for the URL rule.
    
    Attributes:
        distracting_categories: List of categories considered distracting.
        domain_whitelist: List of domains to whitelist.
    """
    distracting_categories: List[str] = field(default_factory=lambda: [
        "social", "entertainment", "shopping"
    ])
    domain_whitelist: List[str] = field(default_factory=list)


@dataclass
class ContextSwitchRuleConfig(DistractionRuleConfig):
    """
    Configuration for the context switch rule.
    
    Attributes:
        switch_threshold: Number of context switches before triggering an alert.
        time_window_seconds: Time window in seconds for counting context switches.
    """
    switch_threshold: int = 5
    time_window_seconds: int = 60


@dataclass
class AreaIncreaseRuleConfig(DistractionRuleConfig):
    """
    Configuration for the area increase rule.
    
    Attributes:
        area_threshold: Percentage increase in window area that triggers an alert.
        min_area: Minimum area in pixels before the rule applies.
    """
    area_threshold: float = 50.0  # 50% increase
    min_area: int = 100000  # Minimum area in pixels


@dataclass
class DistractionThresholds(ConfigurationSection):
    """
    Configuration for distraction thresholds.
    
    Attributes:
        time_threshold: Time threshold in seconds.
        count_threshold: Count threshold.
    """
    time_threshold: int = 60
    count_threshold: int = 3


@dataclass
class AlertHandlerConfig(ConfigurationSection):
    """
    Configuration for an alert handler.
    
    Attributes:
        enabled: Whether the handler is enabled.
        parameters: Handler-specific parameters.
    """
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationHandlerConfig(AlertHandlerConfig):
    """
    Configuration for the notification alert handler.
    
    Attributes:
        min_level: Minimum alert level to trigger a notification.
        cooldown_seconds: Cooldown period between notifications.
    """
    min_level: str = "WARNING"
    cooldown_seconds: int = 60


@dataclass
class BlockingHandlerConfig(AlertHandlerConfig):
    """
    Configuration for the blocking alert handler.
    
    Attributes:
        min_level: Minimum alert level to trigger blocking.
        block_duration_seconds: Duration of blocking in seconds.
    """
    min_level: str = "CRITICAL"
    block_duration_seconds: int = 300


@dataclass
class DistractionConfig(ConfigurationSection):
    """
    Configuration for the distraction detector.
    
    Attributes:
        enabled: Whether distraction detection is enabled.
        thresholds: Distraction thresholds.
        rules: Rule configurations.
        handlers: Handler configurations.
        productive_categories: List of categories considered productive.
        distracting_categories: List of categories considered distracting.
        domain_whitelist: List of domains to whitelist.
    """
    enabled: bool = True
    thresholds: DistractionThresholds = field(default_factory=DistractionThresholds)
    rules: Dict[str, DistractionRuleConfig] = field(default_factory=dict)
    handlers: Dict[str, AlertHandlerConfig] = field(default_factory=dict)
    productive_categories: List[str] = field(default_factory=lambda: [
        "work", "education", "productivity", "development", "email"
    ])
    distracting_categories: List[str] = field(default_factory=lambda: [
        "social", "entertainment", "shopping"
    ])
    domain_whitelist: List[str] = field(default_factory=list)


def get_default_config() -> DistractionConfig:
    """
    Get the default distraction configuration.
    
    Returns:
        The default distraction configuration.
    """
    config = DistractionConfig()
    
    # Add default rule configurations
    config.rules["url_rule"] = URLRuleConfig()
    config.rules["context_switch_rule"] = ContextSwitchRuleConfig()
    config.rules["area_increase_rule"] = AreaIncreaseRuleConfig()
    
    # Add default handler configurations
    config.handlers["notification"] = NotificationHandlerConfig()
    config.handlers["blocking"] = BlockingHandlerConfig()
    
    return config
