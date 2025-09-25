"""
Legacy configuration migrator.

This module provides utilities for migrating from legacy to new configuration systems.
"""

import os
import json
import logging
import shutil
from datetime import datetime
from typing import Any, Dict, Optional, Set, List, Tuple

from core_v2.config.interfaces import ConfigPath, ConfigProvider, ConfigScope
from core_v2.config.adapters.interfaces import LegacyConfigAdapter
from core_v2.config.adapters.parallel_provider import ParallelConfigProvider


class LegacyConfigMigrator:
    """
    Legacy configuration migrator.
    
    This class provides utilities for migrating from legacy to new configuration systems,
    including backup, validation, and rollback capabilities.
    """
    
    def __init__(
        self,
        legacy_adapter: LegacyConfigAdapter,
        new_provider: ConfigProvider,
        backup_dir: Optional[str] = None
    ):
        """
        Initialize the legacy configuration migrator.
        
        Args:
            legacy_adapter: The legacy configuration adapter.
            new_provider: The new configuration provider.
            backup_dir: Optional directory for configuration backups.
        """
        self._legacy_adapter = legacy_adapter
        self._new_provider = new_provider
        self._backup_dir = backup_dir
        self._logger = logging.getLogger(__name__)
        
        # Create backup directory if specified
        if backup_dir and not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self) -> Optional[str]:
        """
        Create a backup of the legacy configuration.
        
        Returns:
            The backup file path, or None if backup failed.
        """
        if not self._backup_dir:
            self._logger.warning("No backup directory specified")
            return None
        
        try:
            # Get the legacy file path
            legacy_file = getattr(self._legacy_adapter, "_legacy_file_path", None)
            if not legacy_file or not os.path.exists(legacy_file):
                self._logger.error("Legacy file not found")
                return None
            
            # Create a backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(
                self._backup_dir,
                f"legacy_config_backup_{timestamp}{os.path.splitext(legacy_file)[1]}"
            )
            
            # Copy the legacy file
            shutil.copy2(legacy_file, backup_file)
            
            self._logger.info(f"Created backup at {backup_file}")
            return backup_file
        except Exception as e:
            self._logger.error(f"Error creating backup: {e}")
            return None
    
    def validate_migration(self, migrated_values: Dict[ConfigPath, Any]) -> Tuple[bool, List[str]]:
        """
        Validate migrated values against the new configuration schema.
        
        Args:
            migrated_values: Dictionary of migrated values.
            
        Returns:
            A tuple of (is_valid, error_messages).
        """
        is_valid = True
        errors = []
        
        # Check if the new provider has schema validation
        validator = getattr(self._new_provider, "get_validator", None)
        if not validator:
            self._logger.warning("New provider does not support schema validation")
            return True, []
        
        # Validate each migrated value
        for path, value in migrated_values.items():
            path_valid, error = validator(path, value)
            if not path_valid:
                is_valid = False
                errors.append(f"Validation error for path '{path}': {error}")
        
        return is_valid, errors
    
    def migrate(self, validate: bool = True, create_backup: bool = True) -> Tuple[bool, Dict[ConfigPath, Any], List[str]]:
        """
        Migrate from legacy to new configuration.
        
        Args:
            validate: Whether to validate migrated values.
            create_backup: Whether to create a backup before migration.
            
        Returns:
            A tuple of (success, migrated_values, error_messages).
        """
        # Create a backup if requested
        if create_backup:
            backup_file = self.create_backup()
            if not backup_file:
                self._logger.warning("Failed to create backup, proceeding without backup")
        
        try:
            # Get all migrated values
            migrated_values = self._legacy_adapter.migrate_all()
            
            # Validate if requested
            if validate:
                is_valid, errors = self.validate_migration(migrated_values)
                if not is_valid:
                    self._logger.error("Validation failed, migration aborted")
                    return False, migrated_values, errors
            
            # Set all values in the new system
            for path, value in migrated_values.items():
                if not self._new_provider.set_value(path, value):
                    self._logger.error(f"Failed to set migrated value for path '{path}'")
            
            # Save the new system
            if not self._new_provider.save():
                self._logger.error("Failed to save new provider after migration")
                return False, migrated_values, ["Failed to save new provider"]
            
            return True, migrated_values, []
        except Exception as e:
            self._logger.error(f"Error during migration: {e}")
            return False, {}, [f"Error during migration: {e}"]
    
    def restore_backup(self, backup_file: str) -> bool:
        """
        Restore a backup of the legacy configuration.
        
        Args:
            backup_file: The backup file path.
            
        Returns:
            True if the backup was restored successfully, False otherwise.
        """
        try:
            # Get the legacy file path
            legacy_file = getattr(self._legacy_adapter, "_legacy_file_path", None)
            if not legacy_file:
                self._logger.error("Legacy file path not found")
                return False
            
            # Check if the backup file exists
            if not os.path.exists(backup_file):
                self._logger.error(f"Backup file not found: {backup_file}")
                return False
            
            # Copy the backup file to the legacy file
            shutil.copy2(backup_file, legacy_file)
            
            # Reload the legacy adapter
            self._legacy_adapter.load_legacy()
            
            self._logger.info(f"Restored backup from {backup_file}")
            return True
        except Exception as e:
            self._logger.error(f"Error restoring backup: {e}")
            return False
    
    def create_parallel_provider(
        self,
        write_to_legacy: bool = True,
        write_to_new: bool = True,
        read_legacy_fallback: bool = True
    ) -> ParallelConfigProvider:
        """
        Create a parallel configuration provider for transitional operation.
        
        Args:
            write_to_legacy: Whether to write changes to the legacy system.
            write_to_new: Whether to write changes to the new system.
            read_legacy_fallback: Whether to fall back to legacy system for reads.
            
        Returns:
            A parallel configuration provider.
        """
        return ParallelConfigProvider(
            new_provider=self._new_provider,
            legacy_adapter=self._legacy_adapter,
            write_to_legacy=write_to_legacy,
            write_to_new=write_to_new,
            read_legacy_fallback=read_legacy_fallback
        )
    
    def deprecate_legacy(self) -> bool:
        """
        Deprecate the legacy configuration by renaming the file.
        
        Returns:
            True if the legacy configuration was deprecated successfully, False otherwise.
        """
        try:
            # Get the legacy file path
            legacy_file = getattr(self._legacy_adapter, "_legacy_file_path", None)
            if not legacy_file or not os.path.exists(legacy_file):
                self._logger.error("Legacy file not found")
                return False
            
            # Create a deprecated filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            deprecated_file = f"{legacy_file}.deprecated_{timestamp}"
            
            # Rename the legacy file
            os.rename(legacy_file, deprecated_file)
            
            self._logger.info(f"Deprecated legacy configuration: {deprecated_file}")
            return True
        except Exception as e:
            self._logger.error(f"Error deprecating legacy configuration: {e}")
            return False
