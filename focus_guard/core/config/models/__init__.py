"""
Configuration models.

This package contains model classes for representing configuration values
and sections in a structured way.
"""

from .config_section import ConfigurationSection, DataclassConfigSection, create_section_from_dataclass
from .config_value import ConfigurationValue
from .domain_model import (
    Category,
    DomainSettings,
    FocusRules,
    UserPreferences,
    DomainConfigSection,
    FocusGuardConfig
)

__all__ = [
    'ConfigurationSection',
    'ConfigurationValue',
    'DataclassConfigSection',
    'create_section_from_dataclass',
    'Category',
    'DomainSettings',
    'FocusRules',
    'UserPreferences',
    'DomainConfigSection',
    'FocusGuardConfig'
]
