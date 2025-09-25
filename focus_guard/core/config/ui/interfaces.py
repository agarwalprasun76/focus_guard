"""
Configuration UI interfaces.

This module defines interfaces for binding configuration values to UI components
and generating forms based on configuration schemas.
"""

from typing import Any, Dict, List, Optional, Protocol, Type, TypeVar, Generic, Callable, Union
from abc import ABC, abstractmethod

from focus_guard.core.config.interfaces import ConfigPath, ConfigValue, ConfigSchema
from focus_guard.core.config.models.config_value import ConfigurationValue


class ConfigUIBinding(ABC):
    """
    Interface for binding configuration values to UI components.
    
    This interface defines methods for synchronizing values between
    configuration and UI components.
    """
    
    @abstractmethod
    def bind_to_config(self, config_value: ConfigurationValue) -> None:
        """
        Bind a UI component to a configuration value.
        
        Args:
            config_value: The configuration value to bind to.
        """
        pass
    
    @abstractmethod
    def update_from_config(self) -> None:
        """
        Update the UI component from the configuration value.
        """
        pass
    
    @abstractmethod
    def update_to_config(self) -> tuple[bool, Optional[str]]:
        """
        Update the configuration value from the UI component.
        
        Returns:
            A tuple of (success, error_message).
        """
        pass
    
    @abstractmethod
    def get_ui_component(self) -> Any:
        """
        Get the UI component.
        
        Returns:
            The UI component.
        """
        pass


class ConfigFormGenerator(ABC):
    """
    Interface for generating forms based on configuration schemas.
    
    This interface defines methods for creating UI forms from configuration
    schemas and handling form submission.
    """
    
    @abstractmethod
    def generate_form(self, schema: ConfigSchema) -> Any:
        """
        Generate a form from a configuration schema.
        
        Args:
            schema: The configuration schema.
            
        Returns:
            A form component.
        """
        pass
    
    @abstractmethod
    def bind_form(self, form: Any, config_data: Dict[str, Any]) -> List[ConfigUIBinding]:
        """
        Bind a form to configuration data.
        
        Args:
            form: The form component.
            config_data: The configuration data.
            
        Returns:
            A list of UI bindings.
        """
        pass
    
    @abstractmethod
    def validate_form(self, form: Any) -> tuple[bool, Dict[str, str]]:
        """
        Validate a form.
        
        Args:
            form: The form component.
            
        Returns:
            A tuple of (is_valid, error_messages).
        """
        pass
    
    @abstractmethod
    def get_form_data(self, form: Any) -> Dict[str, Any]:
        """
        Get data from a form.
        
        Args:
            form: The form component.
            
        Returns:
            The form data.
        """
        pass


class ConfigUIController(ABC):
    """
    Interface for controlling configuration UI.
    
    This interface defines methods for managing configuration UI components
    and handling user interactions.
    """
    
    @abstractmethod
    def register_binding(self, path: ConfigPath, binding: ConfigUIBinding) -> None:
        """
        Register a UI binding for a configuration path.
        
        Args:
            path: The configuration path.
            binding: The UI binding.
        """
        pass
    
    @abstractmethod
    def unregister_binding(self, path: ConfigPath, binding: Optional[ConfigUIBinding] = None) -> None:
        """
        Unregister a UI binding for a configuration path.
        
        Args:
            path: The configuration path.
            binding: The UI binding to unregister. If None, unregister all bindings for the path.
        """
        pass
    
    @abstractmethod
    def update_all_bindings(self) -> None:
        """
        Update all UI bindings from their configuration values.
        """
        pass
    
    @abstractmethod
    def save_all_bindings(self) -> tuple[bool, Dict[ConfigPath, str]]:
        """
        Save all UI bindings to their configuration values.
        
        Returns:
            A tuple of (success, error_messages).
        """
        pass
    
    @abstractmethod
    def create_form(self, schema: ConfigSchema) -> Any:
        """
        Create a form for a configuration schema.
        
        Args:
            schema: The configuration schema.
            
        Returns:
            A form component.
        """
        pass
    
    @abstractmethod
    def handle_form_submission(self, form: Any) -> tuple[bool, Dict[str, str]]:
        """
        Handle a form submission.
        
        Args:
            form: The form component.
            
        Returns:
            A tuple of (success, error_messages).
        """
        pass


class ConfigUIMetadata:
    """
    Metadata for configuration UI components.
    
    This class provides metadata for generating UI components from configuration
    values, including labels, descriptions, and UI hints.
    """
    
    def __init__(
        self,
        label: str,
        description: str = "",
        ui_type: str = "auto",
        ui_props: Optional[Dict[str, Any]] = None,
        order: int = 0,
        group: str = "",
        visible: bool = True,
        read_only: bool = False,
        advanced: bool = False
    ):
        """
        Initialize the configuration UI metadata.
        
        Args:
            label: The label for the UI component.
            description: The description for the UI component.
            ui_type: The type of UI component to use.
            ui_props: Additional properties for the UI component.
            order: The order of the UI component in a form.
            group: The group of the UI component in a form.
            visible: Whether the UI component is visible.
            read_only: Whether the UI component is read-only.
            advanced: Whether the UI component is for advanced settings.
        """
        self.label = label
        self.description = description
        self.ui_type = ui_type
        self.ui_props = ui_props or {}
        self.order = order
        self.group = group
        self.visible = visible
        self.read_only = read_only
        self.advanced = advanced


class ConfigUIHint:
    """
    UI hints for configuration values.
    
    This class provides hints for generating UI components from configuration
    values, including suggested UI component types and properties.
    """
    
    # Common UI component types
    TEXT = "text"
    PASSWORD = "password"
    NUMBER = "number"
    CHECKBOX = "checkbox"
    SWITCH = "switch"
    SELECT = "select"
    RADIO = "radio"
    SLIDER = "slider"
    COLOR = "color"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    FILE = "file"
    TEXTAREA = "textarea"
    
    @staticmethod
    def for_string(
        multiline: bool = False,
        password: bool = False,
        options: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get UI hints for a string value.
        
        Args:
            multiline: Whether the string is multiline.
            password: Whether the string is a password.
            options: Optional list of valid options.
            
        Returns:
            UI hints for the string value.
        """
        if options:
            return {"ui_type": ConfigUIHint.SELECT, "ui_props": {"options": options}}
        elif multiline:
            return {"ui_type": ConfigUIHint.TEXTAREA}
        elif password:
            return {"ui_type": ConfigUIHint.PASSWORD}
        else:
            return {"ui_type": ConfigUIHint.TEXT}
    
    @staticmethod
    def for_number(
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        step: float = 1,
        use_slider: bool = False
    ) -> Dict[str, Any]:
        """
        Get UI hints for a number value.
        
        Args:
            min_value: The minimum value.
            max_value: The maximum value.
            step: The step value.
            use_slider: Whether to use a slider.
            
        Returns:
            UI hints for the number value.
        """
        props = {}
        if min_value is not None:
            props["min"] = min_value
        if max_value is not None:
            props["max"] = max_value
        props["step"] = step
        
        if use_slider and min_value is not None and max_value is not None:
            return {"ui_type": ConfigUIHint.SLIDER, "ui_props": props}
        else:
            return {"ui_type": ConfigUIHint.NUMBER, "ui_props": props}
    
    @staticmethod
    def for_boolean(use_switch: bool = False) -> Dict[str, Any]:
        """
        Get UI hints for a boolean value.
        
        Args:
            use_switch: Whether to use a switch instead of a checkbox.
            
        Returns:
            UI hints for the boolean value.
        """
        if use_switch:
            return {"ui_type": ConfigUIHint.SWITCH}
        else:
            return {"ui_type": ConfigUIHint.CHECKBOX}
    
    @staticmethod
    def for_list(item_type: str = TEXT) -> Dict[str, Any]:
        """
        Get UI hints for a list value.
        
        Args:
            item_type: The UI type for list items.
            
        Returns:
            UI hints for the list value.
        """
        return {"ui_type": "list", "ui_props": {"item_type": item_type}}
    
    @staticmethod
    def for_dict(key_type: str = TEXT, value_type: str = TEXT) -> Dict[str, Any]:
        """
        Get UI hints for a dictionary value.
        
        Args:
            key_type: The UI type for dictionary keys.
            value_type: The UI type for dictionary values.
            
        Returns:
            UI hints for the dictionary value.
        """
        return {
            "ui_type": "dict", 
            "ui_props": {
                "key_type": key_type,
                "value_type": value_type
            }
        }
