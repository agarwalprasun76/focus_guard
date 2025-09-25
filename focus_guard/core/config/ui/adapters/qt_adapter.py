"""
Qt adapter for configuration UI components.

This module provides adapters for integrating the configuration system
with Qt-based user interfaces.
"""

from typing import Any, Dict, List, Optional, Callable, Type, Union
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
from focus_guard.core.config.ui.components import (
    ConfigUIComponent, TextComponent, NumberComponent,
    BooleanComponent, SelectComponent, ListComponent, DictComponent
)


class QtUIFactory:
    """
    Factory for creating Qt UI components.
    
    This class provides methods for creating Qt UI components
    for configuration settings.
    """
    
    @staticmethod
    def create_form(name: str, description: str = "") -> QtWidgets.QWidget:
        """
        Create a form container.
        
        Args:
            name: The form name.
            description: The form description.
            
        Returns:
            A form widget.
        """
        if not QT_AVAILABLE:
            raise ImportError("Qt is not available")
        
        # Create a form widget
        form = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        form.setLayout(layout)
        
        # Add a title if provided
        if name:
            title = QtWidgets.QLabel(name)
            title.setStyleSheet("font-weight: bold; font-size: 16px;")
            layout.addWidget(title)
        
        # Add a description if provided
        if description:
            desc = QtWidgets.QLabel(description)
            desc.setWordWrap(True)
            layout.addWidget(desc)
        
        # Add a scroll area for the form fields
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        
        # Create a widget for the form fields
        fields = QtWidgets.QWidget()
        fields_layout = QtWidgets.QFormLayout()
        fields.setLayout(fields_layout)
        scroll.setWidget(fields)
        
        layout.addWidget(scroll)
        
        # Store the fields layout
        form.fields_layout = fields_layout
        
        return form
    
    @staticmethod
    def create_section(
        form: QtWidgets.QWidget,
        name: str,
        label: str,
        description: str = ""
    ) -> QtWidgets.QWidget:
        """
        Create a section container.
        
        Args:
            form: The parent form.
            name: The section name.
            label: The section label.
            description: The section description.
            
        Returns:
            A section widget.
        """
        if not QT_AVAILABLE:
            raise ImportError("Qt is not available")
        
        # Create a group box
        section = QtWidgets.QGroupBox(label)
        layout = QtWidgets.QVBoxLayout()
        section.setLayout(layout)
        
        # Add a description if provided
        if description:
            desc = QtWidgets.QLabel(description)
            desc.setWordWrap(True)
            layout.addWidget(desc)
        
        # Create a widget for the section fields
        fields = QtWidgets.QWidget()
        fields_layout = QtWidgets.QFormLayout()
        fields.setLayout(fields_layout)
        layout.addWidget(fields)
        
        # Add the section to the form
        form.fields_layout.addRow(section)
        
        # Store the fields layout
        section.fields_layout = fields_layout
        
        return section
    
    @staticmethod
    def create_field(
        form: QtWidgets.QWidget,
        name: str,
        label: str,
        description: str = "",
        field_type: str = "text",
        field_props: Dict[str, Any] = None,
        read_only: bool = False,
        advanced: bool = False,
        order: int = 0,
        group: str = ""
    ) -> Any:
        """
        Create a field component.
        
        Args:
            form: The parent form or section.
            name: The field name.
            label: The field label.
            description: The field description.
            field_type: The field type.
            field_props: Additional field properties.
            read_only: Whether the field is read-only.
            advanced: Whether the field is for advanced settings.
            order: The field order.
            group: The field group.
            
        Returns:
            A field component.
        """
        if not QT_AVAILABLE:
            raise ImportError("Qt is not available")
        
        field_props = field_props or {}
        
        # Create the field based on type
        field = None
        
        if field_type == ConfigUIHint.TEXT:
            field = QtUIFactory._create_text_field(name, label, description, field_props, read_only)
        elif field_type == ConfigUIHint.PASSWORD:
            field = QtUIFactory._create_password_field(name, label, description, field_props, read_only)
        elif field_type == ConfigUIHint.NUMBER:
            field = QtUIFactory._create_number_field(name, label, description, field_props, read_only)
        elif field_type == ConfigUIHint.CHECKBOX:
            field = QtUIFactory._create_checkbox_field(name, label, description, field_props, read_only)
        elif field_type == ConfigUIHint.SWITCH:
            field = QtUIFactory._create_switch_field(name, label, description, field_props, read_only)
        elif field_type == ConfigUIHint.SELECT:
            field = QtUIFactory._create_select_field(name, label, description, field_props, read_only)
        elif field_type == ConfigUIHint.RADIO:
            field = QtUIFactory._create_radio_field(name, label, description, field_props, read_only)
        elif field_type == ConfigUIHint.SLIDER:
            field = QtUIFactory._create_slider_field(name, label, description, field_props, read_only)
        elif field_type == ConfigUIHint.COLOR:
            field = QtUIFactory._create_color_field(name, label, description, field_props, read_only)
        elif field_type == ConfigUIHint.TEXTAREA:
            field = QtUIFactory._create_textarea_field(name, label, description, field_props, read_only)
        else:
            # Default to text field
            field = QtUIFactory._create_text_field(name, label, description, field_props, read_only)
        
        # Add the field to the form
        if hasattr(form, 'fields_layout'):
            # Create a container for the field with label and description
            container = QtWidgets.QWidget()
            container_layout = QtWidgets.QVBoxLayout()
            container_layout.setContentsMargins(0, 0, 0, 0)
            container.setLayout(container_layout)
            
            # Add the field
            container_layout.addWidget(field)
            
            # Add a description if provided
            if description:
                desc = QtWidgets.QLabel(description)
                desc.setWordWrap(True)
                desc.setStyleSheet("color: gray; font-size: 10px;")
                container_layout.addWidget(desc)
            
            # Add the container to the form
            form.fields_layout.addRow(label, container)
        
        return field
    
    @staticmethod
    def _create_text_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QLineEdit:
        """Create a text field."""
        field = QtWidgets.QLineEdit()
        field.setObjectName(name)
        field.setReadOnly(read_only)
        
        # Apply properties
        if 'placeholder' in props:
            field.setPlaceholderText(props['placeholder'])
        
        if 'max_length' in props:
            field.setMaxLength(props['max_length'])
        
        return field
    
    @staticmethod
    def _create_password_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QLineEdit:
        """Create a password field."""
        field = QtWidgets.QLineEdit()
        field.setObjectName(name)
        field.setReadOnly(read_only)
        field.setEchoMode(QtWidgets.QLineEdit.Password)
        
        # Apply properties
        if 'placeholder' in props:
            field.setPlaceholderText(props['placeholder'])
        
        if 'max_length' in props:
            field.setMaxLength(props['max_length'])
        
        return field
    
    @staticmethod
    def _create_number_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QSpinBox:
        """Create a number field."""
        # Check if the field should be a double spin box
        is_double = props.get('is_double', False)
        
        if is_double:
            field = QtWidgets.QDoubleSpinBox()
            
            # Apply properties
            if 'min' in props:
                field.setMinimum(float(props['min']))
            else:
                field.setMinimum(float('-inf'))
            
            if 'max' in props:
                field.setMaximum(float(props['max']))
            else:
                field.setMaximum(float('inf'))
            
            if 'step' in props:
                field.setSingleStep(float(props['step']))
            
            if 'decimals' in props:
                field.setDecimals(int(props['decimals']))
        else:
            field = QtWidgets.QSpinBox()
            
            # Apply properties
            if 'min' in props:
                field.setMinimum(int(props['min']))
            else:
                field.setMinimum(-2147483648)
            
            if 'max' in props:
                field.setMaximum(int(props['max']))
            else:
                field.setMaximum(2147483647)
            
            if 'step' in props:
                field.setSingleStep(int(props['step']))
        
        field.setObjectName(name)
        field.setReadOnly(read_only)
        
        return field
    
    @staticmethod
    def _create_checkbox_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QCheckBox:
        """Create a checkbox field."""
        field = QtWidgets.QCheckBox()
        field.setObjectName(name)
        field.setEnabled(not read_only)
        
        return field
    
    @staticmethod
    def _create_switch_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QCheckBox:
        """Create a switch field."""
        # Qt doesn't have a native switch control, so use a checkbox
        field = QtWidgets.QCheckBox()
        field.setObjectName(name)
        field.setEnabled(not read_only)
        
        return field
    
    @staticmethod
    def _create_select_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QComboBox:
        """Create a select field."""
        field = QtWidgets.QComboBox()
        field.setObjectName(name)
        field.setEnabled(not read_only)
        
        # Apply properties
        if 'options' in props:
            options = props['options']
            option_labels = props.get('option_labels', {})
            
            for option in options:
                option_label = option_labels.get(option, str(option))
                field.addItem(option_label, option)
        
        return field
    
    @staticmethod
    def _create_radio_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QWidget:
        """Create a radio field."""
        # Create a container for the radio buttons
        container = QtWidgets.QWidget()
        container.setObjectName(name)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)
        
        # Create a button group
        button_group = QtWidgets.QButtonGroup(container)
        button_group.setObjectName(f"{name}_group")
        
        # Apply properties
        if 'options' in props:
            options = props['options']
            option_labels = props.get('option_labels', {})
            
            for i, option in enumerate(options):
                option_label = option_labels.get(option, str(option))
                radio = QtWidgets.QRadioButton(option_label)
                radio.setObjectName(f"{name}_{i}")
                radio.setEnabled(not read_only)
                radio.setProperty('value', option)
                
                layout.addWidget(radio)
                button_group.addButton(radio, i)
        
        # Store the button group
        container.button_group = button_group
        
        return container
    
    @staticmethod
    def _create_slider_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QSlider:
        """Create a slider field."""
        field = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        field.setObjectName(name)
        field.setEnabled(not read_only)
        
        # Apply properties
        if 'min' in props:
            field.setMinimum(int(props['min']))
        
        if 'max' in props:
            field.setMaximum(int(props['max']))
        
        if 'step' in props:
            field.setSingleStep(int(props['step']))
        
        return field
    
    @staticmethod
    def _create_color_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QPushButton:
        """Create a color field."""
        field = QtWidgets.QPushButton()
        field.setObjectName(name)
        field.setEnabled(not read_only)
        
        # Set a fixed size
        field.setFixedSize(30, 30)
        
        # Store the current color
        field.color = QtGui.QColor(255, 255, 255)
        
        # Update the button appearance
        def update_color():
            pixmap = QtGui.QPixmap(field.size())
            pixmap.fill(field.color)
            field.setIcon(QtGui.QIcon(pixmap))
            field.setIconSize(field.size())
        
        update_color()
        
        # Connect the button click event
        def on_click():
            color = QtWidgets.QColorDialog.getColor(field.color)
            if color.isValid():
                field.color = color
                update_color()
                field.color_changed.emit(color.name())
        
        field.clicked.connect(on_click)
        
        # Add a custom signal for color changes
        field.color_changed = QtCore.pyqtSignal(str) if hasattr(QtCore, 'pyqtSignal') else QtCore.Signal(str)
        
        return field
    
    @staticmethod
    def _create_textarea_field(
        name: str,
        label: str,
        description: str,
        props: Dict[str, Any],
        read_only: bool
    ) -> QtWidgets.QTextEdit:
        """Create a textarea field."""
        field = QtWidgets.QTextEdit()
        field.setObjectName(name)
        field.setReadOnly(read_only)
        
        # Apply properties
        if 'placeholder' in props:
            field.setPlaceholderText(props['placeholder'])
        
        return field
