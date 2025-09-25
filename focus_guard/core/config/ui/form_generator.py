"""
Configuration form generator.

This module provides utilities for generating UI forms based on configuration schemas.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Callable, Union
import inspect
from dataclasses import is_dataclass, fields

from focus_guard.core.config.interfaces import ConfigSchema, ConfigPath
from focus_guard.core.config.schema import ConfigValueSchema, ConfigSectionSchema, DataclassConfigSchema
from focus_guard.core.config.models.config_value import ConfigurationValue
from focus_guard.core.config.ui.interfaces import ConfigFormGenerator, ConfigUIBinding, ConfigUIMetadata, ConfigUIHint


class DefaultConfigFormGenerator(ConfigFormGenerator):
    """
    Default implementation of the configuration form generator.
    
    This class generates UI forms based on configuration schemas and
    provides methods for binding form components to configuration values.
    """
    
    def __init__(self, ui_factory: Any):
        """
        Initialize the form generator.
        
        Args:
            ui_factory: A factory for creating UI components.
        """
        self._ui_factory = ui_factory
        self._bindings: Dict[str, ConfigUIBinding] = {}
    
    def generate_form(self, schema: ConfigSchema) -> Any:
        """
        Generate a form from a configuration schema.
        
        Args:
            schema: The configuration schema.
            
        Returns:
            A form component.
        """
        # Create a form container
        form = self._ui_factory.create_form(schema.get_name(), schema.get_description())
        
        # Generate form fields based on schema type
        if isinstance(schema, ConfigValueSchema):
            self._generate_value_field(form, schema, schema.get_name())
        elif isinstance(schema, ConfigSectionSchema):
            self._generate_section_fields(form, schema)
        elif isinstance(schema, DataclassConfigSchema):
            self._generate_dataclass_fields(form, schema)
        
        return form
    
    def _generate_value_field(self, form: Any, schema: ConfigValueSchema, name: str, path: str = "") -> None:
        """
        Generate a form field for a value schema.
        
        Args:
            form: The form component.
            schema: The value schema.
            name: The field name.
            path: The field path.
        """
        # Get UI metadata from schema
        metadata = self._get_ui_metadata(schema, name)
        
        # Skip if not visible
        if not metadata.visible:
            return
        
        # Determine field type and properties
        field_type = metadata.ui_type
        field_props = metadata.ui_props
        
        if field_type == "auto":
            # Auto-detect field type based on schema
            field_info = self._get_field_info_from_schema(schema)
            field_type = field_info.get("ui_type", ConfigUIHint.TEXT)
            field_props.update(field_info.get("ui_props", {}))
        
        # Create the field
        field_path = f"{path}.{name}" if path else name
        field = self._ui_factory.create_field(
            form=form,
            name=name,
            label=metadata.label,
            description=metadata.description,
            field_type=field_type,
            field_props=field_props,
            read_only=metadata.read_only,
            advanced=metadata.advanced,
            order=metadata.order,
            group=metadata.group
        )
        
        # Store the field with its path
        self._bindings[field_path] = field
    
    def _generate_section_fields(self, form: Any, schema: ConfigSectionSchema, path: str = "") -> None:
        """
        Generate form fields for a section schema.
        
        Args:
            form: The form component.
            schema: The section schema.
            path: The section path.
        """
        # Get section path
        section_path = schema.get_name() if not path else f"{path}.{schema.get_name()}"
        
        # Create a section container if needed
        if schema.get_description():
            section = self._ui_factory.create_section(
                form=form,
                name=schema.get_name(),
                label=schema.get_name(),
                description=schema.get_description()
            )
        else:
            section = form
        
        # Generate fields for each value schema
        for name, value_schema in schema.get_value_schemas().items():
            self._generate_value_field(section, value_schema, name, section_path)
        
        # Generate fields for each subsection schema
        for name, subsection_schema in schema.get_section_schemas().items():
            self._generate_section_fields(section, subsection_schema, section_path)
    
    def _generate_dataclass_fields(self, form: Any, schema: DataclassConfigSchema, path: str = "") -> None:
        """
        Generate form fields for a dataclass schema.
        
        Args:
            form: The form component.
            schema: The dataclass schema.
            path: The section path.
        """
        # Get dataclass type
        dataclass_type = schema.get_dataclass_type()
        
        # Get section path
        section_path = schema.get_name() if not path else f"{path}.{schema.get_name()}"
        
        # Create a section container if needed
        if schema.get_description():
            section = self._ui_factory.create_section(
                form=form,
                name=schema.get_name(),
                label=schema.get_name(),
                description=schema.get_description()
            )
        else:
            section = form
        
        # Generate fields for each dataclass field
        for field_obj in fields(dataclass_type):
            field_name = field_obj.name
            
            # Skip private fields
            if field_name.startswith('_'):
                continue
            
            # Get field metadata
            metadata = self._get_ui_metadata_from_field(field_obj, field_name)
            
            # Skip if not visible
            if not metadata.visible:
                continue
            
            # Determine field type and properties
            field_type = metadata.ui_type
            field_props = metadata.ui_props
            
            if field_type == "auto":
                # Auto-detect field type based on field type
                field_info = self._get_field_info_from_type(field_obj.type)
                field_type = field_info.get("ui_type", ConfigUIHint.TEXT)
                field_props.update(field_info.get("ui_props", {}))
            
            # Create the field
            field_path = f"{section_path}.{field_name}"
            field = self._ui_factory.create_field(
                form=section,
                name=field_name,
                label=metadata.label,
                description=metadata.description,
                field_type=field_type,
                field_props=field_props,
                read_only=metadata.read_only,
                advanced=metadata.advanced,
                order=metadata.order,
                group=metadata.group
            )
            
            # Store the field with its path
            self._bindings[field_path] = field
    
    def _get_ui_metadata(self, schema: ConfigValueSchema, name: str) -> ConfigUIMetadata:
        """
        Get UI metadata from a schema.
        
        Args:
            schema: The schema.
            name: The field name.
            
        Returns:
            UI metadata for the field.
        """
        # Check if the schema has UI metadata
        if hasattr(schema, "ui_metadata") and isinstance(schema.ui_metadata, ConfigUIMetadata):
            return schema.ui_metadata
        
        # Create default metadata
        return ConfigUIMetadata(
            label=name.replace('_', ' ').title(),
            description=schema.get_description() or ""
        )
    
    def _get_ui_metadata_from_field(self, field_obj: Any, name: str) -> ConfigUIMetadata:
        """
        Get UI metadata from a dataclass field.
        
        Args:
            field_obj: The field object.
            name: The field name.
            
        Returns:
            UI metadata for the field.
        """
        # Check if the field has UI metadata
        if hasattr(field_obj, "metadata") and "ui" in field_obj.metadata:
            ui_metadata = field_obj.metadata["ui"]
            if isinstance(ui_metadata, ConfigUIMetadata):
                return ui_metadata
            elif isinstance(ui_metadata, dict):
                return ConfigUIMetadata(
                    label=ui_metadata.get("label", name.replace('_', ' ').title()),
                    description=ui_metadata.get("description", ""),
                    ui_type=ui_metadata.get("ui_type", "auto"),
                    ui_props=ui_metadata.get("ui_props", {}),
                    order=ui_metadata.get("order", 0),
                    group=ui_metadata.get("group", ""),
                    visible=ui_metadata.get("visible", True),
                    read_only=ui_metadata.get("read_only", False),
                    advanced=ui_metadata.get("advanced", False)
                )
        
        # Create default metadata
        return ConfigUIMetadata(
            label=name.replace('_', ' ').title(),
            description=field_obj.metadata.get("description", "") if hasattr(field_obj, "metadata") else ""
        )
    
    def _get_field_info_from_schema(self, schema: ConfigValueSchema) -> Dict[str, Any]:
        """
        Get field information from a schema.
        
        Args:
            schema: The schema.
            
        Returns:
            Field information including UI type and properties.
        """
        # Determine field type and properties based on validators
        validators = schema.get_validators()
        
        # Check for type validators
        type_validator = next((v for v in validators if hasattr(v, "expected_type")), None)
        if type_validator:
            expected_type = getattr(type_validator, "expected_type", None)
            if expected_type:
                return self._get_field_info_from_type(expected_type)
        
        # Check for enum validators
        enum_validator = next((v for v in validators if hasattr(v, "allowed_values")), None)
        if enum_validator:
            allowed_values = getattr(enum_validator, "allowed_values", None)
            if allowed_values:
                return {
                    "ui_type": ConfigUIHint.SELECT,
                    "ui_props": {"options": allowed_values}
                }
        
        # Default to text field
        return {"ui_type": ConfigUIHint.TEXT, "ui_props": {}}
    
    def _get_field_info_from_type(self, field_type: Type) -> Dict[str, Any]:
        """
        Get field information from a type.
        
        Args:
            field_type: The field type.
            
        Returns:
            Field information including UI type and properties.
        """
        # Handle basic types
        if field_type == str:
            return {"ui_type": ConfigUIHint.TEXT, "ui_props": {}}
        elif field_type == int or field_type == float:
            return {"ui_type": ConfigUIHint.NUMBER, "ui_props": {}}
        elif field_type == bool:
            return {"ui_type": ConfigUIHint.CHECKBOX, "ui_props": {}}
        
        # Handle list types
        origin = getattr(field_type, "__origin__", None)
        if origin == list:
            item_type = getattr(field_type, "__args__", (Any,))[0]
            item_info = self._get_field_info_from_type(item_type)
            return {
                "ui_type": "list",
                "ui_props": {
                    "item_type": item_info.get("ui_type", ConfigUIHint.TEXT),
                    "item_props": item_info.get("ui_props", {})
                }
            }
        
        # Handle dict types
        if origin == dict:
            key_type = getattr(field_type, "__args__", (Any, Any))[0]
            value_type = getattr(field_type, "__args__", (Any, Any))[1]
            key_info = self._get_field_info_from_type(key_type)
            value_info = self._get_field_info_from_type(value_type)
            return {
                "ui_type": "dict",
                "ui_props": {
                    "key_type": key_info.get("ui_type", ConfigUIHint.TEXT),
                    "key_props": key_info.get("ui_props", {}),
                    "value_type": value_info.get("ui_type", ConfigUIHint.TEXT),
                    "value_props": value_info.get("ui_props", {})
                }
            }
        
        # Handle enum types
        if hasattr(field_type, "__members__"):
            return {
                "ui_type": ConfigUIHint.SELECT,
                "ui_props": {"options": list(field_type.__members__.keys())}
            }
        
        # Default to text field
        return {"ui_type": ConfigUIHint.TEXT, "ui_props": {}}
    
    def bind_form(self, form: Any, config_data: Dict[str, Any]) -> List[ConfigUIBinding]:
        """
        Bind a form to configuration data.
        
        Args:
            form: The form component.
            config_data: The configuration data.
            
        Returns:
            A list of UI bindings.
        """
        bindings = []
        
        # Bind each field to its corresponding configuration value
        for path, field in self._bindings.items():
            # Get the configuration value
            value = self._get_value_from_path(config_data, path)
            
            # Create a binding
            binding = self._create_binding(field, value)
            bindings.append(binding)
        
        return bindings
    
    def _get_value_from_path(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get a value from a path in configuration data.
        
        Args:
            data: The configuration data.
            path: The path to the value.
            
        Returns:
            The value at the path.
        """
        parts = path.split('.')
        current = data
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        
        return current
    
    def _create_binding(self, field: Any, value: Any) -> ConfigUIBinding:
        """
        Create a binding between a field and a value.
        
        Args:
            field: The field component.
            value: The value to bind to.
            
        Returns:
            A UI binding.
        """
        # This method should be implemented by UI-specific subclasses
        raise NotImplementedError("Subclasses must implement _create_binding")
    
    def validate_form(self, form: Any) -> tuple[bool, Dict[str, str]]:
        """
        Validate a form.
        
        Args:
            form: The form component.
            
        Returns:
            A tuple of (is_valid, error_messages).
        """
        is_valid = True
        error_messages = {}
        
        # Validate each field
        for path, field in self._bindings.items():
            field_valid, field_error = self._validate_field(field)
            if not field_valid:
                is_valid = False
                error_messages[path] = field_error
        
        return is_valid, error_messages
    
    def _validate_field(self, field: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a field.
        
        Args:
            field: The field component.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        # This method should be implemented by UI-specific subclasses
        raise NotImplementedError("Subclasses must implement _validate_field")
    
    def get_form_data(self, form: Any) -> Dict[str, Any]:
        """
        Get data from a form.
        
        Args:
            form: The form component.
            
        Returns:
            The form data.
        """
        data = {}
        
        # Get data from each field
        for path, field in self._bindings.items():
            # Get the field value
            value = self._get_field_value(field)
            
            # Set the value in the data
            self._set_value_at_path(data, path, value)
        
        return data
    
    def _get_field_value(self, field: Any) -> Any:
        """
        Get the value from a field.
        
        Args:
            field: The field component.
            
        Returns:
            The field value.
        """
        # This method should be implemented by UI-specific subclasses
        raise NotImplementedError("Subclasses must implement _get_field_value")
    
    def _set_value_at_path(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """
        Set a value at a path in configuration data.
        
        Args:
            data: The configuration data.
            path: The path to the value.
            value: The value to set.
        """
        parts = path.split('.')
        current = data
        
        # Create the path
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value
