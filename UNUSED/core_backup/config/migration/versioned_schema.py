"""
Versioned configuration schemas.

This module provides classes for defining versioned configuration schemas
that support automatic migration between versions.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Callable
import copy
from dataclasses import dataclass, is_dataclass

from core_v2.config.interfaces import ConfigSchema
from core_v2.config.schema import ConfigSectionSchema, DataclassConfigSchema
from core_v2.config.migration.migrator import ConfigMigrator, MigrationStep


class VersionedConfigSchema(ConfigSchema):
    """
    Base class for versioned configuration schemas.
    
    This class extends the basic configuration schema with versioning support,
    allowing automatic migration between schema versions.
    """
    
    def __init__(self, name: str, version: str, description: str = ""):
        """
        Initialize the versioned configuration schema.
        
        Args:
            name: The name of the schema.
            version: The schema version.
            description: The schema description.
        """
        self._name = name
        self._version = version
        self._description = description
        self._migrator = ConfigMigrator(version)
    
    def get_name(self) -> str:
        """
        Get the name of the schema.
        
        Returns:
            The schema name.
        """
        return self._name
    
    def get_version(self) -> str:
        """
        Get the version of the schema.
        
        Returns:
            The schema version.
        """
        return self._version
    
    def get_description(self) -> str:
        """
        Get the description of the schema.
        
        Returns:
            The schema description.
        """
        return self._description
    
    def register_migration_step(self, step: MigrationStep) -> None:
        """
        Register a migration step.
        
        Args:
            step: The migration step to register.
        """
        self._migrator.register_migration_step(step)
    
    def migrate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate configuration data to the current schema version.
        
        Args:
            data: The configuration data to migrate.
            
        Returns:
            The migrated configuration data.
        """
        if not data:
            # If data is empty, return a new dict with the schema version
            return {"_schema_version": self._version}
        
        # Migrate the data
        return self._migrator.migrate(data)
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate configuration data against the schema.
        
        Args:
            data: The configuration data to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        # Ensure the data has the correct schema version
        if "_schema_version" not in data:
            data["_schema_version"] = self._version
        elif data["_schema_version"] != self._version:
            # Migrate the data if needed
            try:
                data = self.migrate_data(data)
            except ValueError as e:
                return False, f"Schema version mismatch and migration failed: {e}"
        
        # Perform additional validation in subclasses
        return True, None
    
    def create_instance(self, data: Dict[str, Any]) -> Any:
        """
        Create an instance from configuration data.
        
        Args:
            data: The configuration data.
            
        Returns:
            An instance created from the data.
        """
        # Migrate the data if needed
        if "_schema_version" not in data or data["_schema_version"] != self._version:
            data = self.migrate_data(data)
        
        # Create the instance (to be implemented by subclasses)
        raise NotImplementedError("Subclasses must implement create_instance")


class VersionedSectionSchema(VersionedConfigSchema):
    """
    Versioned schema for configuration sections.
    
    This class combines the versioning support with section schema validation.
    """
    
    def __init__(
        self, 
        name: str, 
        version: str, 
        section_schema: ConfigSectionSchema,
        description: str = ""
    ):
        """
        Initialize the versioned section schema.
        
        Args:
            name: The name of the schema.
            version: The schema version.
            section_schema: The section schema to use for validation.
            description: The schema description.
        """
        super().__init__(name, version, description)
        self._section_schema = section_schema
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate configuration data against the schema.
        
        Args:
            data: The configuration data to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        # First, validate using the versioned schema
        is_valid, error = super().validate(data)
        if not is_valid:
            return is_valid, error
        
        # Then, validate using the section schema
        return self._section_schema.validate(data)
    
    def create_instance(self, data: Dict[str, Any]) -> Any:
        """
        Create an instance from configuration data.
        
        Args:
            data: The configuration data.
            
        Returns:
            An instance created from the data.
        """
        # Migrate the data if needed
        if "_schema_version" not in data or data["_schema_version"] != self._version:
            data = self.migrate_data(data)
        
        # Create the instance using the section schema
        return self._section_schema.create_instance(data)


class VersionedDataclassSchema(VersionedConfigSchema):
    """
    Versioned schema for dataclass-based configuration.
    
    This class combines the versioning support with dataclass schema validation.
    """
    
    def __init__(
        self, 
        name: str, 
        version: str, 
        dataclass_type: Type,
        description: str = ""
    ):
        """
        Initialize the versioned dataclass schema.
        
        Args:
            name: The name of the schema.
            version: The schema version.
            dataclass_type: The dataclass type to use for validation.
            description: The schema description.
        """
        if not is_dataclass(dataclass_type):
            raise TypeError("dataclass_type must be a dataclass")
        
        super().__init__(name, version, description)
        self._dataclass_type = dataclass_type
        self._dataclass_schema = DataclassConfigSchema(dataclass_type)
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate configuration data against the schema.
        
        Args:
            data: The configuration data to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        # First, validate using the versioned schema
        is_valid, error = super().validate(data)
        if not is_valid:
            return is_valid, error
        
        # Then, validate using the dataclass schema
        return self._dataclass_schema.validate(data)
    
    def create_instance(self, data: Dict[str, Any]) -> Any:
        """
        Create an instance from configuration data.
        
        Args:
            data: The configuration data.
            
        Returns:
            An instance of the dataclass.
        """
        # Migrate the data if needed
        if "_schema_version" not in data or data["_schema_version"] != self._version:
            data = self.migrate_data(data)
        
        # Create the instance using the dataclass schema
        return self._dataclass_schema.create_instance(data)


# Helper function to create a versioned schema from a dataclass
def create_versioned_schema(
    dataclass_type: Type,
    name: Optional[str] = None,
    version: str = "1.0.0",
    description: Optional[str] = None
) -> VersionedDataclassSchema:
    """
    Create a versioned schema from a dataclass.
    
    Args:
        dataclass_type: The dataclass type to use.
        name: Optional name for the schema. If not provided, uses the dataclass name.
        version: The schema version.
        description: Optional description for the schema.
        
    Returns:
        A versioned dataclass schema.
    """
    if not is_dataclass(dataclass_type):
        raise TypeError("dataclass_type must be a dataclass")
    
    # Use dataclass name if name not provided
    if name is None:
        name = dataclass_type.__name__
    
    # Use dataclass docstring if description not provided
    if description is None:
        description = dataclass_type.__doc__ or f"Configuration schema for {name}"
    
    return VersionedDataclassSchema(name, version, dataclass_type, description)
