"""
Configuration factory implementation.

This module provides factory methods for creating and initializing
configuration components for the Focus Guard application.
"""

from typing import Optional, Dict, Any

from core_v2.config.interfaces import ConfigurationManager, ConfigProvider, ConfigScope
from core_v2.config.manager import DefaultConfigurationManager
from core_v2.config.providers.json_provider import JsonConfigProvider
from core_v2.config.providers.memory_provider import MemoryConfigProvider
from core_v2.config.adapters.json_adapter import LegacyJsonConfigAdapter, CategoryMappingAdapter
from core_v2.config.providers.parallel_provider import ParallelConfigProvider
from core_v2.config.schema.domain_schema import (
    create_focus_guard_schema,
    create_domain_settings_schema,
    create_focus_rules_schema,
    create_user_preferences_schema
)
from core_v2.config.models.domain_model import (
    Category, CATEGORY_TO_ENUM_MAPPING, FocusGuardConfig
)


class ConfigurationFactory:
    """
    Factory for creating configuration components.
    
    This class provides methods for creating and initializing configuration
    components for the Focus Guard application.
    """
    
    @staticmethod
    def create_manager() -> ConfigurationManager:
        """
        Create a configuration manager.
        
        Returns:
            A configured ConfigurationManager instance.
        """
        return DefaultConfigurationManager()
    
    @staticmethod
    def create_json_provider(
        file_path: str,
        scope: ConfigScope = ConfigScope.USER,
        auto_save: bool = True
    ) -> ConfigProvider:
        """
        Create a JSON configuration provider.
        
        Args:
            file_path: Path to the JSON configuration file.
            scope: The configuration scope.
            auto_save: Whether to automatically save changes.
            
        Returns:
            A configured JsonConfigProvider instance.
        """
        return JsonConfigProvider(file_path, scope, auto_save)
    
    @staticmethod
    def create_memory_provider(
        initial_data: Optional[Dict[str, Any]] = None,
        scope: ConfigScope = ConfigScope.MEMORY
    ) -> ConfigProvider:
        """
        Create a memory configuration provider.
        
        Args:
            initial_data: Initial configuration data.
            scope: The configuration scope.
            
        Returns:
            A configured MemoryConfigProvider instance.
        """
        return MemoryConfigProvider(initial_data, scope)
    
    @staticmethod
    def create_legacy_adapter(
        legacy_file_path: str,
        path_mappings: Dict[str, str],
        auto_save: bool = False
    ) -> ConfigProvider:
        """
        Create a legacy JSON configuration adapter.
        
        Args:
            legacy_file_path: Path to the legacy JSON configuration file.
            path_mappings: Dictionary mapping legacy paths to new paths.
            auto_save: Whether to automatically save changes to the legacy file.
            
        Returns:
            A configured LegacyJsonConfigAdapter instance.
        """
        return LegacyJsonConfigAdapter(legacy_file_path, path_mappings, auto_save=auto_save)
    
    @staticmethod
    def create_category_mapping_adapter(
        legacy_file_path: str,
        path_mappings: Dict[str, str],
        auto_save: bool = False
    ) -> ConfigProvider:
        """
        Create a category mapping adapter.
        
        Args:
            legacy_file_path: Path to the legacy JSON configuration file.
            path_mappings: Dictionary mapping legacy paths to new paths.
            auto_save: Whether to automatically save changes to the legacy file.
            
        Returns:
            A configured CategoryMappingAdapter instance.
        """
        return CategoryMappingAdapter(
            legacy_file_path,
            path_mappings,
            CATEGORY_TO_ENUM_MAPPING,
            auto_save=auto_save
        )
    
    @staticmethod
    def create_parallel_provider(
        new_provider: ConfigProvider,
        legacy_adapter: ConfigProvider,
        write_to_new: bool = True,
        write_to_legacy: bool = True
    ) -> ConfigProvider:
        """
        Create a parallel configuration provider.
        
        Args:
            new_provider: The new configuration provider.
            legacy_adapter: The legacy configuration adapter.
            write_to_new: Whether to write changes to the new provider.
            write_to_legacy: Whether to write changes to the legacy adapter.
            
        Returns:
            A configured ParallelConfigProvider instance.
        """
        return ParallelConfigProvider(
            new_provider,
            legacy_adapter,
            write_to_new,
            write_to_legacy
        )
    
    @staticmethod
    def register_schemas(manager: ConfigurationManager) -> None:
        """
        Register schemas with a configuration manager.
        
        Args:
            manager: The configuration manager to register schemas with.
        """
        # Register domain-specific schemas
        manager.register_schema(create_focus_guard_schema())
        manager.register_schema(create_domain_settings_schema())
        manager.register_schema(create_focus_rules_schema())
        manager.register_schema(create_user_preferences_schema())
    
    @staticmethod
    def setup_focus_guard_config(
        config_file_path: str,
        legacy_config_path: Optional[str] = None,
        path_mappings: Optional[Dict[str, str]] = None
    ) -> tuple[ConfigurationManager, FocusGuardConfig]:
        """
        Set up a complete Focus Guard configuration system.
        
        Args:
            config_file_path: Path to the new configuration file.
            legacy_config_path: Optional path to the legacy configuration file.
            path_mappings: Optional dictionary mapping legacy paths to new paths.
            
        Returns:
            A tuple of (ConfigurationManager, FocusGuardConfig).
        """
        # Create manager
        manager = ConfigurationFactory.create_manager()
        
        # Register schemas
        ConfigurationFactory.register_schemas(manager)
        
        # Create and register providers
        json_provider = ConfigurationFactory.create_json_provider(config_file_path)
        
        if legacy_config_path and path_mappings:
            # Create legacy adapter with category mapping
            legacy_adapter = ConfigurationFactory.create_category_mapping_adapter(
                legacy_config_path,
                path_mappings
            )
            
            # Create parallel provider
            parallel_provider = ConfigurationFactory.create_parallel_provider(
                json_provider,
                legacy_adapter
            )
            
            # Register parallel provider
            manager.register_provider("default", parallel_provider)
        else:
            # Register JSON provider directly
            manager.register_provider("default", json_provider)
        
        # Create memory provider for volatile settings
        memory_provider = ConfigurationFactory.create_memory_provider()
        manager.register_provider("memory", memory_provider)
        
        # Create config model
        config = FocusGuardConfig()
        
        return manager, config
