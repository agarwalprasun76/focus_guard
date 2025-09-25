"""
Configuration UI components.

This module provides UI components for configuration settings,
including bindings for different UI frameworks.
"""

from typing import Any, Dict, List, Optional, Callable, Type, Union
import threading

from focus_guard.core.config.interfaces import ConfigPath, ConfigChangeCallback
from focus_guard.core.config.models.config_value import ConfigurationValue
from focus_guard.core.config.ui.interfaces import ConfigUIBinding, ConfigUIMetadata


class ConfigUIComponent:
    """
    Base class for configuration UI components.
    
    This class provides common functionality for UI components that
    display and edit configuration values.
    """
    
    def __init__(
        self,
        name: str,
        label: str,
        description: str = "",
        read_only: bool = False,
        on_change: Optional[Callable[[Any], None]] = None
    ):
        """
        Initialize the UI component.
        
        Args:
            name: The component name.
            label: The component label.
            description: The component description.
            read_only: Whether the component is read-only.
            on_change: Callback to call when the value changes.
        """
        self._name = name
        self._label = label
        self._description = description
        self._read_only = read_only
        self._on_change = on_change
        self._value = None
        self._error = None
        self._lock = threading.RLock()
    
    def get_name(self) -> str:
        """
        Get the component name.
        
        Returns:
            The component name.
        """
        return self._name
    
    def get_label(self) -> str:
        """
        Get the component label.
        
        Returns:
            The component label.
        """
        return self._label
    
    def get_description(self) -> str:
        """
        Get the component description.
        
        Returns:
            The component description.
        """
        return self._description
    
    def is_read_only(self) -> bool:
        """
        Check if the component is read-only.
        
        Returns:
            True if the component is read-only, False otherwise.
        """
        return self._read_only
    
    def get_value(self) -> Any:
        """
        Get the component value.
        
        Returns:
            The component value.
        """
        with self._lock:
            return self._value
    
    def set_value(self, value: Any) -> None:
        """
        Set the component value.
        
        Args:
            value: The value to set.
        """
        with self._lock:
            if self._value != value:
                self._value = value
                self._error = None
                
                # Notify change listeners
                if self._on_change:
                    try:
                        self._on_change(value)
                    except Exception as e:
                        print(f"Error in UI component change callback: {e}")
    
    def get_error(self) -> Optional[str]:
        """
        Get the component error.
        
        Returns:
            The component error, or None if there is no error.
        """
        with self._lock:
            return self._error
    
    def set_error(self, error: Optional[str]) -> None:
        """
        Set the component error.
        
        Args:
            error: The error to set, or None to clear the error.
        """
        with self._lock:
            self._error = error
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the component value.
        
        Returns:
            A tuple of (is_valid, error_message).
        """
        # Base implementation always validates
        return True, None


class ConfigUIBinding(ConfigUIBinding):
    """
    Base implementation of the configuration UI binding.
    
    This class provides a binding between a configuration value and a UI component.
    """
    
    def __init__(
        self,
        component: ConfigUIComponent,
        config_value: ConfigurationValue,
        path: str
    ):
        """
        Initialize the UI binding.
        
        Args:
            component: The UI component.
            config_value: The configuration value.
            path: The configuration path.
        """
        self._component = component
        self._config_value = config_value
        self._path = path
        
        # Set up change listeners
        self._component_change_listener = lambda value: self._on_component_change(value)
        self._config_change_listener = lambda path, value: self._on_config_change(path, value)
        
        # Bind the component to the configuration value
        self.bind_to_config(config_value)
    
    def bind_to_config(self, config_value: ConfigurationValue) -> None:
        """
        Bind a UI component to a configuration value.
        
        Args:
            config_value: The configuration value to bind to.
        """
        self._config_value = config_value
        
        # Add change listeners
        self._config_value.add_change_listener(self._config_change_listener)
        
        # Update the component from the configuration value
        self.update_from_config()
    
    def update_from_config(self) -> None:
        """
        Update the UI component from the configuration value.
        """
        # Get the value from the configuration
        value = self._config_value.get()
        
        # Update the component
        self._component.set_value(value)
    
    def update_to_config(self) -> tuple[bool, Optional[str]]:
        """
        Update the configuration value from the UI component.
        
        Returns:
            A tuple of (success, error_message).
        """
        # Validate the component
        is_valid, error = self._component.validate()
        if not is_valid:
            return False, error
        
        # Get the value from the component
        value = self._component.get_value()
        
        # Update the configuration value
        success, error = self._config_value.set(value)
        
        # Update the component error
        self._component.set_error(error)
        
        return success, error
    
    def get_ui_component(self) -> Any:
        """
        Get the UI component.
        
        Returns:
            The UI component.
        """
        return self._component
    
    def get_path(self) -> str:
        """
        Get the configuration path.
        
        Returns:
            The configuration path.
        """
        return self._path
    
    def _on_component_change(self, value: Any) -> None:
        """
        Handle component value changes.
        
        Args:
            value: The new value.
        """
        # Update the configuration value
        success, error = self._config_value.set(value)
        
        # Update the component error
        self._component.set_error(error)
    
    def _on_config_change(self, path: str, value: Any) -> None:
        """
        Handle configuration value changes.
        
        Args:
            path: The configuration path.
            value: The new value.
        """
        # Update the component
        self._component.set_value(value)


# Concrete UI components for different value types

class TextComponent(ConfigUIComponent):
    """UI component for text values."""
    
    def __init__(
        self,
        name: str,
        label: str,
        description: str = "",
        read_only: bool = False,
        on_change: Optional[Callable[[str], None]] = None,
        multiline: bool = False,
        password: bool = False,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None
    ):
        """
        Initialize the text component.
        
        Args:
            name: The component name.
            label: The component label.
            description: The component description.
            read_only: Whether the component is read-only.
            on_change: Callback to call when the value changes.
            multiline: Whether the text is multiline.
            password: Whether the text is a password.
            min_length: The minimum allowed length.
            max_length: The maximum allowed length.
            pattern: A regular expression pattern to validate against.
        """
        super().__init__(name, label, description, read_only, on_change)
        self._multiline = multiline
        self._password = password
        self._min_length = min_length
        self._max_length = max_length
        self._pattern = pattern
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the component value.
        
        Returns:
            A tuple of (is_valid, error_message).
        """
        value = self.get_value()
        
        # Check if the value is a string
        if not isinstance(value, str):
            return False, "Value must be a string"
        
        # Check length constraints
        if self._min_length is not None and len(value) < self._min_length:
            return False, f"Value must be at least {self._min_length} characters"
        
        if self._max_length is not None and len(value) > self._max_length:
            return False, f"Value must be at most {self._max_length} characters"
        
        # Check pattern constraint
        if self._pattern is not None:
            import re
            if not re.match(self._pattern, value):
                return False, f"Value must match pattern {self._pattern}"
        
        return True, None


class NumberComponent(ConfigUIComponent):
    """UI component for number values."""
    
    def __init__(
        self,
        name: str,
        label: str,
        description: str = "",
        read_only: bool = False,
        on_change: Optional[Callable[[Union[int, float]], None]] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        step: Union[int, float] = 1,
        is_integer: bool = True
    ):
        """
        Initialize the number component.
        
        Args:
            name: The component name.
            label: The component label.
            description: The component description.
            read_only: Whether the component is read-only.
            on_change: Callback to call when the value changes.
            min_value: The minimum allowed value.
            max_value: The maximum allowed value.
            step: The step value.
            is_integer: Whether the value is an integer.
        """
        super().__init__(name, label, description, read_only, on_change)
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._is_integer = is_integer
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the component value.
        
        Returns:
            A tuple of (is_valid, error_message).
        """
        value = self.get_value()
        
        # Check if the value is a number
        if not isinstance(value, (int, float)) or (self._is_integer and not isinstance(value, int)):
            return False, "Value must be a number"
        
        # Check range constraints
        if self._min_value is not None and value < self._min_value:
            return False, f"Value must be at least {self._min_value}"
        
        if self._max_value is not None and value > self._max_value:
            return False, f"Value must be at most {self._max_value}"
        
        return True, None


class BooleanComponent(ConfigUIComponent):
    """UI component for boolean values."""
    
    def __init__(
        self,
        name: str,
        label: str,
        description: str = "",
        read_only: bool = False,
        on_change: Optional[Callable[[bool], None]] = None,
        use_switch: bool = False
    ):
        """
        Initialize the boolean component.
        
        Args:
            name: The component name.
            label: The component label.
            description: The component description.
            read_only: Whether the component is read-only.
            on_change: Callback to call when the value changes.
            use_switch: Whether to use a switch instead of a checkbox.
        """
        super().__init__(name, label, description, read_only, on_change)
        self._use_switch = use_switch
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the component value.
        
        Returns:
            A tuple of (is_valid, error_message).
        """
        value = self.get_value()
        
        # Check if the value is a boolean
        if not isinstance(value, bool):
            return False, "Value must be a boolean"
        
        return True, None


class SelectComponent(ConfigUIComponent):
    """UI component for selection values."""
    
    def __init__(
        self,
        name: str,
        label: str,
        description: str = "",
        read_only: bool = False,
        on_change: Optional[Callable[[Any], None]] = None,
        options: List[Any] = None,
        option_labels: Optional[Dict[Any, str]] = None,
        multiple: bool = False
    ):
        """
        Initialize the select component.
        
        Args:
            name: The component name.
            label: The component label.
            description: The component description.
            read_only: Whether the component is read-only.
            on_change: Callback to call when the value changes.
            options: The available options.
            option_labels: Labels for the options.
            multiple: Whether multiple selection is allowed.
        """
        super().__init__(name, label, description, read_only, on_change)
        self._options = options or []
        self._option_labels = option_labels or {}
        self._multiple = multiple
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the component value.
        
        Returns:
            A tuple of (is_valid, error_message).
        """
        value = self.get_value()
        
        if self._multiple:
            # Check if the value is a list
            if not isinstance(value, list):
                return False, "Value must be a list"
            
            # Check if all items are valid options
            for item in value:
                if item not in self._options:
                    return False, f"Invalid option: {item}"
        else:
            # Check if the value is a valid option
            if value not in self._options:
                return False, f"Invalid option: {value}"
        
        return True, None
    
    def get_options(self) -> List[Any]:
        """
        Get the available options.
        
        Returns:
            The available options.
        """
        return self._options
    
    def get_option_label(self, option: Any) -> str:
        """
        Get the label for an option.
        
        Args:
            option: The option.
            
        Returns:
            The label for the option.
        """
        return self._option_labels.get(option, str(option))


class ListComponent(ConfigUIComponent):
    """UI component for list values."""
    
    def __init__(
        self,
        name: str,
        label: str,
        description: str = "",
        read_only: bool = False,
        on_change: Optional[Callable[[List[Any]], None]] = None,
        item_component_factory: Callable[[str, str], ConfigUIComponent] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ):
        """
        Initialize the list component.
        
        Args:
            name: The component name.
            label: The component label.
            description: The component description.
            read_only: Whether the component is read-only.
            on_change: Callback to call when the value changes.
            item_component_factory: Factory for creating item components.
            min_length: The minimum allowed length.
            max_length: The maximum allowed length.
        """
        super().__init__(name, label, description, read_only, on_change)
        self._item_component_factory = item_component_factory
        self._min_length = min_length
        self._max_length = max_length
        self._item_components: List[ConfigUIComponent] = []
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the component value.
        
        Returns:
            A tuple of (is_valid, error_message).
        """
        value = self.get_value()
        
        # Check if the value is a list
        if not isinstance(value, list):
            return False, "Value must be a list"
        
        # Check length constraints
        if self._min_length is not None and len(value) < self._min_length:
            return False, f"List must have at least {self._min_length} items"
        
        if self._max_length is not None and len(value) > self._max_length:
            return False, f"List must have at most {self._max_length} items"
        
        # Validate each item
        for i, item_component in enumerate(self._item_components):
            is_valid, error = item_component.validate()
            if not is_valid:
                return False, f"Item {i}: {error}"
        
        return True, None
    
    def get_item_components(self) -> List[ConfigUIComponent]:
        """
        Get the item components.
        
        Returns:
            The item components.
        """
        return self._item_components
    
    def add_item(self, value: Any = None) -> ConfigUIComponent:
        """
        Add an item to the list.
        
        Args:
            value: The item value.
            
        Returns:
            The item component.
        """
        # Create a new item component
        index = len(self._item_components)
        item_name = f"{self._name}_{index}"
        item_label = f"Item {index + 1}"
        
        item_component = self._item_component_factory(item_name, item_label)
        
        # Set the item value
        if value is not None:
            item_component.set_value(value)
        
        # Add the item component
        self._item_components.append(item_component)
        
        # Update the list value
        self._update_value_from_items()
        
        return item_component
    
    def remove_item(self, index: int) -> None:
        """
        Remove an item from the list.
        
        Args:
            index: The item index.
        """
        if 0 <= index < len(self._item_components):
            # Remove the item component
            del self._item_components[index]
            
            # Update the list value
            self._update_value_from_items()
    
    def _update_value_from_items(self) -> None:
        """Update the list value from the item components."""
        value = [item.get_value() for item in self._item_components]
        self.set_value(value)
    
    def set_value(self, value: List[Any]) -> None:
        """
        Set the component value.
        
        Args:
            value: The value to set.
        """
        # Clear existing item components
        self._item_components = []
        
        # Create new item components
        if isinstance(value, list):
            for item_value in value:
                self.add_item(item_value)
        
        # Call the parent method
        super().set_value(value)


class DictComponent(ConfigUIComponent):
    """UI component for dictionary values."""
    
    def __init__(
        self,
        name: str,
        label: str,
        description: str = "",
        read_only: bool = False,
        on_change: Optional[Callable[[Dict[Any, Any]], None]] = None,
        key_component_factory: Callable[[str, str], ConfigUIComponent] = None,
        value_component_factory: Callable[[str, str], ConfigUIComponent] = None
    ):
        """
        Initialize the dictionary component.
        
        Args:
            name: The component name.
            label: The component label.
            description: The component description.
            read_only: Whether the component is read-only.
            on_change: Callback to call when the value changes.
            key_component_factory: Factory for creating key components.
            value_component_factory: Factory for creating value components.
        """
        super().__init__(name, label, description, read_only, on_change)
        self._key_component_factory = key_component_factory
        self._value_component_factory = value_component_factory
        self._key_components: Dict[str, ConfigUIComponent] = {}
        self._value_components: Dict[str, ConfigUIComponent] = {}
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the component value.
        
        Returns:
            A tuple of (is_valid, error_message).
        """
        value = self.get_value()
        
        # Check if the value is a dictionary
        if not isinstance(value, dict):
            return False, "Value must be a dictionary"
        
        # Validate each key and value
        for entry_id, key_component in self._key_components.items():
            # Validate the key
            is_valid, error = key_component.validate()
            if not is_valid:
                return False, f"Key: {error}"
            
            # Validate the value
            value_component = self._value_components.get(entry_id)
            if value_component:
                is_valid, error = value_component.validate()
                if not is_valid:
                    return False, f"Value for key '{key_component.get_value()}': {error}"
        
        return True, None
    
    def get_entries(self) -> List[tuple[str, ConfigUIComponent, ConfigUIComponent]]:
        """
        Get the dictionary entries.
        
        Returns:
            A list of (entry_id, key_component, value_component) tuples.
        """
        entries = []
        
        for entry_id, key_component in self._key_components.items():
            value_component = self._value_components.get(entry_id)
            if value_component:
                entries.append((entry_id, key_component, value_component))
        
        return entries
    
    def add_entry(self, key: Any = None, value: Any = None) -> str:
        """
        Add an entry to the dictionary.
        
        Args:
            key: The entry key.
            value: The entry value.
            
        Returns:
            The entry ID.
        """
        # Create a unique entry ID
        import uuid
        entry_id = str(uuid.uuid4())
        
        # Create key and value components
        key_name = f"{self._name}_key_{entry_id}"
        key_label = "Key"
        key_component = self._key_component_factory(key_name, key_label)
        
        value_name = f"{self._name}_value_{entry_id}"
        value_label = "Value"
        value_component = self._value_component_factory(value_name, value_label)
        
        # Set key and value
        if key is not None:
            key_component.set_value(key)
        
        if value is not None:
            value_component.set_value(value)
        
        # Add the components
        self._key_components[entry_id] = key_component
        self._value_components[entry_id] = value_component
        
        # Update the dictionary value
        self._update_value_from_entries()
        
        return entry_id
    
    def remove_entry(self, entry_id: str) -> None:
        """
        Remove an entry from the dictionary.
        
        Args:
            entry_id: The entry ID.
        """
        if entry_id in self._key_components:
            # Remove the components
            del self._key_components[entry_id]
            
            if entry_id in self._value_components:
                del self._value_components[entry_id]
            
            # Update the dictionary value
            self._update_value_from_entries()
    
    def _update_value_from_entries(self) -> None:
        """Update the dictionary value from the entry components."""
        value = {}
        
        for entry_id, key_component in self._key_components.items():
            key = key_component.get_value()
            
            value_component = self._value_components.get(entry_id)
            if value_component:
                value[key] = value_component.get_value()
        
        self.set_value(value)
    
    def set_value(self, value: Dict[Any, Any]) -> None:
        """
        Set the component value.
        
        Args:
            value: The value to set.
        """
        # Clear existing components
        self._key_components = {}
        self._value_components = {}
        
        # Create new components
        if isinstance(value, dict):
            for key, val in value.items():
                self.add_entry(key, val)
        
        # Call the parent method
        super().set_value(value)
