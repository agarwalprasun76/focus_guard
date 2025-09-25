"""
Domain-specific configuration models.

This module provides configuration models specific to the Focus Guard domain,
including domain categories, site settings, and focus rules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import IntEnum

from core_v2.config.models.config_value import (
    ConfigurationValue, StringConfigValue, IntegerConfigValue,
    BooleanConfigValue, ListConfigValue, DictConfigValue
)
from core_v2.config.models.config_section import (
    ConfigurationSection, DataclassConfigSection, create_section_from_dataclass
)


class Category(IntEnum):
    """Domain categories for classification."""
    UNKNOWN = 0
    SOCIAL_MEDIA = 1
    ENTERTAINMENT = 2
    PRODUCTIVITY = 3
    EDUCATION = 4
    NEWS = 5
    SHOPPING = 6
    FINANCE = 7
    HEALTH = 8
    TECHNOLOGY = 9
    GAMING = 10


# Category mapping for user-friendly strings to enum values
CATEGORY_TO_ENUM_MAPPING = {
    "unknown": Category.UNKNOWN,
    "social": Category.SOCIAL_MEDIA,
    "entertainment": Category.ENTERTAINMENT,
    "productivity": Category.PRODUCTIVITY,
    "education": Category.EDUCATION,
    "news": Category.NEWS,
    "shopping": Category.SHOPPING,
    "finance": Category.FINANCE,
    "health": Category.HEALTH,
    "technology": Category.TECHNOLOGY,
    "gaming": Category.GAMING
}

# Reverse mapping for enum values to user-friendly strings
ENUM_TO_CATEGORY_MAPPING = {v: k for k, v in CATEGORY_TO_ENUM_MAPPING.items()}


@dataclass
class DomainSettings:
    """Settings for a specific domain."""
    category: Category = Category.UNKNOWN
    enabled: bool = True
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None


@dataclass
class FocusRules:
    """Rules for focus sessions."""
    duration_minutes: int = 25
    break_minutes: int = 5
    long_break_minutes: int = 15
    long_break_interval: int = 4
    auto_start_breaks: bool = True
    auto_start_focus: bool = False
    notification_sound: str = "default"
    notification_volume: int = 70


@dataclass
class UserPreferences:
    """User preferences for the application."""
    theme: str = "system"
    start_on_boot: bool = False
    minimize_to_tray: bool = True
    show_notifications: bool = True
    telemetry_enabled: bool = True
    update_check_frequency_days: int = 7


class DomainConfigSection(ConfigurationSection):
    """Configuration section for domain settings."""
    
    def __init__(self, name: str = "domains", description: str = "Domain-specific settings"):
        """
        Initialize the domain configuration section.
        
        Args:
            name: The name of the section.
            description: The description of the section.
        """
        super().__init__(name, description)
        self._domains: Dict[str, DomainSettings] = {}
        
    def add_domain(self, domain: str, settings: DomainSettings) -> None:
        """
        Add or update a domain.
        
        Args:
            domain: The domain name.
            settings: The domain settings.
        """
        domain_section = create_section_from_dataclass(settings)
        self.add_section(domain, domain_section)
        self._domains[domain] = settings
        
    def get_domain(self, domain: str) -> Optional[DomainSettings]:
        """
        Get settings for a domain.
        
        Args:
            domain: The domain name.
            
        Returns:
            The domain settings, or None if not found.
        """
        return self._domains.get(domain)
    
    def get_all_domains(self) -> Dict[str, DomainSettings]:
        """
        Get all domain settings.
        
        Returns:
            A dictionary of domain settings.
        """
        return self._domains.copy()
    
    def remove_domain(self, domain: str) -> bool:
        """
        Remove a domain.
        
        Args:
            domain: The domain name.
            
        Returns:
            True if the domain was removed, False otherwise.
        """
        if domain in self._domains:
            self.remove_section(domain)
            del self._domains[domain]
            return True
        return False
    
    def transform_category_values(self) -> None:
        """
        Transform category values from strings to enum values.
        
        This method is used during migration from legacy configuration
        to ensure that category values are properly typed.
        """
        for domain, settings in self._domains.items():
            if isinstance(settings.category, str) and settings.category in CATEGORY_TO_ENUM_MAPPING:
                settings.category = CATEGORY_TO_ENUM_MAPPING[settings.category]


class FocusGuardConfig:
    """Main configuration for Focus Guard application."""
    
    def __init__(self):
        """Initialize the Focus Guard configuration."""
        self.domains = DomainConfigSection()
        self.focus_rules = create_section_from_dataclass(FocusRules())
        self.user_preferences = create_section_from_dataclass(UserPreferences())
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.
        
        Returns:
            A dictionary representation of the configuration.
        """
        return {
            "domains": {
                domain: {
                    "category": ENUM_TO_CATEGORY_MAPPING.get(settings.category, "unknown"),
                    "enabled": settings.enabled,
                    "custom_rules": settings.custom_rules,
                    "notes": settings.notes
                }
                for domain, settings in self.domains.get_all_domains().items()
            },
            "focus_rules": {
                "duration_minutes": self.focus_rules.get_value("duration_minutes"),
                "break_minutes": self.focus_rules.get_value("break_minutes"),
                "long_break_minutes": self.focus_rules.get_value("long_break_minutes"),
                "long_break_interval": self.focus_rules.get_value("long_break_interval"),
                "auto_start_breaks": self.focus_rules.get_value("auto_start_breaks"),
                "auto_start_focus": self.focus_rules.get_value("auto_start_focus"),
                "notification_sound": self.focus_rules.get_value("notification_sound"),
                "notification_volume": self.focus_rules.get_value("notification_volume")
            },
            "user_preferences": {
                "theme": self.user_preferences.get_value("theme"),
                "start_on_boot": self.user_preferences.get_value("start_on_boot"),
                "minimize_to_tray": self.user_preferences.get_value("minimize_to_tray"),
                "show_notifications": self.user_preferences.get_value("show_notifications"),
                "telemetry_enabled": self.user_preferences.get_value("telemetry_enabled"),
                "update_check_frequency_days": self.user_preferences.get_value("update_check_frequency_days")
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FocusGuardConfig':
        """
        Create a configuration from a dictionary.
        
        Args:
            data: The dictionary to create from.
            
        Returns:
            A FocusGuardConfig instance.
        """
        config = cls()
        
        # Load domains
        if "domains" in data and isinstance(data["domains"], dict):
            for domain, domain_data in data["domains"].items():
                if isinstance(domain_data, dict):
                    # Transform category from string to enum if needed
                    category = domain_data.get("category", "unknown")
                    if isinstance(category, str) and category in CATEGORY_TO_ENUM_MAPPING:
                        category = CATEGORY_TO_ENUM_MAPPING[category]
                    
                    settings = DomainSettings(
                        category=category,
                        enabled=domain_data.get("enabled", True),
                        custom_rules=domain_data.get("custom_rules", {}),
                        notes=domain_data.get("notes")
                    )
                    config.domains.add_domain(domain, settings)
        
        # Load focus rules
        if "focus_rules" in data and isinstance(data["focus_rules"], dict):
            for key, value in data["focus_rules"].items():
                if config.focus_rules.has_value(key):
                    config.focus_rules.set_value(key, value)
        
        # Load user preferences
        if "user_preferences" in data and isinstance(data["user_preferences"], dict):
            for key, value in data["user_preferences"].items():
                if config.user_preferences.has_value(key):
                    config.user_preferences.set_value(key, value)
        
        return config
