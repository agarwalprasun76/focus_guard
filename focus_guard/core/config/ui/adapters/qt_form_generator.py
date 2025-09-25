"""
Qt form generator for configuration UI.

This module provides a form generator for Qt-based user interfaces.
"""

from typing import Any, Dict, List, Optional, Callable, Type, Union, Tuple
import threading

# Import Qt modules conditionally to avoid hard dependency
try:
    from PyQt5 import QtWidgets, QtCore, QtGui
    QT_AVAILABLE = True
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False

from focus_guard.core.config.interfaces import ConfigPath, ConfigSchema
from focus_guard.core.config.models.config_value import ConfigurationValue
from focus_guard.core.config.ui.interfaces import (
    ConfigUIBinding, ConfigFormGenerator, ConfigUIController, 
    ConfigUIMetadata, ConfigUIHint
)
from focus_guard.core.config.ui.form_generator import DefaultConfigFormGenerator
from focus_guard.core.config.ui.adapters.qt_adapter import QtUIFactory


class QtConfigBinding(ConfigUIBinding):
    """
    Qt implementation of the configuration UI binding.
    
    This class provides a binding between a configuration value and a Qt UI component.
    """
    
    def __init__(
        self,
        component: QtWidgets.QWidget,
        config_value: ConfigurationValue,
        path: str
    ):
        """
        Initialize the UI binding.
        
        Args:
            component: The Qt UI component.
            config_value: The configuration value.
            path: The configuration path.
        """
        self._component = component
        self._config_value = config_value
        self._path = path
        
        # Set up change listeners
        self._setup_component_change_listener()
        self._config_change_listener = lambda path, value: self._on_config_change(path, value)
        
        # Bind the component to the configuration value
        self.bind_to_config(config_value)
    
    def _setup_component_change_listener(self) -> None:
        """Set up the component change listener."""
        # Connect the appropriate signal based on the component type
        if isinstance(self._component, QtWidgets.QLineEdit):
            self._component.textChanged.connect(self._on_component_change)
        elif isinstance(self._component, QtWidgets.QSpinBox) or isinstance(self._component, QtWidgets.QDoubleSpinBox):
            self._component.valueChanged.connect(self._on_component_change)
        elif isinstance(self._component, QtWidgets.QCheckBox):
            self._component.stateChanged.connect(lambda state: self._on_component_change(state == QtCore.Qt.Checked))
        elif isinstance(self._component, QtWidgets.QComboBox):
            self._component.currentIndexChanged.connect(lambda index: self._on_component_change(self._component.itemData(index)))
        elif isinstance(self._component, QtWidgets.QSlider):
            self._component.valueChanged.connect(self._on_component_change)
        elif isinstance(self._component, QtWidgets.QTextEdit):
            self._component.textChanged.connect(lambda: self._on_component_change(self._component.toPlainText()))
        elif isinstance(self._component, QtWidgets.QPushButton) and hasattr(self._component, 'color_changed'):
            self._component.color_changed.connect(self._on_component_change)
        elif isinstance(self._component, QtWidgets.QWidget) and hasattr(self._component, 'button_group'):
            # For radio button groups
            self._component.button_group.buttonClicked.connect(
                lambda button: self._on_component_change(button.property('value'))
            )
    
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
        
        # Update the component based on its type
        if isinstance(self._component, QtWidgets.QLineEdit):
            self._component.setText(str(value) if value is not None else "")
        elif isinstance(self._component, QtWidgets.QSpinBox):
            self._component.setValue(int(value) if value is not None else 0)
        elif isinstance(self._component, QtWidgets.QDoubleSpinBox):
            self._component.setValue(float(value) if value is not None else 0.0)
        elif isinstance(self._component, QtWidgets.QCheckBox):
            self._component.setChecked(bool(value) if value is not None else False)
        elif isinstance(self._component, QtWidgets.QComboBox):
            index = self._component.findData(value)
            if index >= 0:
                self._component.setCurrentIndex(index)
        elif isinstance(self._component, QtWidgets.QSlider):
            self._component.setValue(int(value) if value is not None else 0)
        elif isinstance(self._component, QtWidgets.QTextEdit):
            self._component.setText(str(value) if value is not None else "")
        elif isinstance(self._component, QtWidgets.QPushButton) and hasattr(self._component, 'color'):
            if value and isinstance(value, str):
                self._component.color = QtGui.QColor(value)
                # Update the button appearance
                pixmap = QtGui.QPixmap(self._component.size())
                pixmap.fill(self._component.color)
                self._component.setIcon(QtGui.QIcon(pixmap))
                self._component.setIconSize(self._component.size())
        elif isinstance(self._component, QtWidgets.QWidget) and hasattr(self._component, 'button_group'):
            # For radio button groups
            for button in self._component.button_group.buttons():
                if button.property('value') == value:
                    button.setChecked(True)
                    break
    
    def update_to_config(self) -> Tuple[bool, Optional[str]]:
        """
        Update the configuration value from the UI component.
        
        Returns:
            A tuple of (success, error_message).
        """
        # Get the value from the component based on its type
        value = None
        
        if isinstance(self._component, QtWidgets.QLineEdit):
            value = self._component.text()
        elif isinstance(self._component, QtWidgets.QSpinBox):
            value = self._component.value()
        elif isinstance(self._component, QtWidgets.QDoubleSpinBox):
            value = self._component.value()
        elif isinstance(self._component, QtWidgets.QCheckBox):
            value = self._component.isChecked()
        elif isinstance(self._component, QtWidgets.QComboBox):
            value = self._component.itemData(self._component.currentIndex())
        elif isinstance(self._component, QtWidgets.QSlider):
            value = self._component.value()
        elif isinstance(self._component, QtWidgets.QTextEdit):
            value = self._component.toPlainText()
        elif isinstance(self._component, QtWidgets.QPushButton) and hasattr(self._component, 'color'):
            value = self._component.color.name()
        elif isinstance(self._component, QtWidgets.QWidget) and hasattr(self._component, 'button_group'):
            # For radio button groups
            checked_button = self._component.button_group.checkedButton()
            if checked_button:
                value = checked_button.property('value')
        
        # Update the configuration value
        success, error = self._config_value.set(value)
        
        # Show error in the UI if validation fails
        if not success and error:
            QtWidgets.QMessageBox.warning(
                self._component, "Validation Error", error
            )
        
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
        
        # Show error in the UI if validation fails
        if not success and error:
            QtWidgets.QMessageBox.warning(
                self._component, "Validation Error", error
            )
    
    def _on_config_change(self, path: str, value: Any) -> None:
        """
        Handle configuration value changes.
        
        Args:
            path: The configuration path.
            value: The new value.
        """
        # Update the component
        self.update_from_config()


class QtConfigFormGenerator(DefaultConfigFormGenerator):
    """
    Qt implementation of the configuration form generator.
    
    This class provides a form generator for Qt-based user interfaces.
    """
    
    def __init__(self):
        """Initialize the form generator."""
        super().__init__()
        self._ui_factory = QtUIFactory()
    
    def generate_form(self, schema: ConfigSchema) -> Any:
        """
        Generate a form for a configuration schema.
        
        Args:
            schema: The configuration schema.
            
        Returns:
            A form component.
        """
        if not QT_AVAILABLE:
            raise ImportError("Qt is not available")
        
        # Get schema metadata
        name = schema.get_name()
        description = schema.get_description()
        
        # Create a form
        form = self._ui_factory.create_form(name, description)
        
        # Generate fields for the schema
        self._generate_fields_for_schema(form, schema, "")
        
        return form
    
    def bind_form(self, form: Any, config_data: Dict[str, Any]) -> List[ConfigUIBinding]:
        """
        Bind a form to configuration data.
        
        Args:
            form: The form component.
            config_data: The configuration data.
            
        Returns:
            A list of UI bindings.
        """
        if not QT_AVAILABLE:
            raise ImportError("Qt is not available")
        
        bindings = []
        
        # Find all input fields in the form
        fields = self._find_fields(form)
        
        # Bind each field to its configuration value
        for field_name, field in fields.items():
            # Get the configuration value
            path_parts = field_name.split('.')
            value = config_data
            
            for part in path_parts[:-1]:
                if part in value:
                    value = value[part]
                else:
                    value = None
                    break
            
            if value is not None and path_parts[-1] in value:
                field_value = value[path_parts[-1]]
                
                # Create a configuration value
                config_value = self._create_config_value_for_field(field, field_value)
                
                # Create a binding
                binding = QtConfigBinding(field, config_value, field_name)
                bindings.append(binding)
        
        return bindings
    
    def validate_form(self, form: Any) -> Tuple[bool, Dict[str, str]]:
        """
        Validate a form.
        
        Args:
            form: The form component.
            
        Returns:
            A tuple of (is_valid, error_messages).
        """
        if not QT_AVAILABLE:
            raise ImportError("Qt is not available")
        
        is_valid = True
        error_messages = {}
        
        # Find all input fields in the form
        fields = self._find_fields(form)
        
        # Validate each field
        for field_name, field in fields.items():
            field_valid, field_error = self._validate_field(field)
            
            if not field_valid:
                is_valid = False
                error_messages[field_name] = field_error
                
                # Show error in the UI
                QtWidgets.QMessageBox.warning(
                    form, "Validation Error", f"{field_name}: {field_error}"
                )
        
        return is_valid, error_messages
    
    def get_form_data(self, form: Any) -> Dict[str, Any]:
        """
        Get the data from a form.
        
        Args:
            form: The form component.
            
        Returns:
            The form data.
        """
        if not QT_AVAILABLE:
            raise ImportError("Qt is not available")
        
        data = {}
        
        # Find all input fields in the form
        fields = self._find_fields(form)
        
        # Get the value from each field
        for field_name, field in fields.items():
            field_value = self._get_field_value(field)
            
            # Set the value in the data dictionary
            path_parts = field_name.split('.')
            current = data
            
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            current[path_parts[-1]] = field_value
        
        return data
    
    def _find_fields(self, widget: QtWidgets.QWidget) -> Dict[str, QtWidgets.QWidget]:
        """
        Find all input fields in a widget.
        
        Args:
            widget: The widget to search.
            
        Returns:
            A dictionary of field name to field widget.
        """
        fields = {}
        
        # Check if the widget is a field
        if hasattr(widget, 'objectName') and widget.objectName():
            # Skip fields with names starting with underscore
            if not widget.objectName().startswith('_'):
                fields[widget.objectName()] = widget
        
        # Check child widgets
        for child in widget.findChildren(QtWidgets.QWidget):
            # Skip layout widgets
            if isinstance(child, QtWidgets.QLayout):
                continue
            
            # Check if the child is a field
            if hasattr(child, 'objectName') and child.objectName():
                # Skip fields with names starting with underscore
                if not child.objectName().startswith('_'):
                    fields[child.objectName()] = child
        
        return fields
    
    def _validate_field(self, field: QtWidgets.QWidget) -> Tuple[bool, Optional[str]]:
        """
        Validate a field.
        
        Args:
            field: The field to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        # Validate based on field type
        if isinstance(field, QtWidgets.QLineEdit):
            # Check if the field is required
            if field.property('required') and not field.text():
                return False, "This field is required"
            
            # Check if the field has a pattern
            pattern = field.property('pattern')
            if pattern and field.text():
                import re
                if not re.match(pattern, field.text()):
                    return False, f"Value must match pattern {pattern}"
        
        elif isinstance(field, QtWidgets.QSpinBox) or isinstance(field, QtWidgets.QDoubleSpinBox):
            # Validation is handled by the widget
            pass
        
        elif isinstance(field, QtWidgets.QCheckBox):
            # No validation needed
            pass
        
        elif isinstance(field, QtWidgets.QComboBox):
            # Check if the field is required
            if field.property('required') and field.currentIndex() < 0:
                return False, "This field is required"
        
        elif isinstance(field, QtWidgets.QSlider):
            # No validation needed
            pass
        
        elif isinstance(field, QtWidgets.QTextEdit):
            # Check if the field is required
            if field.property('required') and not field.toPlainText():
                return False, "This field is required"
        
        return True, None
    
    def _get_field_value(self, field: QtWidgets.QWidget) -> Any:
        """
        Get the value from a field.
        
        Args:
            field: The field to get the value from.
            
        Returns:
            The field value.
        """
        if isinstance(field, QtWidgets.QLineEdit):
            return field.text()
        elif isinstance(field, QtWidgets.QSpinBox):
            return field.value()
        elif isinstance(field, QtWidgets.QDoubleSpinBox):
            return field.value()
        elif isinstance(field, QtWidgets.QCheckBox):
            return field.isChecked()
        elif isinstance(field, QtWidgets.QComboBox):
            return field.itemData(field.currentIndex())
        elif isinstance(field, QtWidgets.QSlider):
            return field.value()
        elif isinstance(field, QtWidgets.QTextEdit):
            return field.toPlainText()
        elif isinstance(field, QtWidgets.QPushButton) and hasattr(field, 'color'):
            return field.color.name()
        elif isinstance(field, QtWidgets.QWidget) and hasattr(field, 'button_group'):
            # For radio button groups
            checked_button = field.button_group.checkedButton()
            if checked_button:
                return checked_button.property('value')
            return None
        
        return None
    
    def _create_config_value_for_field(
        self, 
        field: QtWidgets.QWidget, 
        value: Any
    ) -> ConfigurationValue:
        """
        Create a configuration value for a field.
        
        Args:
            field: The field.
            value: The initial value.
            
        Returns:
            A configuration value.
        """
        from focus_guard.core.config.models.config_value import (
            StringConfigValue, IntegerConfigValue, BooleanConfigValue,
            ListConfigValue, DictConfigValue
        )
        
        # Create a configuration value based on field type
        if isinstance(field, QtWidgets.QLineEdit):
            return StringConfigValue(value)
        elif isinstance(field, QtWidgets.QSpinBox):
            return IntegerConfigValue(value)
        elif isinstance(field, QtWidgets.QDoubleSpinBox):
            return StringConfigValue(str(value))  # Use string for float values
        elif isinstance(field, QtWidgets.QCheckBox):
            return BooleanConfigValue(value)
        elif isinstance(field, QtWidgets.QComboBox):
            return StringConfigValue(str(value))
        elif isinstance(field, QtWidgets.QSlider):
            return IntegerConfigValue(value)
        elif isinstance(field, QtWidgets.QTextEdit):
            return StringConfigValue(value)
        elif isinstance(field, QtWidgets.QPushButton) and hasattr(field, 'color'):
            return StringConfigValue(value)
        elif isinstance(field, QtWidgets.QWidget) and hasattr(field, 'button_group'):
            return StringConfigValue(str(value))
        
        # Default to string value
        return StringConfigValue(str(value) if value is not None else "")
