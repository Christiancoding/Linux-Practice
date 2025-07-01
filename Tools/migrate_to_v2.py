#!/usr/bin/env python3
"""
Linux Plus Study Tool V2 Migration Script

Migrates existing data and files from the current structure to the new 
enhanced v2 architecture while preserving data integrity and functionality.
"""

import sys
import shutil
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Ensure Python 3 compatibility
if sys.version_info < (3, 8):
    print("This script requires Python 3.8+. Please upgrade.")
    sys.exit(1)

class MigrationManager:
    """Comprehensive migration utility for Linux Plus Study Tool v2."""
    
    def __init__(self, source_dir: str, target_dir: str, dry_run: bool = False):
        """Initialize migration manager with source and target directories."""
        self.source_path = Path(source_dir).resolve()
        self.target_path = Path(target_dir).resolve()
        self.dry_run = dry_run
        self.migration_log = []
        
        self._setup_logging()
        self._validate_directories()
        
    def _setup_logging(self) -> None:
        """Configure comprehensive logging infrastructure."""
        log_level = logging.INFO
        log_format = '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _validate_directories(self) -> None:
        """Validate source and target directory accessibility."""
        if not self.source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_path}")
            
        if not self.source_path.is_dir():
            raise NotADirectoryError(f"Source path is not a directory: {self.source_path}")
            
        # Create target directory if it doesn't exist
        self.target_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Source directory: {self.source_path}")
        self.logger.info(f"Target directory: {self.target_path}")
        self.logger.info(f"Dry run mode: {self.dry_run}")

    def create_backup(self) -> Path:
        """Create a timestamped backup of existing data."""
        backup_dir = self.target_path.parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            if self.target_path.exists() and any(self.target_path.iterdir()):
                if not self.dry_run:
                    shutil.copytree(self.target_path, backup_dir)
                self.logger.info(f"Backup created: {backup_dir}")
                return backup_dir
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            raise
            
        return backup_dir

    def migrate_models(self) -> None:
        """Migrate model files with enhanced structure."""
        model_mappings = [
            ('models/question.py', 'models/question.py'),
            ('models/game_state.py', 'models/game_state.py'),
            ('models/achievements.py', 'models/achievements.py')
        ]
        
        self._copy_files_with_mappings('Models', model_mappings)
        self._create_model_init_file()

    def migrate_controllers(self) -> None:
        """Migrate controller files to enhanced structure."""
        controller_mappings = [
            ('controllers/quiz_controller.py', 'controllers/quiz_controller.py'),
            ('controllers/stats_controller.py', 'controllers/stats_controller.py')
        ]
        
        self._copy_files_with_mappings('Controllers', controller_mappings)
        self._create_controller_init_file()

    def migrate_views(self) -> None:
        """Migrate view files to enhanced structure."""
        view_mappings = [
            ('views/cli_view.py', 'views/cli_view.py'),
            ('views/web_view.py', 'views/web_view.py')
        ]
        
        self._copy_files_with_mappings('Views', view_mappings)
        self._create_view_init_file()

    def migrate_utils(self) -> None:
        """Migrate utility files to enhanced structure."""
        util_mappings = [
            ('utils/cli_playground.py', 'utils/cli_playground.py'),
            ('utils/config.py', 'utils/config.py'),
            ('utils/database.py', 'utils/database.py'),
            ('utils/validators.py', 'utils/validators.py')
        ]
        
        self._copy_files_with_mappings('Utils', util_mappings)
        self._create_utils_init_file()

    def migrate_templates(self) -> None:
        """Migrate template files to enhanced structure."""
        template_mappings = [
            ('templates/achievements.html', 'templates/achievements.html'),
            ('templates/base.html', 'templates/base.html'),
            ('templates/cli_playground.html', 'templates/cli_playground.html'),
            ('templates/error.html', 'templates/error.html'),
            ('templates/import.html', 'templates/import.html'),
            ('templates/index.html', 'templates/index.html'),
            ('templates/quiz.html', 'templates/quiz.html'),
            ('templates/review.html', 'templates/review.html'),
            ('templates/settings.html', 'templates/settings.html'),
            ('templates/stats.html', 'templates/stats.html')
        ]
        
        self._copy_files_with_mappings('Templates', template_mappings)

    def migrate_static_files(self) -> None:
        """Migrate static assets to enhanced structure."""
        static_mappings = [
            ('static/css/style.css', 'static/css/style.css'),
            ('static/js/app.js', 'static/js/app.js'),
            ('static/js/cli_playground.js', 'static/js/cli_playground.js')
        ]
        
        self._copy_files_with_mappings('Static files', static_mappings)

    def migrate_data_files(self) -> None:
        """Migrate data files and create backup copies."""
        data_mappings = [
            ('data/questions.json', 'data/questions.json'),
            ('linux_plus_achievements.json', 'linux_plus_achievements.json'),
            ('linux_plus_history.json', 'linux_plus_history.json'),
            ('web_settings.json', 'web_settings.json')
        ]
        
        self._copy_files_with_mappings('Data files', data_mappings)
        
        # Also create backup copies in data/backup/
        backup_dir = self.target_path / 'data' / 'backup'
        if not self.dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)
            
        backup_mappings = [
            ('data/questions.json', 'data/backup/questions_backup.json'),
            ('linux_plus_achievements.json', 'data/backup/achievements_backup.json'),
            ('linux_plus_history.json', 'data/backup/history_backup.json'),
            ('web_settings.json', 'data/backup/web_settings_backup.json')
        ]
        
        self._copy_files_with_mappings('Data backups', backup_mappings)

    def migrate_cli_sandbox(self) -> None:
        """Migrate CLI sandbox files and structure."""
        sandbox_files = [
            'cli_sandbox/data.csv',
            'cli_sandbox/log.txt', 
            'cli_sandbox/notes.md',
            'cli_sandbox/sample.txt'
        ]
        
        for file_path in sandbox_files:
            source_file = self.source_path / file_path
            target_file = self.target_path / file_path
            
            if source_file.exists():
                self._copy_single_file(source_file, target_file, 'CLI Sandbox')

    def migrate_root_files(self) -> None:
        """Migrate root configuration and entry files."""
        root_mappings = [
            ('main.py', 'main.py'),
            ('requirements.txt', 'requirements.txt')
        ]
        
        self._copy_files_with_mappings('Root files', root_mappings)

    def integrate_vm_project(self, vm_source_dir: Optional[str] = None) -> None:
        """Integrate Linux VM project into new structure."""
        if vm_source_dir is None:
            # Try to find VM project in common locations
            possible_vm_paths = [
                self.source_path.parent / 'Linux_VM',
                self.source_path / 'Linux_VM',
                Path.cwd() / 'Linux_VM'
            ]
            
            vm_path = None
            for path in possible_vm_paths:
                if path.exists():
                    vm_path = path
                    break
                    
            if vm_path is None:
                self.logger.warning("Linux VM project not found. Skipping VM integration.")
                return
        else:
            vm_path = Path(vm_source_dir)
            
        self.logger.info(f"Integrating VM project from: {vm_path}")
        
        # Copy VM project structure to vm_integration/
        vm_target = self.target_path / 'vm_integration'
        
        if not self.dry_run:
            vm_target.mkdir(parents=True, exist_ok=True)
            
            try:
                # Copy specific VM directories if they exist
                vm_dirs = ['controllers', 'models', 'templates', 'utils']
                for dir_name in vm_dirs:
                    vm_source_dir = vm_path / dir_name
                    if vm_source_dir.exists():
                        vm_target_dir = vm_target / dir_name
                        shutil.copytree(vm_source_dir, vm_target_dir, dirs_exist_ok=True)
                        self.logger.info(f"Copied VM {dir_name} to vm_integration/{dir_name}")
                        
            except Exception as e:
                self.logger.error(f"VM integration failed: {e}")

    def _copy_files_with_mappings(self, category: str, mappings: List[Tuple[str, str]]) -> None:
        """Copy files based on source-to-target mappings."""
        self.logger.info(f"Migrating {category}...")
        
        for source_rel, target_rel in mappings:
            source_file = self.source_path / source_rel
            target_file = self.target_path / target_rel
            
            self._copy_single_file(source_file, target_file, category)

    def _copy_single_file(self, source_file: Path, target_file: Path, category: str) -> None:
        """Copy a single file with comprehensive error handling."""
        try:
            if source_file.exists():
                if not self.dry_run:
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, target_file)
                
                self.migration_log.append(f"✓ {source_file} → {target_file}")
                self.logger.debug(f"Copied: {source_file} → {target_file}")
            else:
                self.migration_log.append(f"⚠ Missing: {source_file}")
                self.logger.warning(f"{category} file not found: {source_file}")
                
        except PermissionError:
            self.migration_log.append(f"✗ Permission denied: {source_file}")
            self.logger.error(f"Permission denied copying {source_file}")
        except Exception as e:
            self.migration_log.append(f"✗ Error: {source_file} - {e}")
            self.logger.error(f"Error copying {source_file}: {e}")

    def _create_model_init_file(self) -> None:
        """Create enhanced __init__.py for models package."""
        init_content = '''"""
Enhanced model package for Linux Plus Study Tool v2.

Provides both legacy JSON-based models and new ORM-based models
for seamless migration and extended functionality.
"""

from .question import Question
from .game_state import GameState
from .achievements import Achievements

__all__ = ['Question', 'GameState', 'Achievements']
'''
        self._create_init_file('models/__init__.py', init_content)

    def _create_controller_init_file(self) -> None:
        """Create enhanced __init__.py for controllers package."""
        init_content = '''"""
Enhanced controller package for Linux Plus Study Tool v2.

Provides business logic orchestration with enhanced features including
spaced repetition, adaptive learning, and comprehensive analytics.
"""

from .quiz_controller import QuizController
from .stats_controller import StatsController

__all__ = ['QuizController', 'StatsController']
'''
        self._create_init_file('controllers/__init__.py', init_content)

    def _create_view_init_file(self) -> None:
        """Create enhanced __init__.py for views package."""
        init_content = '''"""
Enhanced view package for Linux Plus Study Tool v2.

Provides multiple interface modalities including CLI, web, and API
with modern responsive design and accessibility features.
"""

from .cli_view import CLIView
from .web_view import app

__all__ = ['CLIView', 'app']
'''
        self._create_init_file('views/__init__.py', init_content)

    def _create_utils_init_file(self) -> None:
        """Create enhanced __init__.py for utils package."""
        init_content = '''"""
Enhanced utilities package for Linux Plus Study Tool v2.

Provides comprehensive utility functions including database management,
validation, configuration, and CLI playground functionality.
"""

from .database import DatabaseManager
from .validators import validate_user_answer, validate_menu_choice
from .config import get_config
from .cli_playground import CLIPlayground

__all__ = ['DatabaseManager', 'validate_user_answer', 'validate_menu_choice', 'get_config', 'CLIPlayground']
'''
        self._create_init_file('utils/__init__.py', init_content)

    def _create_init_file(self, relative_path: str, content: str) -> None:
        """Create an __init__.py file with specified content."""
        if not self.dry_run:
            init_file = self.target_path / relative_path
            init_file.parent.mkdir(parents=True, exist_ok=True)
            init_file.write_text(content.strip() + '\n')
        
        self.migration_log.append(f"✓ Created: {relative_path}")

    def generate_migration_report(self) -> None:
        """Generate comprehensive migration report."""
        report_path = self.target_path / f'migration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        report_content = [
            "="*60,
            "Linux Plus Study Tool V2 Migration Report",
            "="*60,
            f"Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Source Directory: {self.source_path}",
            f"Target Directory: {self.target_path}",
            f"Dry Run Mode: {self.dry_run}",
            "",
            "Migration Results:",
            "-"*20,
            ""
        ]
        
        report_content.extend(self.migration_log)
        
        if not self.dry_run:
            report_path.write_text('\n'.join(report_content))
            
        # Also print to console
        print('\n'.join(report_content))
        self.logger.info(f"Migration report saved to: {report_path}")

    def run_migration(self, include_vm: bool = True, vm_path: Optional[str] = None) -> None:
        """Execute complete migration process."""
        try:
            self.logger.info("Starting Linux Plus Study Tool v2 migration...")
            
            # Create backup of target directory
            self.create_backup()
            
            # Execute migration steps
            migration_steps = [
                ('Models', self.migrate_models),
                ('Controllers', self.migrate_controllers),
                ('Views', self.migrate_views),
                ('Utils', self.migrate_utils),
                ('Templates', self.migrate_templates),
                ('Static Files', self.migrate_static_files),
                ('Data Files', self.migrate_data_files),
                ('CLI Sandbox', self.migrate_cli_sandbox),
                ('Root Files', self.migrate_root_files)
            ]
            
            for step_name, step_function in migration_steps:
                try:
                    step_function()
                    self.logger.info(f"✓ {step_name} migration completed")
                except Exception as e:
                    self.logger.error(f"✗ {step_name} migration failed: {e}")
                    
            # VM integration (optional)
            if include_vm:
                try:
                    self.integrate_vm_project(vm_path)
                    self.logger.info("✓ VM integration completed")
                except Exception as e:
                    self.logger.error(f"✗ VM integration failed: {e}")
                    
            # Generate final report
            self.generate_migration_report()
            
            self.logger.info("Migration process completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Migration process failed: {e}", exc_info=True)
            raise

def main():
    """Primary execution entry point with comprehensive error management."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate Linux Plus Study Tool to v2 architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'source_dir',
        help='Source directory containing existing Linux Plus Study Tool'
    )
    
    parser.add_argument(
        'target_dir', 
        help='Target directory for v2 structure'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform migration simulation without copying files'
    )
    
    parser.add_argument(
        '--vm-path',
        help='Path to Linux VM project for integration'
    )
    
    parser.add_argument(
        '--no-vm',
        action='store_true',
        help='Skip VM project integration'
    )
    
    args = parser.parse_args()
    
    try:
        migrator = MigrationManager(
            source_dir=args.source_dir,
            target_dir=args.target_dir,
            dry_run=args.dry_run
        )
        
        migrator.run_migration(
            include_vm=not args.no_vm,
            vm_path=args.vm_path
        )
        
        print("\n🎉 Migration completed successfully!")
        if args.dry_run:
            print("This was a dry run. Use without --dry-run to perform actual migration.")
            
    except Exception as e:
        logging.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()