"""
Schema definition and validation for configuration values.

This module provides classes for defining configuration schemas and validating
configuration values against those schemas.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union, TypeVar, Generic, get_type_hints
import re
from datetime import datetime

from core_v2.config.interfaces import ConfigSchema, ConfigValidator


class ConfigValueType(Enum):
    """Enumeration of supported configuration value types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"
    EMAIL = "email"
    URL = "url"
    PATH = "path"
    DATETIME = "datetime"


class TypeValidator(ConfigValidator):
    """Validator for checking value types."""
    
    def __init__(self, value_type: ConfigValueType):
        """
        Initialize the type validator.
        
        Args:
            value_type: The expected type of the value.
        """
        self.value_type = value_type
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate that a value is of the expected type.
        
        Args:
            value: The value to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if self.value_type == ConfigValueType.STRING:
            if not isinstance(value, str):
                return False, f"Expected string, got {type(value).__name__}"
        elif self.value_type == ConfigValueType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool):
                return False, f"Expected integer, got {type(value).__name__}"
        elif self.value_type == ConfigValueType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False, f"Expected number, got {type(value).__name__}"
        elif self.value_type == ConfigValueType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"Expected boolean, got {type(value).__name__}"
        elif self.value_type == ConfigValueType.LIST:
            if not isinstance(value, list):
                return False, f"Expected list, got {type(value).__name__}"
        elif self.value_type == ConfigValueType.OBJECT:
            if not isinstance(value, dict):
                return False, f"Expected object, got {type(value).__name__}"
        elif self.value_type == ConfigValueType.EMAIL:
            if not isinstance(value, str):
                return False, f"Expected email string, got {type(value).__name__}"
            # Simple email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                return False, "Invalid email format"
        elif self.value_type == ConfigValueType.URL:
            if not isinstance(value, str):
                return False, f"Expected URL string, got {type(value).__name__}"
            # Simple URL validation
            url_pattern = r'^(http|https)://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
            if not re.match(url_pattern, value):
                return False, "Invalid URL format"
        elif self.value_type == ConfigValueType.PATH:
            if not isinstance(value, str):
                return False, f"Expected path string, got {type(value).__name__}"
        elif self.value_type == ConfigValueType.DATETIME:
            if not isinstance(value, (str, datetime)):
                return False, f"Expected datetime string or object, got {type(value).__name__}"
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value)
                except ValueError:
                    return False, "Invalid datetime format, expected ISO format"
        
        return True, None


class RangeValidator(ConfigValidator):
    """Validator for checking numeric ranges."""
    
    def __init__(self, min_value: Optional[Union[int, float]] = None, max_value: Optional[Union[int, float]] = None):
        """
        Initialize the range validator.
        
        Args:
            min_value: The minimum allowed value (inclusive).
            max_value: The maximum allowed value (inclusive).
        """
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate that a value is within the specified range.
        
        Args:
            value: The value to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not isinstance(value, (int, float)):
            return False, f"Expected number, got {type(value).__name__}"
        
        if self.min_value is not None and value < self.min_value:
            return False, f"Value {value} is less than minimum {self.min_value}"
        
        if self.max_value is not None and value > self.max_value:
            return False, f"Value {value} is greater than maximum {self.max_value}"
        
        return True, None


class LengthValidator(ConfigValidator):
    """Validator for checking string or list lengths."""
    
    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None):
        """
        Initialize the length validator.
        
        Args:
            min_length: The minimum allowed length (inclusive).
            max_length: The maximum allowed length (inclusive).
        """
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate that a value's length is within the specified range.
        
        Args:
            value: The value to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not hasattr(value, "__len__"):
            return False, f"Value of type {type(value).__name__} does not have a length"
        
        length = len(value)
        
        if self.min_length is not None and length < self.min_length:
            return False, f"Length {length} is less than minimum {self.min_length}"
        
        if self.max_length is not None and length > self.max_length:
            return False, f"Length {length} is greater than maximum {self.max_length}"
        
        return True, None


class PatternValidator(ConfigValidator):
    """Validator for checking string patterns."""
    
    def __init__(self, pattern: str):
        """
        Initialize the pattern validator.
        
        Args:
            pattern: The regular expression pattern to match.
        """
        self.pattern = pattern
        self.regex = re.compile(pattern)
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate that a value matches the specified pattern.
        
        Args:
            value: The value to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not isinstance(value, str):
            return False, f"Expected string, got {type(value).__name__}"
        
        if not self.regex.match(value):
            return False, f"Value does not match pattern {self.pattern}"
        
        return True, None


class EnumValidator(ConfigValidator):
    """Validator for checking enum values."""
    
    def __init__(self, enum_values: List[Any]):
        """
        Initialize the enum validator.
        
        Args:
            enum_values: The list of allowed values.
        """
        self.enum_values = enum_values
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate that a value is one of the allowed enum values.
        
        Args:
            value: The value to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if value not in self.enum_values:
            return False, f"Value {value} is not one of {self.enum_values}"
        
        return True, None


@dataclass
class ConfigValueSchema:
    """Schema for a configuration value."""
    name: str
    type: ConfigValueType
    description: str
    default: Any = None
    required: bool = False
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[Any]] = None
    item_type: Optional[ConfigValueType] = None
    properties: Optional[Dict[str, 'ConfigValueSchema']] = None
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a value against this schema.
        
        Args:
            value: The value to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        # Check if value is required
        if value is None:
            if self.required:
                return False, f"{self.name} is required"
            return True, None
        
        # Type validation
        type_validator = TypeValidator(self.type)
        is_valid, error = type_validator.validate(value)
        if not is_valid:
            return False, error
        
        # Range validation for numeric types
        if self.type in (ConfigValueType.INTEGER, ConfigValueType.FLOAT) and (self.min_value is not None or self.max_value is not None):
            range_validator = RangeValidator(self.min_value, self.max_value)
            is_valid, error = range_validator.validate(value)
            if not is_valid:
                return False, error
        
        # Length validation for strings and lists
        if self.type in (ConfigValueType.STRING, ConfigValueType.LIST, ConfigValueType.EMAIL, ConfigValueType.URL, ConfigValueType.PATH) and (self.min_length is not None or self.max_length is not None):
            length_validator = LengthValidator(self.min_length, self.max_length)
            is_valid, error = length_validator.validate(value)
            if not is_valid:
                return False, error
        
        # Pattern validation for strings
        if self.type in (ConfigValueType.STRING, ConfigValueType.EMAIL, ConfigValueType.URL, ConfigValueType.PATH) and self.pattern is not None:
            pattern_validator = PatternValidator(self.pattern)
            is_valid, error = pattern_validator.validate(value)
            if not is_valid:
                return False, error
        
        # Enum validation
        if self.enum_values is not None:
            enum_validator = EnumValidator(self.enum_values)
            is_valid, error = enum_validator.validate(value)
            if not is_valid:
                return False, error
        
        # List item validation
        if self.type == ConfigValueType.LIST and self.item_type is not None and value:
            item_validator = TypeValidator(self.item_type)
            for i, item in enumerate(value):
                is_valid, error = item_validator.validate(item)
                if not is_valid:
                    return False, f"Item {i}: {error}"
        
        # Object property validation
        if self.type == ConfigValueType.OBJECT and self.properties is not None:
            if not isinstance(value, dict):
                return False, f"Expected object, got {type(value).__name__}"
            
            for prop_name, prop_schema in self.properties.items():
                if prop_name in value:
                    is_valid, error = prop_schema.validate(value[prop_name])
                    if not is_valid:
                        return False, f"Property {prop_name}: {error}"
                elif prop_schema.required:
                    return False, f"Required property {prop_name} is missing"
        
        return True, None


class ConfigSectionSchema(Generic[T]):
    """Schema for a configuration section."""
    
    def __init__(self, name: str, description: str):
        """
        Initialize the configuration section schema.
        
        Args:
            name: The name of the section.
            description: The description of the section.
        """
        self.name = name
        self.description = description
        self.properties: Dict[str, ConfigValueSchema] = {}
    
    def get_name(self) -> str:
        """
        Get the name of the schema.
        
        Returns:
            The name of the schema.
        """
        return self.name
    
    def get_description(self) -> str:
        """
        Get the description of the schema.
        
        Returns:
            The description of the schema.
        """
        return self.description
    
    def add_property(self, prop: ConfigValueSchema) -> None:
        """
        Add a property to this section.
        
        Args:
            prop: The property schema to add.
        """
        self.properties[prop.name] = prop
    
    def validate(self, config: Dict[str, Any]) -> tuple[bool, Dict[str, str]]:
        """
        Validate a configuration against this schema.
        
        Args:
            config: The configuration to validate.
            
        Returns:
            A tuple of (is_valid, error_dict).
        """
        errors = {}
        
        for prop_name, prop_schema in self.properties.items():
            if prop_name in config:
                is_valid, error = prop_schema.validate(config[prop_name])
                if not is_valid:
                    errors[prop_name] = error
            elif prop_schema.required:
                errors[prop_name] = f"Required property {prop_name} is missing"
        
        return len(errors) == 0, errors
    
    def get_defaults(self) -> Dict[str, Any]:
        """
        Get the default values for this schema.
        
        Returns:
            A dictionary of default values.
        """
        defaults = {}
        
        for prop_name, prop_schema in self.properties.items():
            if prop_schema.default is not None:
                defaults[prop_name] = prop_schema.default
        
        return defaults


T = TypeVar('T')

class DataclassConfigSchema(ConfigSchema[T], Generic[T]):
    """
    Configuration schema based on a dataclass.
    
    This class uses a dataclass type to define the schema for a configuration section.
    It automatically extracts property information from the dataclass fields.
    """
    
    def __init__(self, dataclass_type: Type[T], name: str = None, description: str = None):
        """
        Initialize the dataclass-based configuration schema.
        
        Args:
            dataclass_type: The dataclass type to use for the schema.
            name: Optional name for the schema. If not provided, uses the dataclass name.
            description: Optional description for the schema.
        """
        self.dataclass_type = dataclass_type
        self._name = name or dataclass_type.__name__
        self._description = description or dataclass_type.__doc__ or f"Configuration for {self._name}"
        self._properties = self._extract_properties()
    
    def _extract_properties(self) -> Dict[str, ConfigValueSchema]:
        """
        Extract property schemas from the dataclass fields.
        
        Returns:
            A dictionary mapping field names to property schemas.
        """
        properties = {}
        hints = get_type_hints(self.dataclass_type)
        
        for field_name, field_type in hints.items():
            # Skip private fields
            if field_name.startswith('_'):
                continue
            
            # Determine ConfigValueType from Python type
            value_type = self._get_value_type(field_type)
            
            # Get default value if available
            default = getattr(self.dataclass_type, field_name, None)
            
            # Create property schema
            properties[field_name] = ConfigValueSchema(
                name=field_name,
                type=value_type,
                description=f"{field_name} configuration",
                default=default,
                required=default is None
            )
        
        return properties
    
    def _get_value_type(self, python_type) -> ConfigValueType:
        """
        Convert a Python type to a ConfigValueType.
        
        Args:
            python_type: The Python type to convert.
            
        Returns:
            The corresponding ConfigValueType.
        """
        if python_type == str:
            return ConfigValueType.STRING
        elif python_type == int:
            return ConfigValueType.INTEGER
        elif python_type == float:
            return ConfigValueType.FLOAT
        elif python_type == bool:
            return ConfigValueType.BOOLEAN
        elif getattr(python_type, "__origin__", None) == list:
            return ConfigValueType.LIST
        elif getattr(python_type, "__origin__", None) == dict:
            return ConfigValueType.OBJECT
        elif python_type == datetime:
            return ConfigValueType.DATETIME
        else:
            return ConfigValueType.OBJECT
    
    def get_name(self) -> str:
        """
        Get the name of the schema.
        
        Returns:
            The name of the schema.
        """
        return self._name
    
    def get_description(self) -> str:
        """
        Get the description of the schema.
        
        Returns:
            The description of the schema.
        """
        return self._description
    
    def validate(self, config: Dict[str, Any]) -> tuple[bool, Dict[str, str]]:
        """
        Validate a configuration against this schema.
        
        Args:
            config: The configuration to validate.
            
        Returns:
            A tuple of (is_valid, error_dict).
        """
        errors = {}
        
        for prop_name, prop_schema in self._properties.items():
            if prop_name in config:
                is_valid, error = prop_schema.validate(config[prop_name])
                if not is_valid:
                    errors[prop_name] = error
            elif prop_schema.required:
                errors[prop_name] = f"Required property {prop_name} is missing"
        
        return len(errors) == 0, errors
    
    def get_defaults(self) -> Dict[str, Any]:
        """
        Get the default values for this schema.
        
        Returns:
            A dictionary of default values.
        """
        defaults = {}
        
        for prop_name, prop_schema in self._properties.items():
            if prop_schema.default is not None:
                defaults[prop_name] = prop_schema.default
        
        return defaults
    
    def create_instance(self, config: Dict[str, Any]) -> T:
        """
        Create a typed instance from a configuration dictionary.
        
        Args:
            config: The configuration dictionary.
            
        Returns:
            A typed instance representing the configuration.
        """
        # Filter the config to only include fields that exist in the dataclass
        filtered_config = {k: v for k, v in config.items() if k in self._properties}
        
        # Create an instance of the dataclass with the filtered config
        return self.dataclass_type(**filtered_config)
