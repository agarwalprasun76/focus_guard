"""
Example schema plugin.

This module provides an example implementation of a schema plugin.
"""

from typing import Any, Dict, List, Optional, Set, Type
import re

from core_v2.config.interfaces import ConfigSchema, ConfigValidator
from core_v2.config.plugins.interfaces import SchemaPlugin, ValidatorPlugin


class EmailValidator(ConfigValidator):
    """
    Email address validator.
    
    This validator checks if a value is a valid email address.
    """
    
    def __init__(self, allow_empty: bool = False):
        """
        Initialize the email validator.
        
        Args:
            allow_empty: Whether to allow empty values.
        """
        self._allow_empty = allow_empty
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a value.
        
        Args:
            value: The value to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        # Check if the value is a string
        if not isinstance(value, str):
            return False, "Value must be a string"
        
        # Check if the value is empty
        if not value:
            if self._allow_empty:
                return True, None
            else:
                return False, "Email address cannot be empty"
        
        # Check if the value is a valid email address
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            return False, "Invalid email address format"
        
        return True, None


class UrlValidator(ConfigValidator):
    """
    URL validator.
    
    This validator checks if a value is a valid URL.
    """
    
    def __init__(self, allow_empty: bool = False, require_https: bool = False):
        """
        Initialize the URL validator.
        
        Args:
            allow_empty: Whether to allow empty values.
            require_https: Whether to require HTTPS URLs.
        """
        self._allow_empty = allow_empty
        self._require_https = require_https
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a value.
        
        Args:
            value: The value to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        # Check if the value is a string
        if not isinstance(value, str):
            return False, "Value must be a string"
        
        # Check if the value is empty
        if not value:
            if self._allow_empty:
                return True, None
            else:
                return False, "URL cannot be empty"
        
        # Check if the value is a valid URL
        url_pattern = r'^(https?://)([\w-]+(\.[\w-]+)+)([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?$'
        if not re.match(url_pattern, value):
            return False, "Invalid URL format"
        
        # Check if the URL uses HTTPS
        if self._require_https and not value.startswith('https://'):
            return False, "URL must use HTTPS"
        
        return True, None


class EmailSchema(ConfigSchema):
    """
    Email address schema.
    
    This schema validates email addresses.
    """
    
    def __init__(self, allow_empty: bool = False):
        """
        Initialize the email schema.
        
        Args:
            allow_empty: Whether to allow empty values.
        """
        self._validator = EmailValidator(allow_empty)
    
    def get_name(self) -> str:
        """
        Get the schema name.
        
        Returns:
            The schema name.
        """
        return "email"
    
    def get_description(self) -> str:
        """
        Get the schema description.
        
        Returns:
            The schema description.
        """
        return "Email address schema"
    
    def get_validator(self) -> ConfigValidator:
        """
        Get the schema validator.
        
        Returns:
            The schema validator.
        """
        return self._validator
    
    def get_default_value(self) -> Any:
        """
        Get the default value.
        
        Returns:
            The default value.
        """
        return ""
    
    def get_ui_hint(self) -> str:
        """
        Get the UI hint.
        
        Returns:
            The UI hint.
        """
        return "email"


class UrlSchema(ConfigSchema):
    """
    URL schema.
    
    This schema validates URLs.
    """
    
    def __init__(self, allow_empty: bool = False, require_https: bool = False):
        """
        Initialize the URL schema.
        
        Args:
            allow_empty: Whether to allow empty values.
            require_https: Whether to require HTTPS URLs.
        """
        self._validator = UrlValidator(allow_empty, require_https)
        self._require_https = require_https
    
    def get_name(self) -> str:
        """
        Get the schema name.
        
        Returns:
            The schema name.
        """
        return "url"
    
    def get_description(self) -> str:
        """
        Get the schema description.
        
        Returns:
            The schema description.
        """
        if self._require_https:
            return "HTTPS URL schema"
        else:
            return "URL schema"
    
    def get_validator(self) -> ConfigValidator:
        """
        Get the schema validator.
        
        Returns:
            The schema validator.
        """
        return self._validator
    
    def get_default_value(self) -> Any:
        """
        Get the default value.
        
        Returns:
            The default value.
        """
        return ""
    
    def get_ui_hint(self) -> str:
        """
        Get the UI hint.
        
        Returns:
            The UI hint.
        """
        return "url"


class CustomSchemaPlugin(SchemaPlugin):
    """
    Custom schema plugin.
    
    This plugin provides custom schema types for the configuration system.
    """
    
    def __init__(self):
        """Initialize the custom schema plugin."""
        self._name = "custom_schema_plugin"
        self._description = "Custom schema plugin for email and URL validation"
        self._version = "1.0.0"
    
    def get_name(self) -> str:
        """
        Get the plugin name.
        
        Returns:
            The plugin name.
        """
        return self._name
    
    def get_description(self) -> str:
        """
        Get the plugin description.
        
        Returns:
            The plugin description.
        """
        return self._description
    
    def get_version(self) -> str:
        """
        Get the plugin version.
        
        Returns:
            The plugin version.
        """
        return self._version
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if the plugin was initialized successfully, False otherwise.
        """
        return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin.
        
        Returns:
            True if the plugin was shut down successfully, False otherwise.
        """
        return True
    
    def get_schema_types(self) -> List[Type[ConfigSchema]]:
        """
        Get the schema types provided by this plugin.
        
        Returns:
            A list of schema types.
        """
        return [EmailSchema, UrlSchema]


class CustomValidatorPlugin(ValidatorPlugin):
    """
    Custom validator plugin.
    
    This plugin provides custom validators for the configuration system.
    """
    
    def __init__(self):
        """Initialize the custom validator plugin."""
        self._name = "custom_validator_plugin"
        self._description = "Custom validator plugin for email and URL validation"
        self._version = "1.0.0"
    
    def get_name(self) -> str:
        """
        Get the plugin name.
        
        Returns:
            The plugin name.
        """
        return self._name
    
    def get_description(self) -> str:
        """
        Get the plugin description.
        
        Returns:
            The plugin description.
        """
        return self._description
    
    def get_version(self) -> str:
        """
        Get the plugin version.
        
        Returns:
            The plugin version.
        """
        return self._version
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if the plugin was initialized successfully, False otherwise.
        """
        return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin.
        
        Returns:
            True if the plugin was shut down successfully, False otherwise.
        """
        return True
    
    def get_validators(self) -> List[Type[ConfigValidator]]:
        """
        Get the validators provided by this plugin.
        
        Returns:
            A list of validator types.
        """
        return [EmailValidator, UrlValidator]
