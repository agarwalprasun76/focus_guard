"""
Configuration migration framework.

This module provides classes and utilities for migrating configuration data
between different schema versions.
"""

from typing import Any, Dict, List, Optional, Callable, Type, Union
import logging
from datetime import datetime
import copy

# Set up logging
logger = logging.getLogger(__name__)


class MigrationStep:
    """
    Represents a single migration step between two schema versions.
    
    A migration step defines how to transform configuration data from
    one schema version to the next.
    """
    
    def __init__(
        self,
        source_version: str,
        target_version: str,
        description: str,
        transform_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ):
        """
        Initialize the migration step.
        
        Args:
            source_version: The source schema version.
            target_version: The target schema version.
            description: A description of the migration step.
            transform_func: A function that transforms configuration data
                from the source version to the target version.
        """
        self.source_version = source_version
        self.target_version = target_version
        self.description = description
        self.transform_func = transform_func
    
    def apply(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply the migration step to configuration data.
        
        Args:
            config_data: The configuration data to transform.
            
        Returns:
            The transformed configuration data.
        """
        logger.info(f"Applying migration step: {self.description} ({self.source_version} -> {self.target_version})")
        
        try:
            # Create a deep copy to avoid modifying the original data
            result = self.transform_func(copy.deepcopy(config_data))
            
            # Update the schema version
            if isinstance(result, dict):
                if "_schema_version" not in result:
                    result["_schema_version"] = self.target_version
                elif result["_schema_version"] == self.source_version:
                    result["_schema_version"] = self.target_version
            
            return result
        except Exception as e:
            logger.error(f"Error applying migration step: {e}")
            raise


class ConfigMigrator:
    """
    Manages configuration schema migrations.
    
    This class handles the migration of configuration data between different
    schema versions, applying the appropriate migration steps in sequence.
    """
    
    def __init__(self, current_version: str):
        """
        Initialize the configuration migrator.
        
        Args:
            current_version: The current schema version.
        """
        self.current_version = current_version
        self.migration_steps: Dict[str, Dict[str, MigrationStep]] = {}
        self.version_history: List[str] = []
    
    def register_migration_step(self, step: MigrationStep) -> None:
        """
        Register a migration step.
        
        Args:
            step: The migration step to register.
        """
        source = step.source_version
        target = step.target_version
        
        # Initialize dictionaries if needed
        if source not in self.migration_steps:
            self.migration_steps[source] = {}
        
        # Register the step
        self.migration_steps[source][target] = step
        
        # Update version history
        if source not in self.version_history:
            self.version_history.append(source)
        if target not in self.version_history:
            self.version_history.append(target)
        
        # Sort version history
        self._sort_version_history()
    
    def _sort_version_history(self) -> None:
        """Sort the version history based on semantic versioning."""
        # This is a simple implementation that assumes versions are in format x.y.z
        def version_key(v: str) -> tuple:
            try:
                return tuple(map(int, v.split('.')))
            except (ValueError, AttributeError):
                # If the version is not in the expected format, use a default value
                return (0, 0, 0)
        
        self.version_history.sort(key=version_key)
    
    def find_migration_path(self, source_version: str, target_version: str) -> List[MigrationStep]:
        """
        Find a path of migration steps from source to target version.
        
        Args:
            source_version: The source schema version.
            target_version: The target schema version.
            
        Returns:
            A list of migration steps to apply in sequence.
            
        Raises:
            ValueError: If no migration path is found.
        """
        # If source and target are the same, no migration is needed
        if source_version == target_version:
            return []
        
        # Find the path using breadth-first search
        queue = [(source_version, [])]
        visited = set()
        
        while queue:
            current_version, path = queue.pop(0)
            
            if current_version in visited:
                continue
            
            visited.add(current_version)
            
            # Check if we've reached the target
            if current_version == target_version:
                return path
            
            # Add all possible next steps
            if current_version in self.migration_steps:
                for next_version, step in self.migration_steps[current_version].items():
                    if next_version not in visited:
                        queue.append((next_version, path + [step]))
        
        # If we get here, no path was found
        raise ValueError(f"No migration path found from {source_version} to {target_version}")
    
    def migrate(self, config_data: Dict[str, Any], target_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Migrate configuration data to the target version.
        
        Args:
            config_data: The configuration data to migrate.
            target_version: The target schema version. If None, uses the current version.
            
        Returns:
            The migrated configuration data.
            
        Raises:
            ValueError: If no migration path is found.
        """
        # Use current version if target is not specified
        if target_version is None:
            target_version = self.current_version
        
        # Get the source version from the config data
        source_version = config_data.get("_schema_version", "0.0.0")
        
        # If source and target are the same, no migration is needed
        if source_version == target_version:
            return config_data
        
        # Find the migration path
        try:
            migration_path = self.find_migration_path(source_version, target_version)
        except ValueError as e:
            logger.error(f"Migration failed: {e}")
            raise
        
        # Apply each migration step in sequence
        result = config_data
        for step in migration_path:
            result = step.apply(result)
        
        return result
    
    def create_migration_history(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a migration history entry for configuration data.
        
        Args:
            config_data: The configuration data.
            
        Returns:
            A dictionary with migration history information.
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "source_version": config_data.get("_schema_version", "0.0.0"),
            "target_version": self.current_version
        }


# Helper functions for common migration operations

def rename_field(old_name: str, new_name: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Create a migration function that renames a field.
    
    Args:
        old_name: The old field name.
        new_name: The new field name.
        
    Returns:
        A function that transforms configuration data by renaming a field.
    """
    def transform(config_data: Dict[str, Any]) -> Dict[str, Any]:
        if old_name in config_data:
            config_data[new_name] = config_data.pop(old_name)
        return config_data
    
    return transform


def move_field(source_path: str, target_path: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Create a migration function that moves a field to a new location.
    
    Args:
        source_path: The source path (dot-separated).
        target_path: The target path (dot-separated).
        
    Returns:
        A function that transforms configuration data by moving a field.
    """
    def transform(config_data: Dict[str, Any]) -> Dict[str, Any]:
        # Get the source value
        source_parts = source_path.split('.')
        source_value = config_data
        
        for part in source_parts[:-1]:
            if part not in source_value or not isinstance(source_value[part], dict):
                # Source path doesn't exist or is not a dictionary
                return config_data
            source_value = source_value[part]
        
        if source_parts[-1] not in source_value:
            # Source field doesn't exist
            return config_data
        
        # Get the value to move
        value = source_value[source_parts[-1]]
        
        # Create the target path
        target_parts = target_path.split('.')
        target_dict = config_data
        
        for part in target_parts[:-1]:
            if part not in target_dict:
                target_dict[part] = {}
            elif not isinstance(target_dict[part], dict):
                # Target path exists but is not a dictionary
                return config_data
            target_dict = target_dict[part]
        
        # Set the value at the target path
        target_dict[target_parts[-1]] = value
        
        # Remove the source field
        del source_value[source_parts[-1]]
        
        return config_data
    
    return transform


def transform_field(
    field_path: str, 
    transform_func: Callable[[Any], Any]
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Create a migration function that transforms a field value.
    
    Args:
        field_path: The field path (dot-separated).
        transform_func: A function that transforms the field value.
        
    Returns:
        A function that transforms configuration data by transforming a field value.
    """
    def transform(config_data: Dict[str, Any]) -> Dict[str, Any]:
        # Get the field value
        parts = field_path.split('.')
        current = config_data
        
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                # Path doesn't exist or is not a dictionary
                return config_data
            current = current[part]
        
        if parts[-1] not in current:
            # Field doesn't exist
            return config_data
        
        # Transform the value
        current[parts[-1]] = transform_func(current[parts[-1]])
        
        return config_data
    
    return transform


def add_field(
    field_path: str, 
    value: Any
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Create a migration function that adds a new field.
    
    Args:
        field_path: The field path (dot-separated).
        value: The value to set.
        
    Returns:
        A function that transforms configuration data by adding a new field.
    """
    def transform(config_data: Dict[str, Any]) -> Dict[str, Any]:
        # Create the path
        parts = field_path.split('.')
        current = config_data
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # Path exists but is not a dictionary
                return config_data
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value
        
        return config_data
    
    return transform


def remove_field(field_path: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Create a migration function that removes a field.
    
    Args:
        field_path: The field path (dot-separated).
        
    Returns:
        A function that transforms configuration data by removing a field.
    """
    def transform(config_data: Dict[str, Any]) -> Dict[str, Any]:
        # Get the field value
        parts = field_path.split('.')
        current = config_data
        
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                # Path doesn't exist or is not a dictionary
                return config_data
            current = current[part]
        
        if parts[-1] in current:
            # Remove the field
            del current[parts[-1]]
        
        return config_data
    
    return transform
