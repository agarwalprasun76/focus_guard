"""
Domain-specific configuration migration.

This module provides migration steps and utilities for Focus Guard
configuration data between different schema versions.
"""

from typing import Dict, Any, Optional
import logging

from focus_guard.core.config.migration.migrator import (
    ConfigMigrator, MigrationStep, 
    rename_field, move_field, transform_field, add_field, remove_field
)
from focus_guard.core.config.models.domain_model import CATEGORY_TO_ENUM_MAPPING


# Set up logging
logger = logging.getLogger(__name__)


# Current schema version
CURRENT_SCHEMA_VERSION = "2.0.0"


def create_focus_guard_migrator() -> ConfigMigrator:
    """
    Create a migrator for Focus Guard configuration.
    
    Returns:
        A configured ConfigMigrator instance.
    """
    migrator = ConfigMigrator(CURRENT_SCHEMA_VERSION)
    
    # Register migration steps
    
    # Migration from 1.0.0 to 1.1.0
    migrator.register_migration_step(MigrationStep(
        source_version="1.0.0",
        target_version="1.1.0",
        description="Rename 'app' section to 'application'",
        transform_func=rename_field("app", "application")
    ))
    
    # Migration from 1.1.0 to 1.2.0
    migrator.register_migration_step(MigrationStep(
        source_version="1.1.0",
        target_version="1.2.0",
        description="Move user preferences to dedicated section",
        transform_func=move_field("settings.preferences", "user_preferences")
    ))
    
    # Migration from 1.2.0 to 1.3.0
    migrator.register_migration_step(MigrationStep(
        source_version="1.2.0",
        target_version="1.3.0",
        description="Transform domain categories to enum values",
        transform_func=transform_domain_categories
    ))
    
    # Migration from 1.3.0 to 2.0.0
    migrator.register_migration_step(MigrationStep(
        source_version="1.3.0",
        target_version="2.0.0",
        description="Restructure focus settings to focus_rules",
        transform_func=restructure_focus_settings
    ))
    
    return migrator


def transform_domain_categories(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform domain categories from strings to enum values.
    
    Args:
        config_data: The configuration data to transform.
        
    Returns:
        The transformed configuration data.
    """
    # Create a copy to avoid modifying the original
    result = config_data.copy()
    
    # Check if domains section exists
    if "domains" in result and isinstance(result["domains"], dict):
        domains = result["domains"]
        
        # Transform each domain's category
        for domain, settings in domains.items():
            if isinstance(settings, dict) and "category" in settings:
                category = settings["category"]
                
                # Transform string category to enum value
                if isinstance(category, str) and category in CATEGORY_TO_ENUM_MAPPING:
                    settings["category"] = CATEGORY_TO_ENUM_MAPPING[category]
    
    return result


def restructure_focus_settings(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Restructure focus settings to focus_rules.
    
    Args:
        config_data: The configuration data to transform.
        
    Returns:
        The transformed configuration data.
    """
    # Create a copy to avoid modifying the original
    result = config_data.copy()
    
    # Initialize focus_rules if it doesn't exist
    if "focus_rules" not in result:
        result["focus_rules"] = {}
    
    # Map of old paths to new paths
    path_mappings = {
        "settings.focus.duration": "focus_rules.duration_minutes",
        "settings.focus.short_break": "focus_rules.break_minutes",
        "settings.focus.long_break": "focus_rules.long_break_minutes",
        "settings.focus.long_break_interval": "focus_rules.long_break_interval",
        "settings.focus.auto_start_breaks": "focus_rules.auto_start_breaks",
        "settings.focus.auto_start_focus": "focus_rules.auto_start_focus",
        "settings.notifications.sound": "focus_rules.notification_sound",
        "settings.notifications.volume": "focus_rules.notification_volume"
    }
    
    # Move each setting to its new location
    for old_path, new_path in path_mappings.items():
        # Extract components of the path
        old_components = old_path.split(".")
        new_components = new_path.split(".")
        
        # Navigate to the old value
        current = result
        found = True
        for component in old_components[:-1]:
            if component not in current or not isinstance(current[component], dict):
                found = False
                break
            current = current[component]
        
        if found and old_components[-1] in current:
            # Get the value
            value = current[old_components[-1]]
            
            # Navigate to the new location
            target = result
            for component in new_components[:-1]:
                if component not in target:
                    target[component] = {}
                target = target[component]
            
            # Set the value
            target[new_components[-1]] = value
            
            # Remove the old value
            del current[old_components[-1]]
    
    # Clean up empty dictionaries
    clean_empty_dicts(result)
    
    return result


def clean_empty_dicts(data: Dict[str, Any]) -> None:
    """
    Recursively remove empty dictionaries from a dictionary.
    
    Args:
        data: The dictionary to clean.
    """
    keys_to_delete = []
    
    for key, value in data.items():
        if isinstance(value, dict):
            clean_empty_dicts(value)
            if not value:
                keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del data[key]


def migrate_focus_guard_config(
    config_data: Dict[str, Any],
    target_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Migrate Focus Guard configuration data to the target version.
    
    Args:
        config_data: The configuration data to migrate.
        target_version: The target schema version. If None, uses the current version.
        
    Returns:
        The migrated configuration data.
    """
    # Get the source version from the config data
    source_version = config_data.get("schema_version", "1.0.0")
    
    # If target version is not specified, use the current version
    if target_version is None:
        target_version = CURRENT_SCHEMA_VERSION
    
    # If already at the target version, return as is
    if source_version == target_version:
        return config_data
    
    # Create migrator
    migrator = create_focus_guard_migrator()
    
    # Migrate the data
    migrated_data = migrator.migrate(config_data, target_version)
    
    # Update the schema version
    migrated_data["schema_version"] = target_version
    
    # Add migration history
    if "migration_history" not in migrated_data:
        migrated_data["migration_history"] = []
    
    migrated_data["migration_history"].append(migrator.create_migration_history(config_data))
    
    return migrated_data
