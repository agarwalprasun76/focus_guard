"""
Configuration manager implementation.

This module provides the central configuration manager implementation that
coordinates configuration providers, schemas, and event handling.
"""

import threading
import time
from collections import defaultdict
import logging
from cachetools import TTLCache
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union

from focus_guard.core.config.events.event_bus import ConfigEventBus
from focus_guard.core.config.interfaces import (
    ConfigChangeCallback,
    ConfigPath,
    ConfigProvider,
    ConfigScope,
    ConfigSchema,
    ConfigValue,
    ConfigurationManager,
)

# Type variable for configuration section types
T = TypeVar("T")


class DefaultConfigurationManager(ConfigurationManager):
    """
    Default implementation of the configuration manager.

    This class orchestrates configuration management by interacting with registered
    providers and schemas. It supports caching, validation, and event notifications.
    """

    def __init__(self, validation_enabled: bool = True, auto_coerce_types: bool = True, cache_ttl: int = 300):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._providers: Dict[ConfigScope, List[Tuple[int, ConfigProvider]]] = defaultdict(list)
        self._schemas: Dict[str, ConfigSchema] = {}
        self._schema_path_mappings: Dict[str, ConfigSchema] = {}
        self._cache = TTLCache(maxsize=1024, ttl=cache_ttl)
        self._lock = threading.RLock()
        self._event_bus = ConfigEventBus()
        self._validation_enabled = validation_enabled
        self._auto_coerce_types = auto_coerce_types
        self.logger.info("DefaultConfigurationManager initialized.")

    def register_provider(self, provider: ConfigProvider, scope: ConfigScope, priority: int = 0):
        with self._lock:
            self.logger.info(f"Registering provider '{provider.get_name()}' in scope '{scope.name}' with priority {priority}.")
            self._providers[scope].append((priority, provider))
            self._providers[scope].sort(key=lambda x: x[0], reverse=True)
            self.clear_cache()

    def register_schema(self, schema: ConfigSchema, path: Optional[ConfigPath] = None):
        with self._lock:
            schema_name = schema.get_name()
            self.logger.info(f"Registering schema '{schema_name}' for path '{path or schema_name}'.")
            self._schemas[schema_name] = schema
            if path:
                self._schema_path_mappings[path] = schema
            else:
                self._schema_path_mappings[schema_name] = schema
            self.clear_cache()

    def get_value(self, path: ConfigPath, default: Any = None) -> Any:
        with self._lock:
            if path in self._cache:
                self.logger.debug(f"Cache hit for '{path}'")
                return self._cache[path]

            self.logger.debug(f"Cache miss for '{path}', searching providers.")
            for scope in sorted(self._providers.keys(), key=lambda s: s.value):
                for _, provider in self._providers[scope]:
                    if provider.has_value(path):
                        value = provider.get_value(path)
                        self.logger.debug(f"Found value for '{path}' in provider {provider.__class__.__name__}: {value}")
                        self._cache[path] = value
                        return value

            self.logger.debug(f"Value for '{path}' not found in any provider, checking schema defaults.")
            schema, relative_path = self._find_schema_for_path(path)
            if schema and relative_path is not None:
                # get_default_values returns a flat dict of {relative_path: value}
                schema_defaults = schema.get_default_values()
                if relative_path in schema_defaults:
                    default_value = schema_defaults[relative_path]
                    self.logger.debug(f"Found default value for '{path}' in schema '{schema.get_name()}': {default_value}")
                    self._cache[path] = default_value
                    return default_value

            self.logger.debug(f"No value or default found for '{path}'. Returning provided default: {default}")
            return default

    def set_value(self, path: ConfigPath, value: Any) -> bool:
        with self._lock:
            self.logger.debug(f"Attempting to set value for '{path}'.")
            if self._validation_enabled:
                is_valid, error_message, coerced_value = self._validate_value(path, value)
                if not is_valid:
                    self.logger.error(f"Validation failed for '{path}': {error_message}")
                    raise ValueError(f"Validation failed for '{path}': {error_message}")
                if coerced_value is not None:
                    self.logger.debug(f"Value for '{path}' coerced from '{value}' to '{coerced_value}'.")
                    value = coerced_value

            if ConfigScope.USER in self._providers and self._providers[ConfigScope.USER]:
                # Get the highest priority provider in the USER scope
                _, provider = self._providers[ConfigScope.USER][0]
                self.logger.debug(f"Setting value for '{path}' in provider '{provider.__class__.__name__}'.")
                provider.set_value(path, value)
                self.clear_cache(path)
                self._event_bus.publish(path, value)
                return True
            
            self.logger.warning(f"No provider found in USER scope to set value for '{path}'.")
            return False

    def delete_value(self, path: str) -> bool:
        with self._lock:
            self.logger.debug(f"Attempting to delete value for '{path}'.")
            
            # Check if any provider has this value
            for scope in sorted(self._providers.keys(), key=lambda s: s.value):
                self.logger.debug(f"Checking scope: {scope}")
                for priority, provider in self._providers[scope]:
                    self.logger.debug(f"  Checking provider: {provider.get_name()} (priority: {priority})")
                    has_val = provider.has_value(path)
                    self.logger.debug(f"  Provider {provider.get_name()} has_value('{path}') = {has_val}")
                    if has_val:
                        self.logger.debug(f"Deleting value for '{path}' from provider '{provider.get_name()}'.")
                        result = provider.delete_value(path)
                        if result:
                            self.clear_cache(path)
                            self._event_bus.publish(path, None)  # Publish None to indicate deletion
                            return True
                        return False
            
            self.logger.debug(f"No value found to delete at path '{path}'.")
            return False

    def get_section(self, schema_type: Union[Type[T], str]) -> Optional[T]:
        with self._lock:
            schema_name = schema_type if isinstance(schema_type, str) else schema_type.__name__
            schema = self._schemas.get(schema_name)
            if not schema:
                self.logger.error(f"Schema '{schema_name}' not registered.")
                return None

            self.logger.debug(f"Getting section for schema '{schema_name}'.")
            section_data = self._get_section_data(schema)
            
            try:
                instance = schema.create_instance(section_data)
                self.logger.debug(f"Successfully created instance for schema '{schema_name}'.")
                return instance
            except Exception as e:
                self.logger.error(f"Failed to create instance for schema '{schema_name}': {e}", exc_info=True)
                return None

    def validate_configuration(self) -> Tuple[bool, Dict[str, str]]:
        with self._lock:
            all_errors = {}
            self.logger.info("Starting full configuration validation.")
            for schema_name, schema in self._schemas.items():
                self.logger.debug(f"Validating schema '{schema_name}'.")
                section_data = self._get_section_data(schema)
                is_valid, errors = schema.validate(section_data)
                if not is_valid:
                    self.logger.warning(f"Validation failed for schema '{schema_name}': {errors}")
                    for key, msg in errors.items():
                        full_path = f"{schema_name}.{key}"
                        all_errors[full_path] = msg
            
            if not all_errors:
                self.logger.info("Configuration validation successful.")
                return True, {}
            else:
                self.logger.error(f"Configuration validation failed with errors: {all_errors}")
                return False, all_errors

    def subscribe(self, path: ConfigPath, callback: ConfigChangeCallback):
        self.logger.info(f"Subscribing callback to path '{path}'.")
        self._event_bus.subscribe(path, callback)

    def unsubscribe(self, path: ConfigPath, callback: ConfigChangeCallback):
        self.logger.info(f"Unsubscribing callback from path '{path}'.")
        self._event_bus.unsubscribe(path, callback)

    def clear_cache(self, path: Optional[ConfigPath] = None):
        with self._lock:
            if path:
                if path in self._cache:
                    del self._cache[path]
                    self.logger.debug(f"Cleared cache for path '{path}'.")
            else:
                self._cache.clear()
                self.logger.info("Cleared all caches.")

    def save(self) -> None:
        with self._lock:
            self.logger.info("Saving configuration changes.")
            for scope in self._providers:
                for _, provider in self._providers[scope]:
                    if hasattr(provider, 'save'):
                        provider.save()

    def reload(self) -> None:
        with self._lock:
            self.logger.info("Reloading configuration from providers.")
            for scope in self._providers:
                for _, provider in self._providers[scope]:
                    if hasattr(provider, 'load'):
                        provider.load()
            self.clear_cache()
            self._event_bus.publish("*", value=self)  # Pass self as value parameter

    def _get_section_data(self, schema: ConfigSchema) -> Dict[str, Any]:
        schema_name = schema.get_name()
        prefix = schema_name + '.'

        # 1. Get defaults from schema and unflatten them into a nested dictionary.
        defaults = schema.get_default_values() if hasattr(schema, 'get_default_values') else {}
        self.logger.debug(f"Schema defaults for '{schema_name}': {defaults}")
        section_data = self._unflatten_dict(defaults)

        # 2. Collect and merge data from all providers, overwriting defaults.
        for scope in sorted(self._providers.keys(), key=lambda s: s.value):
            for _, provider in self._providers[scope]:
                provider_paths = provider.get_all_paths(prefix=prefix)
                # Strip the schema name prefix from the paths for correct unflattening
                provider_values = {p[len(prefix):]: provider.get_value(p) for p in provider_paths}
                unflattened_provider_data = self._unflatten_dict(provider_values)
                # Deep merge provider data over the existing section data (which starts with defaults)
                section_data = self._deep_merge(section_data, unflattened_provider_data)
        
        self.logger.debug(f"Final merged section data for '{schema_name}': {section_data}")
        return section_data

    def _find_schema_for_path(self, path: ConfigPath) -> Tuple[Optional[ConfigSchema], Optional[str]]:
        # Find the longest matching registered schema path for the given config path
        best_match = None
        for schema_path in self._schema_path_mappings:
            if path.startswith(schema_path):
                if best_match is None or len(schema_path) > len(best_match):
                    best_match = schema_path

        if best_match is not None:
            schema = self._schema_path_mappings[best_match]
            # The relative path is the part of the path that comes after the schema path
            relative_path = path[len(best_match):].lstrip('.')
            self.logger.debug(f"Found schema '{schema.get_name()}' for path '{path}' with relative path '{relative_path}'.")
            return schema, relative_path

        # Fallback for schemas that might not have an explicit path mapping (e.g., registered by name)
        parts = path.split('.')
        if parts and parts[0] in self._schemas:
            schema = self._schemas[parts[0]]
            relative_path = '.'.join(parts[1:])
            self.logger.debug(f"Found schema '{schema.get_name()}' by name for path '{path}' with relative path '{relative_path}'.")
            return schema, relative_path

        self.logger.debug(f"No schema found for path '{path}'.")
        return None, None

    def _validate_value(self, path: str, value: Any) -> tuple[bool, str, Optional[Any]]:
        schema, relative_path = self._find_schema_for_path(path)
        if not schema or relative_path is None:
            self.logger.debug(f"No schema found for validation of path '{path}'. Skipping validation.")
            return True, '', None

        coerced_value = None
        value_to_validate = value

        if self._auto_coerce_types and hasattr(schema, 'coerce_value'):
            try:
                coerced_value = schema.coerce_value(relative_path, value)
                value_to_validate = coerced_value
                self.logger.debug(f"Coerced value for '{path}': {coerced_value}")
            except (ValueError, TypeError) as e:
                error_message = f"Could not coerce value for '{path}': {e}"
                self.logger.warning(error_message)
                return False, error_message, None

        if hasattr(schema, 'validate_value'):
            is_valid, error_message = schema.validate_value(relative_path, value_to_validate)
            if not is_valid:
                self.logger.warning(f"Validation failed for '{path}' with value '{value_to_validate}': {error_message}")
            return is_valid, error_message, coerced_value

        return True, '', coerced_value

    def _unflatten_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        if not d:
            return result

        for key, value in d.items():
            if not key:  # Handle root-level value assignment
                if isinstance(value, dict):
                    result = self._deep_merge(result, value)
                continue

            parts = key.split('.')
            d_ref = result
            for part in parts[:-1]:
                if part not in d_ref or not isinstance(d_ref[part], dict):
                    d_ref[part] = {}
                d_ref = d_ref[part]
            d_ref[parts[-1]] = value
        return result

    def _deep_merge(self, destination: Dict, source: Dict) -> Dict:
        for key, value in source.items():
            if isinstance(value, dict) and key in destination and isinstance(destination[key], dict):
                destination[key] = self._deep_merge(destination[key], value)
            else:
                destination[key] = value
        return destination
