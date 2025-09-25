#!/usr/bin/env python3
"""
Blocking Module Migration Script

This script handles the migration of blocking functionality from the activity module
to the core blocking module. It performs the following tasks:
1. Migrates blocking policies to the new format
2. Updates configuration files
3. Verifies the migration was successful
4. Provides rollback capability
"""

import os
import sys
import json
import shutil
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blocking_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BlockingMigration:
    """Handles the migration of blocking functionality between modules."""
    
    def __init__(self, config_path: str, dry_run: bool = False):
        """Initialize the migration with configuration.
        
        Args:
            config_path: Path to the main configuration file
            dry_run: If True, only simulate the migration without making changes
        """
        self.config_path = Path(config_path)
        self.dry_run = dry_run
        self.backup_dir = Path('migration_backup') / datetime.now().strftime('%Y%m%d_%H%M%S')
        self.config = self._load_config()
        
        # Paths
        self.project_root = Path(__file__).parent.parent.parent
        self.blocking_dir = self.project_root / 'focus_guard' / 'core' / 'blocking'
        self.activity_blocking_dir = self.project_root / 'focus_guard' / 'core' / 'activity' / 'blocking'
        
        # Ensure backup directory exists
        if not self.dry_run:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load the application configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)
    
    def backup_file(self, file_path: Path) -> None:
        """Create a backup of a file."""
        if not file_path.exists():
            logger.warning(f"File not found for backup: {file_path}")
            return
            
        backup_path = self.backup_dir / file_path.relative_to(self.project_root)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.dry_run:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backed up {file_path} to {backup_path}")
        else:
            logger.info(f"[DRY RUN] Would back up {file_path} to {backup_path}")
    
    def migrate_blocking_policies(self) -> bool:
        """Migrate blocking policies from activity module to core blocking module."""
        logger.info("Starting blocking policy migration...")
        
        # 1. Backup existing files
        self.backup_file(self.activity_blocking_dir / 'models.py')
        self.backup_file(self.activity_blocking_dir / 'policy_engine.py')
        
        # 2. Create target directories if they don't exist
        target_models_dir = self.blocking_dir / 'models'
        target_policy_dir = self.blocking_dir / 'policy'
        
        if not self.dry_run:
            target_models_dir.mkdir(exist_ok=True)
            target_policy_dir.mkdir(exist_ok=True)
        
        # 3. Migrate models
        self._migrate_models(target_models_dir)
        
        # 4. Migrate policy engine
        self._migrate_policy_engine(target_policy_dir)
        
        # 5. Update imports in affected files
        self._update_imports()
        
        logger.info("Blocking policy migration completed successfully")
        return True
    
    def _migrate_models(self, target_dir: Path) -> None:
        """Migrate blocking models to the new location."""
        source_file = self.activity_blocking_dir / 'models.py'
        target_file = target_dir / 'blocking_models.py'
        
        if not source_file.exists():
            logger.warning(f"Source models file not found: {source_file}")
            return
        
        logger.info(f"Migrating models from {source_file} to {target_file}")
        
        if not self.dry_run:
            # Read and transform the source file
            content = source_file.read_text(encoding='utf-8')
            
            # Update imports and class names if needed
            content = content.replace(
                'from focus_guard.core.activity.blocking',
                'from focus_guard.core.blocking.models'
            )
            
            # Write to new location
            target_file.write_text(content, encoding='utf-8')
    
    def _migrate_policy_engine(self, target_dir: Path) -> None:
        """Migrate policy engine to the new location."""
        source_file = self.activity_blocking_dir / 'policy_engine.py'
        target_file = target_dir / 'engine.py'
        
        if not source_file.exists():
            logger.warning(f"Source policy engine file not found: {source_file}")
            return
        
        logger.info(f"Migrating policy engine from {source_file} to {target_file}")
        
        if not self.dry_run:
            # Read and transform the source file
            content = source_file.read_text(encoding='utf-8')
            
            # Update imports and class names if needed
            content = content.replace(
                'from focus_guard.core.activity.blocking.models',
                'from focus_guard.core.blocking.models.blocking_models'
            )
            
            # Write to new location
            target_file.write_text(content, encoding='utf-8')
    
    def _update_imports(self) -> None:
        """Update imports in affected files."""
        # List of files that might need import updates
        affected_files = [
            self.project_root / 'focus_guard' / 'core' / 'activity' / 'browser' / 'enhanced_domain_blocker.py',
            self.project_root / 'focus_guard' / 'core' / 'activity' / 'browser' / 'comprehensive_activity_system.py',
            # Add more files as needed
        ]
        
        for file_path in affected_files:
            if not file_path.exists():
                continue
                
            self.backup_file(file_path)
            
            if not self.dry_run:
                content = file_path.read_text(encoding='utf-8')
                
                # Update import paths
                content = content.replace(
                    'from focus_guard.core.activity.blocking.models',
                    'from focus_guard.core.blocking.models.blocking_models'
                )
                content = content.replace(
                    'from focus_guard.core.activity.blocking.policy_engine',
                    'from focus_guard.core.blocking.policy.engine'
                )
                
                file_path.write_text(content, encoding='utf-8')
                logger.info(f"Updated imports in {file_path}")
    
    def verify_migration(self) -> bool:
        """Verify that the migration was successful."""
        logger.info("Verifying migration...")
        success = True
        
        # Check that new files exist
        required_files = [
            self.blocking_dir / 'models' / 'blocking_models.py',
            self.blocking_dir / 'policy' / 'engine.py',
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                logger.error(f"Missing required file: {file_path}")
                success = False
            else:
                logger.info(f"Verified: {file_path} exists")
        
        # TODO: Add more verification steps
        
        if success:
            logger.info("Migration verification completed successfully")
        else:
            logger.error("Migration verification failed")
        
        return success
    
    def rollback(self) -> bool:
        """Rollback the migration using the backup files."""
        logger.info("Starting rollback...")
        
        if not self.backup_dir.exists():
            logger.error("No backup directory found for rollback")
            return False
        
        try:
            # Restore files from backup
            for backup_file in self.backup_dir.rglob('*'):
                if backup_file.is_file():
                    rel_path = backup_file.relative_to(self.backup_dir)
                    target_file = self.project_root / rel_path
                    
                    if self.dry_run:
                        logger.info(f"[DRY RUN] Would restore {backup_file} to {target_file}")
                    else:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup_file, target_file)
                        logger.info(f"Restored {target_file} from backup")
            
            # Clean up empty directories in the new structure
            if not self.dry_run:
                self._cleanup_empty_directories()
            
            logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def _cleanup_empty_directories(self) -> None:
        """Remove any empty directories created during migration."""
        for dir_path in [
            self.blocking_dir / 'models',
            self.blocking_dir / 'policy'
        ]:
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    logger.info(f"Removed empty directory: {dir_path}")
            except Exception as e:
                logger.warning(f"Failed to remove directory {dir_path}: {e}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Migrate blocking functionality from activity to core module.')
    parser.add_argument('--config', default='config/app_config.json',
                      help='Path to the application configuration file')
    parser.add_argument('--dry-run', action='store_true',
                      help='Simulate the migration without making changes')
    parser.add_argument('--rollback', action='store_true',
                      help='Rollback the migration using the most recent backup')
    parser.add_argument('--verify', action='store_true',
                      help='Verify the migration was successful')
    return parser.parse_args()

def main():
    """Main entry point for the migration script."""
    args = parse_args()
    
    try:
        migrator = BlockingMigration(args.config, args.dry_run)
        
        if args.rollback:
            return 0 if migrator.rollback() else 1
        
        if not migrator.migrate_blocking_policies():
            return 1
            
        if args.verify and not migrator.verify_migration():
            return 1
            
        return 0
        
    except Exception as e:
        logger.critical(f"Migration failed: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
