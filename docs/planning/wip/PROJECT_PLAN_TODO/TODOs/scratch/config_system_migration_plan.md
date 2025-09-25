# Configuration System Migration Plan

## Overview

This document outlines the plan for migrating the current configuration system from `core/config` to a more modular, extensible architecture in `core_v2`. The new configuration system will serve as a centralized place for user and system preferences with a clean interface for UI integration, supporting features like email accounts, calendar integrations, and alerting preferences.

## Current Implementation Analysis

### Existing Components

1. **ConfigManager** (`config_manager.py`)
   - Handles loading/saving configuration from JSON files
   - Supports multiple user profiles
   - Provides default values for missing settings
   - Manages user-specific configurations

2. **SimpleConfigManager** (`simple_config_manager.py`)
   - Simplified version of ConfigManager
   - Works with a single configuration file
   - Lacks multi-user support

3. **ConfigHelper** (`config_helper.py`)
   - Provides dot notation access to configuration values
   - Offers get/set methods with path strings
   - Converts between dict and ConfigHelper objects

### Current Configuration Structure

- Configuration stored in JSON files
- User configurations in `config/users/{user_id}.json`
- Template configuration in `config/user_config_template.json`
- Application configuration in `config/focus_guard_config.json`
- Settings organized hierarchically (e.g., `alert_system.providers.email.enabled`)

### Limitations of Current System

1. **Limited Validation**
   - No schema validation for configuration values
   - No type checking or constraints enforcement

2. **No UI Integration Layer**
   - Direct file manipulation required for configuration changes
   - No clear separation between storage and presentation

3. **Limited Extensibility**
   - Difficult to add new configuration providers (e.g., database, cloud)
   - No plugin system for extending configuration capabilities

4. **No Change Notifications**
   - Components can't subscribe to configuration changes
   - Manual polling required to detect changes

5. **No Version Migration**
   - No built-in support for migrating between configuration versions
   - Manual migration required when schema changes

## Design Goals for core_v2 Configuration System

1. **Modularity**
   - Clear separation of concerns (storage, validation, access)
   - Pluggable storage backends (file, database, cloud)
   - Support for different configuration scopes (user, system, application)

2. **Type Safety and Validation**
   - Schema-based validation with type checking
   - Default values and constraints
   - Migration support for schema changes

3. **UI Integration**
   - Clean interface for UI components
   - Two-way binding between UI and configuration
   - Real-time validation and feedback

4. **Extensibility**
   - Plugin system for adding new configuration sections
   - Support for custom validators and converters
   - Event system for configuration changes

5. **Performance and Reliability**
   - Efficient caching and lazy loading
   - Thread safety for concurrent access
   - Robust error handling and recovery

## Architecture Design

### Core Components

1. **ConfigurationManager**
   - Central access point for all configuration operations
   - Manages configuration providers and validators
   - Handles caching and change notifications

2. **ConfigurationProvider Interface**
   - Abstract interface for configuration storage
   - Implementations: FileProvider, DatabaseProvider, etc.
   - Responsible for loading/saving configuration data

3. **ConfigurationSchema**
   - Defines structure, types, and constraints for configuration
   - Supports validation and migration
   - Provides documentation for configuration options

4. **ConfigurationValue**
   - Represents a typed configuration value
   - Handles validation, conversion, and constraints
   - Supports change tracking and notifications

5. **ConfigurationUI**
   - Bridges configuration system with UI components
   - Provides form generation and binding
   - Handles validation feedback and error display

### Directory Structure

```
core_v2/
  config/
    __init__.py
    manager.py              # ConfigurationManager implementation
    interfaces.py           # Core interfaces and abstract classes
    schema.py               # Schema definition and validation
    providers/
      __init__.py
      file_provider.py      # JSON file-based provider
      db_provider.py        # Database provider
      memory_provider.py    # In-memory provider for testing
    models/
      __init__.py
      config_value.py       # ConfigurationValue implementation
      config_section.py     # ConfigurationSection implementation
    validators/
      __init__.py
      type_validators.py    # Basic type validators
      constraint_validators.py  # Constraint validators
    ui/
      __init__.py
      form_generator.py     # UI form generation
      binding.py            # Two-way data binding
    events/
      __init__.py
      event_bus.py          # Event system for config changes
    migration/
      __init__.py
      migrator.py           # Version migration support
```

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

1. **Define Core Interfaces**
   - Create `interfaces.py` with base interfaces
   - Define provider and validator interfaces
   - Implement basic event system

2. **Implement Schema System**
   - Create schema definition classes
   - Implement validation framework
   - Support for default values and constraints

3. **Create File Provider**
   - Implement JSON file provider
   - Support for different scopes (user, system)
   - Backward compatibility with existing files

### Phase 2: Manager and Models (Week 1-2)

1. **Implement ConfigurationManager**
   - Central access point for configuration
   - Provider registration and management
   - Caching and optimization

2. **Create Value Models**
   - Implement ConfigurationValue class
   - Support for different value types
   - Change tracking and validation

3. **Add Migration Support**
   - Version tracking for configurations
   - Migration framework for schema changes
   - Automatic migration on load

### Phase 3: UI Integration (Week 2-3)

1. **Design UI Interface**
   - Define UI binding interfaces
   - Create form generation utilities
   - Implement validation feedback

2. **Implement Settings UI**
   - Create reusable settings components
   - Support for different input types
   - Real-time validation and feedback

3. **Add Integration Points**
   - Connect with existing UI framework
   - Support for different UI technologies
   - Accessibility considerations

### Phase 4: Advanced Features and Testing (Week 3-4)

1. **Implement Additional Providers**
   - Database provider for larger configurations
   - Memory provider for testing
   - Remote provider for cloud settings

2. **Add Plugin System**
   - Support for configuration plugins
   - Dynamic schema extension
   - Custom validators and converters

3. **Comprehensive Testing**
   - Unit tests for all components
   - Integration tests for common scenarios
   - Migration tests for version changes

## Migration Strategy

### Step 1: Parallel Implementation

1. Create the new configuration system in `core_v2/config`
2. Implement adapters for existing configuration files
3. Run both systems in parallel during development

### Step 2: Incremental Migration

1. Update one component at a time to use the new system
2. Migrate configuration files to new format with backward compatibility
3. Add UI integration points as components are migrated

### Step 3: Legacy Support

1. Create compatibility layer for legacy code
2. Deprecate old configuration system
3. Provide migration utilities for user configurations

## Code Examples

### Configuration Schema Definition

```python
# core_v2/config/schema.py
from typing import Any, Dict, List, Optional, Type, Union
from enum import Enum
from dataclasses import dataclass

class ConfigValueType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"
    EMAIL = "email"
    URL = "url"
    PATH = "path"

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
        """Validate a value against this schema."""
        # Implementation of validation logic
        pass

class ConfigSectionSchema:
    """Schema for a configuration section."""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.properties: Dict[str, Union[ConfigValueSchema, ConfigSectionSchema]] = {}
        
    def add_property(self, prop: Union[ConfigValueSchema, 'ConfigSectionSchema']) -> None:
        """Add a property to this section."""
        self.properties[prop.name] = prop
        
    def validate(self, config: Dict[str, Any]) -> tuple[bool, Dict[str, str]]:
        """Validate a configuration against this schema."""
        # Implementation of validation logic
        pass
```

### Configuration Manager

```python
# core_v2/config/manager.py
from typing import Any, Dict, List, Optional, Type, Union, Callable
from pathlib import Path
import threading
from abc import ABC, abstractmethod

from core_v2.config.interfaces import ConfigProvider, ConfigObserver
from core_v2.config.schema import ConfigSectionSchema
from core_v2.config.events.event_bus import ConfigEventBus

class ConfigurationManager:
    """Central manager for configuration access and manipulation."""
    
    def __init__(self):
        self._providers: Dict[str, ConfigProvider] = {}
        self._schemas: Dict[str, ConfigSectionSchema] = {}
        self._cache: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._event_bus = ConfigEventBus()
        
    def register_provider(self, name: str, provider: ConfigProvider) -> None:
        """Register a configuration provider."""
        with self._lock:
            self._providers[name] = provider
            
    def register_schema(self, schema: ConfigSectionSchema) -> None:
        """Register a configuration schema."""
        with self._lock:
            self._schemas[schema.name] = schema
            
    def get_value(self, path: str, default: Any = None) -> Any:
        """Get a configuration value by path."""
        # Implementation of value retrieval with caching
        pass
        
    def set_value(self, path: str, value: Any) -> bool:
        """Set a configuration value by path."""
        # Implementation of value setting with validation
        pass
        
    def subscribe(self, path: str, callback: Callable[[str, Any], None]) -> None:
        """Subscribe to changes in a configuration value."""
        self._event_bus.subscribe(path, callback)
        
    def unsubscribe(self, path: str, callback: Callable[[str, Any], None]) -> None:
        """Unsubscribe from changes in a configuration value."""
        self._event_bus.unsubscribe(path, callback)
        
    def save(self) -> bool:
        """Save all configuration changes."""
        # Implementation of saving to all providers
        pass
```

### File Provider Implementation

```python
# core_v2/config/providers/file_provider.py
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

from core_v2.config.interfaces import ConfigProvider
from core_v2.utils.paths import get_config_dir

class JsonFileProvider(ConfigProvider):
    """Configuration provider that uses JSON files."""
    
    def __init__(self, file_path: Optional[str] = None, scope: str = "user"):
        """
        Initialize the JSON file provider.
        
        Args:
            file_path: Path to the JSON file. If None, uses default based on scope.
            scope: Scope of the configuration ("user", "system", "app").
        """
        self.scope = scope
        
        if file_path is None:
            config_dir = get_config_dir()
            if scope == "user":
                # Use current user ID or default
                user_id = os.environ.get("FOCUS_GUARD_USER_ID", "default")
                self.file_path = config_dir / "users" / f"{user_id}.json"
            elif scope == "system":
                self.file_path = config_dir / "system_config.json"
            else:
                self.file_path = config_dir / "app_config.json"
        else:
            self.file_path = Path(file_path)
            
        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize with empty config if file doesn't exist
        if not self.file_path.exists():
            self._config = {}
            self._save_config()
        else:
            self._config = self._load_config()
            
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from the file."""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
            
    def _save_config(self) -> bool:
        """Save configuration to the file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            return True
        except Exception:
            return False
            
    def get(self, path: str, default: Any = None) -> Any:
        """Get a configuration value by path."""
        parts = path.split('.')
        current = self._config
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
            
        return current
        
    def set(self, path: str, value: Any) -> bool:
        """Set a configuration value by path."""
        parts = path.split('.')
        current = self._config
        
        # Navigate to the parent of the target node
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # Cannot navigate further if current node is not a dict
                return False
            current = current[part]
            
        # Set the value
        current[parts[-1]] = value
        return self._save_config()
        
    def has(self, path: str) -> bool:
        """Check if a configuration path exists."""
        parts = path.split('.')
        current = self._config
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
            
        return True
        
    def delete(self, path: str) -> bool:
        """Delete a configuration value by path."""
        parts = path.split('.')
        current = self._config
        
        # Navigate to the parent of the target node
        for i, part in enumerate(parts[:-1]):
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
            
        # Delete the value if it exists
        if parts[-1] in current:
            del current[parts[-1]]
            return self._save_config()
        return False
```

### UI Integration Example

```python
# core_v2/config/ui/form_generator.py
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass

from core_v2.config.schema import ConfigSectionSchema, ConfigValueSchema, ConfigValueType

@dataclass
class FormField:
    """Represents a form field for configuration UI."""
    name: str
    label: str
    field_type: str  # "text", "number", "checkbox", "select", etc.
    value: Any
    description: Optional[str] = None
    placeholder: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    validators: Optional[List[Dict[str, Any]]] = None
    disabled: bool = False
    required: bool = False

class FormGenerator:
    """Generates UI form definitions from configuration schemas."""
    
    @staticmethod
    def generate_form(schema: ConfigSectionSchema, values: Dict[str, Any]) -> List[FormField]:
        """
        Generate form fields from a configuration schema.
        
        Args:
            schema: Configuration schema
            values: Current configuration values
            
        Returns:
            List of form fields
        """
        fields = []
        
        for name, prop in schema.properties.items():
            if isinstance(prop, ConfigValueSchema):
                # Get current value or default
                value = values.get(name, prop.default)
                
                # Create field based on property type
                field = FormGenerator._create_field_for_value(prop, value)
                fields.append(field)
            elif isinstance(prop, ConfigSectionSchema):
                # For nested sections, we could either create a fieldset
                # or handle them separately depending on UI requirements
                pass
                
        return fields
        
    @staticmethod
    def _create_field_for_value(schema: ConfigValueSchema, value: Any) -> FormField:
        """Create a form field for a configuration value."""
        field_type = "text"  # Default field type
        options = None
        validators = []
        
        # Determine field type based on schema type
        if schema.type == ConfigValueType.INTEGER or schema.type == ConfigValueType.FLOAT:
            field_type = "number"
            
            # Add min/max validators if specified
            if schema.min_value is not None:
                validators.append({"type": "min", "value": schema.min_value})
            if schema.max_value is not None:
                validators.append({"type": "max", "value": schema.max_value})
                
        elif schema.type == ConfigValueType.BOOLEAN:
            field_type = "checkbox"
            
        elif schema.type == ConfigValueType.EMAIL:
            field_type = "email"
            validators.append({"type": "email"})
            
        elif schema.type == ConfigValueType.URL:
            field_type = "url"
            validators.append({"type": "url"})
            
        elif schema.enum_values:
            field_type = "select"
            options = [{"value": v, "label": str(v)} for v in schema.enum_values]
            
        # Add required validator if needed
        if schema.required:
            validators.append({"type": "required"})
            
        # Add string length validators if needed
        if schema.min_length is not None:
            validators.append({"type": "minLength", "value": schema.min_length})
        if schema.max_length is not None:
            validators.append({"type": "maxLength", "value": schema.max_length})
            
        # Add pattern validator if needed
        if schema.pattern:
            validators.append({"type": "pattern", "value": schema.pattern})
            
        return FormField(
            name=schema.name,
            label=schema.name.replace('_', ' ').title(),
            field_type=field_type,
            value=value,
            description=schema.description,
            options=options,
            validators=validators,
            required=schema.required
        )
```

## Benefits of the New System

1. **Improved Developer Experience**
   - Type-safe configuration access
   - Clear validation and error messages
   - Better IDE support with interfaces

2. **Enhanced User Experience**
   - Dynamic UI generation from schemas
   - Real-time validation feedback
   - Consistent settings interface

3. **Better Maintainability**
   - Modular architecture for easier updates
   - Clear separation of concerns
   - Comprehensive testing support

4. **Extensibility**
   - Easy to add new configuration sections
   - Support for different storage backends
   - Plugin system for custom extensions

5. **Integration with Other Systems**
   - Clean interfaces for UI components
   - Event system for reactive updates
   - Support for remote configuration

## Conclusion

This migration plan outlines a comprehensive approach to modernizing the configuration system in FocusGuard. By implementing a modular, type-safe, and UI-friendly configuration system, we can significantly improve both the developer and user experience while enabling new features and integrations.

The phased implementation approach allows for incremental migration with minimal disruption to existing functionality, while the flexible architecture ensures that the system can grow and adapt to future requirements.
