"""
Domain-specific configuration schemas.

This module provides JSON schemas for validating Focus Guard domain-specific
configuration data.
"""

from typing import Dict, Any

from focus_guard.core.config.schema.schema import JsonConfigSchema
from focus_guard.core.config.models.domain_model import CATEGORY_TO_ENUM_MAPPING


def create_focus_guard_schema() -> JsonConfigSchema:
    """
    Create a JSON schema for Focus Guard configuration.
    
    Returns:
        A JSON schema for validating Focus Guard configuration.
    """
    # Define the domain settings schema
    domain_settings_schema = {
        "type": "object",
        "properties": {
            "category": {
                "oneOf": [
                    {"type": "string", "enum": list(CATEGORY_TO_ENUM_MAPPING.keys())},
                    {"type": "integer", "minimum": 0, "maximum": 10}
                ],
                "default": "unknown"
            },
            "enabled": {"type": "boolean", "default": True},
            "custom_rules": {"type": "object", "default": {}},
            "notes": {"type": ["string", "null"], "default": None}
        },
        "required": ["category", "enabled"],
        "additionalProperties": False
    }
    
    # Define the focus rules schema
    focus_rules_schema = {
        "type": "object",
        "properties": {
            "duration_minutes": {"type": "integer", "minimum": 1, "maximum": 120, "default": 25},
            "break_minutes": {"type": "integer", "minimum": 1, "maximum": 60, "default": 5},
            "long_break_minutes": {"type": "integer", "minimum": 1, "maximum": 120, "default": 15},
            "long_break_interval": {"type": "integer", "minimum": 1, "maximum": 10, "default": 4},
            "auto_start_breaks": {"type": "boolean", "default": True},
            "auto_start_focus": {"type": "boolean", "default": False},
            "notification_sound": {"type": "string", "default": "default"},
            "notification_volume": {"type": "integer", "minimum": 0, "maximum": 100, "default": 70}
        },
        "additionalProperties": False
    }
    
    # Define the user preferences schema
    user_preferences_schema = {
        "type": "object",
        "properties": {
            "theme": {"type": "string", "enum": ["light", "dark", "system"], "default": "system"},
            "start_on_boot": {"type": "boolean", "default": False},
            "minimize_to_tray": {"type": "boolean", "default": True},
            "show_notifications": {"type": "boolean", "default": True},
            "telemetry_enabled": {"type": "boolean", "default": True},
            "update_check_frequency_days": {"type": "integer", "minimum": 0, "maximum": 365, "default": 7}
        },
        "additionalProperties": False
    }
    
    # Define the main schema
    schema = {
        "type": "object",
        "properties": {
            "domains": {
                "type": "object",
                "patternProperties": {
                    "^[a-zA-Z0-9.-]+$": domain_settings_schema
                },
                "additionalProperties": False
            },
            "focus_rules": focus_rules_schema,
            "user_preferences": user_preferences_schema
        },
        "additionalProperties": False
    }
    
    return JsonConfigSchema("focus_guard_config", schema, "Focus Guard Configuration Schema")


def create_domain_settings_schema() -> JsonConfigSchema:
    """
    Create a JSON schema for domain settings.
    
    Returns:
        A JSON schema for validating domain settings.
    """
    schema = {
        "type": "object",
        "patternProperties": {
            "^[a-zA-Z0-9.-]+$": {
                "type": "object",
                "properties": {
                    "category": {
                        "oneOf": [
                            {"type": "string", "enum": list(CATEGORY_TO_ENUM_MAPPING.keys())},
                            {"type": "integer", "minimum": 0, "maximum": 10}
                        ],
                        "default": "unknown"
                    },
                    "enabled": {"type": "boolean", "default": True},
                    "custom_rules": {"type": "object", "default": {}},
                    "notes": {"type": ["string", "null"], "default": None}
                },
                "required": ["category", "enabled"],
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }
    
    return JsonConfigSchema("domain_settings", schema, "Domain Settings Schema")


def create_focus_rules_schema() -> JsonConfigSchema:
    """
    Create a JSON schema for focus rules.
    
    Returns:
        A JSON schema for validating focus rules.
    """
    schema = {
        "type": "object",
        "properties": {
            "duration_minutes": {"type": "integer", "minimum": 1, "maximum": 120, "default": 25},
            "break_minutes": {"type": "integer", "minimum": 1, "maximum": 60, "default": 5},
            "long_break_minutes": {"type": "integer", "minimum": 1, "maximum": 120, "default": 15},
            "long_break_interval": {"type": "integer", "minimum": 1, "maximum": 10, "default": 4},
            "auto_start_breaks": {"type": "boolean", "default": True},
            "auto_start_focus": {"type": "boolean", "default": False},
            "notification_sound": {"type": "string", "default": "default"},
            "notification_volume": {"type": "integer", "minimum": 0, "maximum": 100, "default": 70}
        },
        "additionalProperties": False
    }
    
    return JsonConfigSchema("focus_rules", schema, "Focus Rules Schema")


def create_user_preferences_schema() -> JsonConfigSchema:
    """
    Create a JSON schema for user preferences.
    
    Returns:
        A JSON schema for validating user preferences.
    """
    schema = {
        "type": "object",
        "properties": {
            "theme": {"type": "string", "enum": ["light", "dark", "system"], "default": "system"},
            "start_on_boot": {"type": "boolean", "default": False},
            "minimize_to_tray": {"type": "boolean", "default": True},
            "show_notifications": {"type": "boolean", "default": True},
            "telemetry_enabled": {"type": "boolean", "default": True},
            "update_check_frequency_days": {"type": "integer", "minimum": 0, "maximum": 365, "default": 7}
        },
        "additionalProperties": False
    }
    
    return JsonConfigSchema("user_preferences", schema, "User Preferences Schema")
