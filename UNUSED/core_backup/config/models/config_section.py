"""
Configuration section models.

This module provides classes for representing configuration sections that
group related configuration values together.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, get_type_hints
from dataclasses import dataclass, field, fields, is_dataclass

from core_v2.config.interfaces import ConfigPath, ConfigChangeCallback
from core_v2.config.models.config_value import ConfigurationValue


class ConfigurationSection:
    """
    Base class for configuration sections.
    
    Configuration sections group related configuration values together
    and provide a structured way to access and manage them.
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize the configuration section.
        
        Args:
            name: The name of the section.
            description: The description of the section.
        """
        self._name = name
        self._description = description
        self._values: Dict[str, ConfigurationValue] = {}
        self._sections: Dict[str, 'ConfigurationSection'] = {}
        self._path = name
    
    def get_name(self) -> str:
        """
        Get the name of the section.
        
        Returns:
            The name of the section.
        """
        return self._name
    
    def get_description(self) -> str:
        """
        Get the description of the section.
        
        Returns:
            The description of the section.
        """
        return self._description
    
    def get_path(self) -> str:
        """
        Get the full path of the section.
        
        Returns:
            The full path of the section.
        """
        return self._path
    
    def set_path(self, path: str) -> None:
        """
        Set the path of the section.
        
        Args:
            path: The path to set.
        """
        self._path = path
        
        # Update paths of child values and sections
        for name, value in self._values.items():
            value.set_path(f"{path}.{name}")
        
        for name, section in self._sections.items():
            section.set_path(f"{path}.{name}")
    
    def add_value(self, name: str, value: ConfigurationValue) -> None:
        """
        Add a configuration value to the section.
        
        Args:
            name: The name of the value.
            value: The configuration value to add.
        """
        self._values[name] = value
        value.set_path(f"{self._path}.{name}")
    
    def add_section(self, name: str, section: 'ConfigurationSection') -> None:
        """
        Add a subsection to the section.
        
        Args:
            name: The name of the section.
            section: The configuration section to add.
        """
        self._sections[name] = section
        section.set_path(f"{self._path}.{name}")
    
    def get_value(self, name: str) -> Optional[ConfigurationValue]:
        """
        Get a configuration value by name.
        
        Args:
            name: The name of the value.
            
        Returns:
            The configuration value, or None if not found.
        """
        return self._values.get(name)
    
    def get_section(self, name: str) -> Optional['ConfigurationSection']:
        """
        Get a subsection by name.
        
        Args:
            name: The name of the section.
            
        Returns:
            The configuration section, or None if not found.
        """
        return self._sections.get(name)
    
    def get_value_at_path(self, path: str) -> Optional[ConfigurationValue]:
        """
        Get a configuration value by path.
        
        Args:
            path: The path to the value, relative to this section.
            
        Returns:
            The configuration value, or None if not found.
        """
        if not path:
            return None
        
        parts = path.split('.')
        first, rest = parts[0], '.'.join(parts[1:]) if len(parts) > 1 else ""
        
        if first in self._values and not rest:
            return self._values[first]
        
        if first in self._sections:
            return self._sections[first].get_value_at_path(rest)
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the section to a dictionary.
        
        Returns:
            A dictionary representation of the section.
        """
        result = {}
        
        # Add values
        for name, value in self._values.items():
            result[name] = value.get()
        
        # Add sections
        for name, section in self._sections.items():
            result[name] = section.to_dict()
        
        return result
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update the section from a dictionary.
        
        Args:
            data: The dictionary to update from.
        """
        if not isinstance(data, dict):
            return
        
        # Update values
        for name, value in self._values.items():
            if name in data:
                value.set(data[name])
        
        # Update sections
        for name, section in self._sections.items():
            if name in data and isinstance(data[name], dict):
                section.from_dict(data[name])
    
    def register_change_callback(self, callback: ConfigChangeCallback) -> None:
        """
        Register a change callback for all values in this section.
        
        Args:
            callback: The callback to register.
        """
        # Register for values
        for value in self._values.values():
            value.add_change_listener(callback)
        
        # Register for sections
        for section in self._sections.values():
            section.register_change_callback(callback)
    
    def unregister_change_callback(self, callback: ConfigChangeCallback) -> None:
        """
        Unregister a change callback for all values in this section.
        
        Args:
            callback: The callback to unregister.
        """
        # Unregister for values
        for value in self._values.values():
            value.remove_change_listener(callback)
        
        # Unregister for sections
        for section in self._sections.values():
            section.unregister_change_callback(callback)


class DataclassConfigSection(ConfigurationSection):
    """
    Configuration section based on a dataclass.
    
    This class uses a dataclass to define the structure of a configuration section,
    automatically creating configuration values based on the dataclass fields.
    """
    
    def __init__(self, dataclass_instance: Any, name: Optional[str] = None, description: Optional[str] = None):
        """
        Initialize the dataclass-based configuration section.
        
        Args:
            dataclass_instance: An instance of the dataclass to use.
            name: Optional name for the section. If not provided, uses the dataclass name.
            description: Optional description for the section.
        """
        if not is_dataclass(dataclass_instance):
            raise TypeError("dataclass_instance must be an instance of a dataclass")
        
        # Use dataclass name if name not provided
        if name is None:
            name = type(dataclass_instance).__name__
        
        # Use dataclass docstring if description not provided
        if description is None:
            description = type(dataclass_instance).__doc__ or f"Configuration for {name}"
        
        super().__init__(name, description)
        
        # Create configuration values from dataclass fields
        self._create_values_from_dataclass(dataclass_instance)
    
    def _create_values_from_dataclass(self, dataclass_instance: Any) -> None:
        """
        Create configuration values from dataclass fields.
        
        Args:
            dataclass_instance: The dataclass instance to use.
        """
        for field_obj in fields(dataclass_instance):
            field_name = field_obj.name
            field_value = getattr(dataclass_instance, field_name)
            
            # Skip private fields
            if field_name.startswith('_'):
                continue
            
            # If the field is another dataclass, create a nested section
            if is_dataclass(field_value):
                subsection = DataclassConfigSection(field_value, field_name)
                self.add_section(field_name, subsection)
            else:
                # Create a configuration value based on the field type
                config_value = self._create_config_value(field_value, field_obj)
                self.add_value(field_name, config_value)
    
    def _create_config_value(self, value: Any, field_obj: Any) -> ConfigurationValue:
        """
        Create a configuration value based on a dataclass field.
        
        Args:
            value: The field value.
            field_obj: The field object.
            
        Returns:
            A configuration value for the field.
        """
        from core_v2.config.models.config_value import (
            ConfigurationValue, StringConfigValue, IntegerConfigValue,
            BooleanConfigValue, ListConfigValue, DictConfigValue
        )
        
        # Get field type
        field_type = field_obj.type
        
        # Create appropriate configuration value based on type
        if field_type == str:
            return StringConfigValue(value)
        elif field_type == int:
            return IntegerConfigValue(value)
        elif field_type == bool:
            return BooleanConfigValue(value)
        elif getattr(field_type, "__origin__", None) == list:
            return ListConfigValue(value)
        elif getattr(field_type, "__origin__", None) == dict:
            return DictConfigValue(value)
        else:
            # Default to generic configuration value
            return ConfigurationValue(value)
    
    def to_dataclass(self, dataclass_type: Type) -> Any:
        """
        Convert the section to a dataclass instance.
        
        Args:
            dataclass_type: The dataclass type to create.
            
        Returns:
            An instance of the dataclass.
        """
        # Create a dictionary of field values
        field_values = {}
        
        # Get values from configuration values
        for name, value in self._values.items():
            field_values[name] = value.get()
        
        # Get values from subsections
        for name, section in self._sections.items():
            if isinstance(section, DataclassConfigSection):
                # Get the field type from the dataclass
                field_type = get_type_hints(dataclass_type).get(name)
                if field_type and is_dataclass(field_type):
                    field_values[name] = section.to_dataclass(field_type)
        
        # Create the dataclass instance
        return dataclass_type(**field_values)
    
    def from_dataclass(self, dataclass_instance: Any) -> None:
        """
        Update the section from a dataclass instance.
        
        Args:
            dataclass_instance: The dataclass instance to update from.
        """
        if not is_dataclass(dataclass_instance):
            raise TypeError("dataclass_instance must be an instance of a dataclass")
        
        # Update values from dataclass fields
        for field_obj in fields(dataclass_instance):
            field_name = field_obj.name
            field_value = getattr(dataclass_instance, field_name)
            
            # Skip private fields
            if field_name.startswith('_'):
                continue
            
            # Update value or section
            if field_name in self._values:
                self._values[field_name].set(field_value)
            elif field_name in self._sections and is_dataclass(field_value):
                if isinstance(self._sections[field_name], DataclassConfigSection):
                    self._sections[field_name].from_dataclass(field_value)


# Create a helper function to easily create configuration sections from dataclasses
def create_section_from_dataclass(dataclass_instance: Any, name: Optional[str] = None, description: Optional[str] = None) -> DataclassConfigSection:
    """
    Create a configuration section from a dataclass.
    
    Args:
        dataclass_instance: The dataclass instance to use.
        name: Optional name for the section.
        description: Optional description for the section.
        
    Returns:
        A configuration section based on the dataclass.
    """
    return DataclassConfigSection(dataclass_instance, name, description)
