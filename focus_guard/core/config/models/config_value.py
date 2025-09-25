"""
Configuration value models.

This module provides classes for representing configuration values in a
structured way with support for validation, change tracking, and notifications.
"""

from typing import Any, Optional, Callable, List, Dict, Union
from datetime import datetime
import copy

from focus_guard.core.config.interfaces import ConfigValue, ConfigChangeCallback


class ConfigurationValue:
    """
    Represents a typed configuration value.
    
    This class provides a wrapper around a configuration value with support
    for validation, change tracking, and notifications.
    """
    
    def __init__(
        self, 
        path: str,
        value: Any = None, 
        default: Any = None,
        validators: List[Callable[[Any], tuple[bool, Optional[str]]]] = None,
        on_change: List[ConfigChangeCallback] = None
    ):
        """
        Initialize the configuration value.
        
        Args:
            path: The configuration path for this value.
            value: The initial value.
            default: The default value to use if value is None.
            validators: List of validator functions for this value.
            on_change: List of callbacks to call when the value changes.
        """
        self._path = path
        self._value = value if value is not None else default
        self._default = default
        self._validators = validators or []
        self._on_change = on_change or []
        self._original_value = copy.deepcopy(self._value)
    
    @property
    def path(self) -> str:
        """Get the configuration path."""
        return self._path
    
    def get(self) -> Any:
        """
        Get the current value.
        
        Returns:
            The current value.
        """
        return self._value
    
    def get_value(self) -> Any:
        """
        Get the current value (alias for get).
        
        Returns:
            The current value.
        """
        return self._value
    
    def set_value(self, value: Any) -> None:
        """
        Set a new value.
        
        Args:
            value: The new value to set.
        """
        # Just delegate to set() - it already handles callbacks
        self.set(value)
    
    def is_modified(self) -> bool:
        """
        Check if the value has been modified from its original value.
        
        Returns:
            True if modified, False otherwise.
        """
        return self._value != self._original_value
    
    def reset(self) -> None:
        """Reset the value to its original value."""
        self._value = copy.deepcopy(self._original_value)
    
    def commit(self) -> None:
        """Commit the current value as the new original value."""
        self._original_value = copy.deepcopy(self._value)
    
    def on_change(self, callback: ConfigChangeCallback) -> None:
        """
        Add a change callback.
        
        Args:
            callback: The callback to add.
        """
        if callback not in self._on_change:
            self._on_change.append(callback)
    
    def remove_on_change(self, callback: ConfigChangeCallback) -> None:
        """
        Remove a change callback.
        
        Args:
            callback: The callback to remove.
        """
        if callback in self._on_change:
            self._on_change.remove(callback)
    
    def set(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Set a new value.
        
        Args:
            value: The new value to set.
            
        Returns:
            A tuple of (success, error_message).
        """
        # Validate the new value
        for validator in self._validators:
            is_valid, error = validator(value)
            if not is_valid:
                return False, error
        
        # If value is unchanged, do nothing
        if self._value == value:
            return True, None
        
        # Store the old value
        old_value = self._value
        
        # Set the new value
        self._value = value
        
        # Notify change listeners
        for callback in self._on_change:
            try:
                if self._path:
                    callback(self._path, value)
                else:
                    callback(value, old_value)
            except Exception as e:
                print(f"Error in configuration value change callback: {e}")
        
        return True, None
    
    def reset(self) -> None:
        """Reset the value to its original value."""
        self.set(self._original_value)
    
    def is_modified(self) -> bool:
        """
        Check if the value has been modified from its original value.
        
        Returns:
            True if the value has been modified, False otherwise.
        """
        return self._value != self._original_value
    
    def add_validator(self, validator: Callable[[Any], tuple[bool, Optional[str]]]) -> None:
        """
        Add a validator function.
        
        Args:
            validator: The validator function to add.
        """
        if validator not in self._validators:
            self._validators.append(validator)
    
    def add_change_listener(self, callback: ConfigChangeCallback) -> None:
        """
        Add a change listener.
        
        Args:
            callback: The callback to add.
        """
        if callback not in self._on_change:
            self._on_change.append(callback)
    
    def remove_change_listener(self, callback: ConfigChangeCallback) -> None:
        """
        Remove a change listener.
        
        Args:
            callback: The callback to remove.
        """
        if callback in self._on_change:
            self._on_change.remove(callback)
    
    def set_path(self, path: str) -> None:
        """
        Set the path for this configuration value.
        
        Args:
            path: The path to set.
        """
        self._path = path


class StringConfigValue(ConfigurationValue):
    """Configuration value that holds a string."""
    
    def __init__(
        self,
        path: str,
        value: Optional[str] = None,
        default: Optional[str] = "",
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        validators: List[Callable[[str], tuple[bool, Optional[str]]]] = None,
        on_change: List[ConfigChangeCallback] = None
    ):
        """
        Initialize the string configuration value.
        
        Args:
            path: The configuration path for this value.
            value: The initial value.
            default: The default value to use if value is None.
            min_length: The minimum allowed length.
            max_length: The maximum allowed length.
            pattern: A regular expression pattern to validate against.
            validators: List of validator functions for this value.
            on_change: List of callbacks to call when the value changes.
        """
        # Create validators based on parameters
        all_validators = validators or []
        
        # Add type validator
        all_validators.append(lambda v: (isinstance(v, str), "Value must be a string"))
        
        # Add length validators
        if min_length is not None:
            all_validators.append(lambda v: (len(v) >= min_length, f"Value must be at least {min_length} characters"))
        if max_length is not None:
            all_validators.append(lambda v: (len(v) <= max_length, f"Value must be at most {max_length} characters"))
        
        # Add pattern validator
        if pattern is not None:
            import re
            regex = re.compile(pattern)
            all_validators.append(lambda v: (regex.match(v) is not None, f"Value must match pattern {pattern}"))
        
        super().__init__(path, value, default, all_validators, on_change)
    
    def validate(self, value: str) -> bool:
        """
        Validate a string value.
        
        Args:
            value: The value to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        for validator in self._validators:
            is_valid, _ = validator(value)
            if not is_valid:
                return False
        return True
    
    def get(self) -> str:
        """
        Get the current value.
        
        Returns:
            The current string value.
        """
        value = super().get()
        return str(value) if value is not None else ""


class IntegerConfigValue(ConfigurationValue):
    """Configuration value that holds an integer."""
    
    def __init__(
        self,
        path: str,
        value: Optional[int] = None,
        default: int = 0,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        validators: List[Callable[[int], tuple[bool, Optional[str]]]] = None,
        on_change: List[ConfigChangeCallback] = None
    ):
        """
        Initialize the integer configuration value.
        
        Args:
            path: The configuration path for this value.
            value: The initial value.
            default: The default value to use if value is None.
            min_value: The minimum allowed value.
            max_value: The maximum allowed value.
            validators: List of validator functions for this value.
            on_change: List of callbacks to call when the value changes.
        """
        # Create validators based on parameters
        all_validators = validators or []
        
        # Add type validator
        all_validators.append(lambda v: (isinstance(v, int) and not isinstance(v, bool), "Value must be an integer"))
        
        # Add range validators
        if min_value is not None:
            all_validators.append(lambda v: (v >= min_value, f"Value must be at least {min_value}"))
        if max_value is not None:
            all_validators.append(lambda v: (v <= max_value, f"Value must be at most {max_value}"))
        
        super().__init__(path, value, default, all_validators, on_change)
    
    def validate(self, value: int) -> bool:
        """
        Validate an integer value.
        
        Args:
            value: The value to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        for validator in self._validators:
            is_valid, _ = validator(value)
            if not is_valid:
                return False
        return True
    
    def get(self) -> int:
        """
        Get the current value.
        
        Returns:
            The current integer value.
        """
        value = super().get()
        return int(value) if value is not None else 0


class BooleanConfigValue(ConfigurationValue):
    """Configuration value that holds a boolean."""
    
    def __init__(
        self,
        path: str,
        value: Optional[bool] = None,
        default: bool = False,
        validators: List[Callable[[bool], tuple[bool, Optional[str]]]] = None,
        on_change: List[ConfigChangeCallback] = None
    ):
        """
        Initialize the boolean configuration value.
        
        Args:
            path: The configuration path for this value.
            value: The initial value.
            default: The default value to use if value is None.
            validators: List of validator functions for this value.
            on_change: List of callbacks to call when the value changes.
        """
        # Create validators based on parameters
        all_validators = validators or []
        
        # Add type validator
        all_validators.append(lambda v: (isinstance(v, bool), "Value must be a boolean"))
        
        super().__init__(path, value, default, all_validators, on_change)
    
    def validate(self, value: bool) -> bool:
        """
        Validate a boolean value.
        
        Args:
            value: The value to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        for validator in self._validators:
            is_valid, _ = validator(value)
            if not is_valid:
                return False
        return True
    
    def get(self) -> bool:
        """
        Get the current value.
        
        Returns:
            The current boolean value.
        """
        value = super().get()
        return bool(value) if value is not None else False


class ListConfigValue(ConfigurationValue):
    """Configuration value that holds a list."""
    
    def __init__(
        self,
        path: str,
        value: Optional[List] = None,
        default: Optional[List] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        item_validator: Optional[Callable[[Any], tuple[bool, Optional[str]]]] = None,
        validators: List[Callable[[List], tuple[bool, Optional[str]]]] = None,
        on_change: List[ConfigChangeCallback] = None
    ):
        """
        Initialize the list configuration value.
        
        Args:
            path: The configuration path for this value.
            value: The initial value.
            default: The default value to use if value is None.
            min_length: The minimum allowed length.
            max_length: The maximum allowed length.
            item_validator: Validator function for list items.
            validators: List of validator functions for this value.
            on_change: List of callbacks to call when the value changes.
        """
        # Create validators based on parameters
        all_validators = validators or []
        
        # Add type validator
        all_validators.append(lambda v: (isinstance(v, list), "Value must be a list"))
        
        # Add length validators
        if min_length is not None:
            all_validators.append(lambda v: (len(v) >= min_length, f"List must have at least {min_length} items"))
        if max_length is not None:
            all_validators.append(lambda v: (len(v) <= max_length, f"List must have at most {max_length} items"))
        
        # Add item validator
        if item_validator is not None:
            all_validators.append(lambda v: self._validate_items(v, item_validator))
        
        # Set default to empty list if None
        if default is None:
            default = []
        
        super().__init__(path, value, default, all_validators, on_change)
    
    def validate(self, value: List) -> bool:
        """
        Validate a list value.
        
        Args:
            value: The value to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        for validator in self._validators:
            is_valid, _ = validator(value)
            if not is_valid:
                return False
        return True
    
    def _validate_items(self, value: List, validator: Callable[[Any], tuple[bool, Optional[str]]]) -> tuple[bool, Optional[str]]:
        """
        Validate all items in a list.
        
        Args:
            value: The list to validate.
            validator: The validator function to apply to each item.
            
        Returns:
            A tuple of (success, error_message).
        """
        for i, item in enumerate(value):
            is_valid, error = validator(item)
            if not is_valid:
                return False, f"Item {i}: {error}"
        return True, None
    
    def get(self) -> List:
        """
        Get the current value.
        
        Returns:
            The current list value.
        """
        value = super().get()
        return list(value) if value is not None else []
    
    def append(self, item: Any) -> tuple[bool, Optional[str]]:
        """
        Append an item to the list.
        
        Args:
            item: The item to append.
            
        Returns:
            A tuple of (success, error_message).
        """
        current = self.get()
        current.append(item)
        return self.set(current)
    
    def remove(self, item: Any) -> tuple[bool, Optional[str]]:
        """
        Remove an item from the list.
        
        Args:
            item: The item to remove.
            
        Returns:
            A tuple of (success, error_message).
        """
        current = self.get()
        if item in current:
            current.remove(item)
            return self.set(current)
        return False, "Item not found in list"


class DictConfigValue(ConfigurationValue):
    """Configuration value that holds a dictionary."""
    
    def __init__(
        self,
        path: str,
        value: Optional[Dict] = None,
        default: Optional[Dict] = None,
        key_validator: Optional[Callable[[Any], tuple[bool, Optional[str]]]] = None,
        value_validator: Optional[Callable[[Any], tuple[bool, Optional[str]]]] = None,
        validators: List[Callable[[Dict], tuple[bool, Optional[str]]]] = None,
        on_change: List[ConfigChangeCallback] = None
    ):
        """
        Initialize the dictionary configuration value.
        
        Args:
            path: The configuration path for this value.
            value: The initial value.
            default: The default value to use if value is None.
            key_validator: Validator function for dictionary keys.
            value_validator: Validator function for dictionary values.
            validators: List of validator functions for this value.
            on_change: List of callbacks to call when the value changes.
        """
        # Create validators based on parameters
        all_validators = validators or []
        
        # Add type validator
        all_validators.append(lambda v: (isinstance(v, dict), "Value must be a dictionary"))
        
        # Add key/value validators
        if key_validator is not None or value_validator is not None:
            all_validators.append(lambda v: self._validate_dict(v, key_validator, value_validator))
        
        # Set default to empty dict if None
        if default is None:
            default = {}
        
        super().__init__(path, value, default, all_validators, on_change)
    
    def validate(self, value: Dict) -> bool:
        """
        Validate a dictionary value.
        
        Args:
            value: The value to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        for validator in self._validators:
            is_valid, _ = validator(value)
            if not is_valid:
                return False
        return True
    
    def _validate_dict(
        self, 
        value: Dict, 
        key_validator: Optional[Callable[[Any], tuple[bool, Optional[str]]]], 
        value_validator: Optional[Callable[[Any], tuple[bool, Optional[str]]]]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate all keys and values in a dictionary.
        
        Args:
            value: The dictionary to validate.
            key_validator: The validator function to apply to each key.
            value_validator: The validator function to apply to each value.
            
        Returns:
            A tuple of (success, error_message).
        """
        for k, v in value.items():
            if key_validator is not None:
                is_valid, error = key_validator(k)
                if not is_valid:
                    return False, f"Key '{k}': {error}"
            
            if value_validator is not None:
                is_valid, error = value_validator(v)
                if not is_valid:
                    return False, f"Value for key '{k}': {error}"
        
        return True, None
    
    def get(self) -> Dict:
        """
        Get the current value.
        
        Returns:
            The current dictionary value.
        """
        value = super().get()
        return dict(value) if value is not None else {}
    
    def get_item(self, key: Any, default: Any = None) -> Any:
        """
        Get an item from the dictionary.
        
        Args:
            key: The key to get.
            default: The default value to return if the key doesn't exist.
            
        Returns:
            The value for the key, or the default if not found.
        """
        current = self.get()
        return current.get(key, default)
    
    def set_item(self, key: Any, value: Any) -> tuple[bool, Optional[str]]:
        """
        Set an item in the dictionary.
        
        Args:
            key: The key to set.
            value: The value to set.
            
        Returns:
            A tuple of (success, error_message).
        """
        current = self.get()
        current[key] = value
        return self.set(current)
    
    def remove_item(self, key: Any) -> tuple[bool, Optional[str]]:
        """
        Remove an item from the dictionary.
        
        Args:
            key: The key to remove.
            
        Returns:
            A tuple of (success, error_message).
        """
        current = self.get()
        if key in current:
            del current[key]
            return self.set(current)
        return False, f"Key '{key}' not found in dictionary"
