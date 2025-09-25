"""
Configuration UI controller.

This module provides a controller for managing configuration UI components
and handling user interactions.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Type
import threading

from focus_guard.core.config.interfaces import ConfigPath, ConfigSchema, ConfigurationManager
from focus_guard.core.config.ui.interfaces import ConfigUIBinding, ConfigFormGenerator, ConfigUIController


class DefaultConfigUIController(ConfigUIController):
    """
    Default implementation of the configuration UI controller.
    
    This class manages UI bindings and handles form interactions, providing
    a central point for coordinating between configuration values and UI components.
    """
    
    def __init__(
        self, 
        config_manager: ConfigurationManager,
        form_generator: ConfigFormGenerator
    ):
        """
        Initialize the UI controller.
        
        Args:
            config_manager: The configuration manager.
            form_generator: The form generator.
        """
        self._config_manager = config_manager
        self._form_generator = form_generator
        self._bindings: Dict[ConfigPath, List[ConfigUIBinding]] = {}
        self._forms: Dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def register_binding(self, path: ConfigPath, binding: ConfigUIBinding) -> None:
        """
        Register a UI binding for a configuration path.
        
        Args:
            path: The configuration path.
            binding: The UI binding.
        """
        with self._lock:
            if path not in self._bindings:
                self._bindings[path] = []
            
            if binding not in self._bindings[path]:
                self._bindings[path].append(binding)
                
                # Subscribe to configuration changes
                self._config_manager.subscribe(path, self._on_config_change)
    
    def unregister_binding(self, path: ConfigPath, binding: Optional[ConfigUIBinding] = None) -> None:
        """
        Unregister a UI binding for a configuration path.
        
        Args:
            path: The configuration path.
            binding: The UI binding to unregister. If None, unregister all bindings for the path.
        """
        with self._lock:
            if path not in self._bindings:
                return
            
            if binding is None:
                # Unregister all bindings for the path
                self._bindings[path] = []
                
                # Unsubscribe from configuration changes
                self._config_manager.unsubscribe(path, self._on_config_change)
            else:
                # Unregister a specific binding
                if binding in self._bindings[path]:
                    self._bindings[path].remove(binding)
                
                # If no more bindings for this path, unsubscribe from configuration changes
                if not self._bindings[path]:
                    self._config_manager.unsubscribe(path, self._on_config_change)
    
    def _on_config_change(self, path: ConfigPath, value: Any) -> None:
        """
        Handle configuration changes.
        
        Args:
            path: The configuration path.
            value: The new value.
        """
        with self._lock:
            if path in self._bindings:
                for binding in self._bindings[path]:
                    binding.update_from_config()
    
    def update_all_bindings(self) -> None:
        """
        Update all UI bindings from their configuration values.
        """
        with self._lock:
            for path, bindings in self._bindings.items():
                for binding in bindings:
                    binding.update_from_config()
    
    def save_all_bindings(self) -> tuple[bool, Dict[ConfigPath, str]]:
        """
        Save all UI bindings to their configuration values.
        
        Returns:
            A tuple of (success, error_messages).
        """
        success = True
        error_messages = {}
        
        with self._lock:
            for path, bindings in self._bindings.items():
                for binding in bindings:
                    binding_success, error = binding.update_to_config()
                    if not binding_success:
                        success = False
                        error_messages[path] = error
        
        return success, error_messages
    
    def create_form(self, schema: ConfigSchema) -> Any:
        """
        Create a form for a configuration schema.
        
        Args:
            schema: The configuration schema.
            
        Returns:
            A form component.
        """
        # Generate the form
        form = self._form_generator.generate_form(schema)
        
        # Store the form
        schema_name = schema.get_name()
        self._forms[schema_name] = form
        
        return form
    
    def bind_form(self, schema_name: str) -> List[ConfigUIBinding]:
        """
        Bind a form to configuration data.
        
        Args:
            schema_name: The name of the schema.
            
        Returns:
            A list of UI bindings.
        """
        if schema_name not in self._forms:
            return []
        
        # Get the form
        form = self._forms[schema_name]
        
        # Get the configuration data
        config_data = self._config_manager.get_value(schema_name, {})
        
        # Bind the form
        bindings = self._form_generator.bind_form(form, config_data)
        
        # Register the bindings
        for binding in bindings:
            self.register_binding(f"{schema_name}.{binding.get_path()}", binding)
        
        return bindings
    
    def handle_form_submission(self, form: Any) -> tuple[bool, Dict[str, str]]:
        """
        Handle a form submission.
        
        Args:
            form: The form component.
            
        Returns:
            A tuple of (success, error_messages).
        """
        # Validate the form
        is_valid, error_messages = self._form_generator.validate_form(form)
        
        if not is_valid:
            return False, error_messages
        
        # Get the form data
        form_data = self._form_generator.get_form_data(form)
        
        # Find the schema name
        schema_name = None
        for name, stored_form in self._forms.items():
            if stored_form == form:
                schema_name = name
                break
        
        if schema_name is None:
            return False, {"form": "Form not registered"}
        
        # Update the configuration
        success = self._config_manager.set_value(schema_name, form_data)
        
        if not success:
            return False, {"form": "Failed to update configuration"}
        
        # Save the configuration
        save_success = self._config_manager.save()
        
        if not save_success:
            return False, {"form": "Failed to save configuration"}
        
        return True, {}
