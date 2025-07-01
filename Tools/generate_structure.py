#!/usr/bin/env python3
"""
Linux Plus Study Tool V2 - Project Structure Generator

A comprehensive utility for creating the enhanced project structure
for the Linux Plus Study Tool migration with proper organization
and initialization of all required directories and files.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Ensure Python 3 compatibility
if sys.version_info < (3, 8):
    print("This script requires Python 3.8+. Please upgrade.")
    sys.exit(1)

class ProjectStructureGenerator:
    """Advanced project structure generator for Linux Plus Study Tool V2."""
    
    def __init__(self, base_path: Optional[str] = None, preserve_existing: bool = True):
        """
        Initialize project structure generator.
        
        Args:
            base_path: Root directory for project (defaults to current directory)
            preserve_existing: Whether to preserve existing files during migration
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.preserve_existing = preserve_existing
        self.project_root = self.base_path / "linux_plus_study_v2"
        
        self._setup_logging()
        self._define_structure()
    
    def _setup_logging(self) -> None:
        """Configure comprehensive logging infrastructure."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    self.base_path / f'structure_generator_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
                )
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Project Structure Generator initialized")
    
    def _define_structure(self) -> None:
        """Define the complete project structure with directories and initial files."""
        self.directory_structure = {
            'api': {
                '__init__.py': self._get_init_content(),
                'v1': {
                    '__init__.py': self._get_init_content(),
                    'endpoints': {
                        '__init__.py': self._get_init_content(),
                        'quiz.py': self._get_api_endpoint_template('quiz'),
                        'stats.py': self._get_api_endpoint_template('stats'),
                        'auth.py': self._get_api_endpoint_template('auth'),
                        'practice.py': self._get_api_endpoint_template('practice'),
                    },
                    'middleware': {
                        '__init__.py': self._get_init_content(),
                        'auth.py': self._get_middleware_template('auth'),
                        'rate_limiting.py': self._get_middleware_template('rate_limiting'),
                    }
                },
                'v2': {
                    '__init__.py': self._get_init_content(),
                }
            },
            'cli_sandbox': {
                'data.csv': 'name,age,city\nJohn,25,New York\nJane,30,Los Angeles\nBob,35,Chicago',
                'log.txt': 'INFO: System started\nERROR: Failed to connect\nINFO: Retrying connection\nWARNING: Low disk space\nINFO: Connection established',
                'notes.md': '# CLI Sandbox Notes\n\nThis is a practice environment for Linux commands.\n\n## Available Files\n- data.csv: Sample CSV data\n- log.txt: System log entries\n- sample.txt: Text file for practice\n',
                'sample.txt': 'This is a sample text file for practicing Linux commands.\nYou can use commands like cat, grep, head, tail, etc.\nFeel free to experiment with text processing commands.',
                'environments': {
                    'beginner': {},
                    'intermediate': {},
                    'advanced': {}
                }
            },
            'controllers': {
                '__init__.py': self._get_init_content(),
                'quiz_controller.py': self._get_controller_template('quiz'),
                'stats_controller.py': self._get_controller_template('stats'),
                'auth_controller.py': self._get_controller_template('auth'),
                'learning_controller.py': self._get_controller_template('learning'),
                'practice_controller.py': self._get_controller_template('practice'),
            },
            'core': {
                '__init__.py': self._get_init_content(),
                'algorithms': {
                    '__init__.py': self._get_init_content(),
                    'spaced_repetition.py': self._get_algorithm_template('spaced_repetition'),
                    'adaptive_learning.py': self._get_algorithm_template('adaptive_learning'),
                    'analytics.py': self._get_algorithm_template('analytics'),
                },
                'security': {
                    '__init__.py': self._get_init_content(),
                    'encryption.py': self._get_security_template('encryption'),
                    'validators.py': self._get_security_template('validators'),
                    'auth.py': self._get_security_template('auth'),
                },
                'integrations': {
                    '__init__.py': self._get_init_content(),
                    'calendar.py': self._get_integration_template('calendar'),
                    'cloud_storage.py': self._get_integration_template('cloud_storage'),
                    'notification.py': self._get_integration_template('notification'),
                }
            },
            'data': {
                'migrations': {},
                'questions.json': '{}',  # Placeholder - will be migrated from existing
                'schemas': {
                    '__init__.py': self._get_init_content(),
                    'quiz.py': self._get_schema_template('quiz'),
                    'user.py': self._get_schema_template('user'),
                    'analytics.py': self._get_schema_template('analytics'),
                },
                'seed_data': {}
            },
            'models': {
                '__init__.py': self._get_init_content(),
                'achievements.py': self._get_model_template('achievements'),
                'game_state.py': self._get_model_template('game_state'),
                'question.py': self._get_model_template('question'),
                'user.py': self._get_model_template('user'),
                'session.py': self._get_model_template('session'),
                'analytics.py': self._get_model_template('analytics'),
                'practice_environment.py': self._get_model_template('practice_environment'),
            },
            'services': {
                '__init__.py': self._get_init_content(),
                'quiz_service.py': self._get_service_template('quiz'),
                'learning_service.py': self._get_service_template('learning'),
                'analytics_service.py': self._get_service_template('analytics'),
                'notification_service.py': self._get_service_template('notification'),
                'vm_service.py': self._get_service_template('vm'),
            },
            'static': {
                'css': {
                    'style.css': self._get_css_template(),
                    'themes': {
                        'dark.css': self._get_theme_template('dark'),
                        'light.css': self._get_theme_template('light'),
                    },
                    'components': {}
                },
                'js': {
                    'app.js': self._get_js_template('app'),
                    'cli_playground.js': self._get_js_template('cli_playground'),
                    'modules': {
                        'quiz.js': self._get_js_module_template('quiz'),
                        'analytics.js': self._get_js_module_template('analytics'),
                        'auth.js': self._get_js_module_template('auth'),
                        'practice.js': self._get_js_module_template('practice'),
                    },
                    'components': {}
                },
                'assets': {
                    'images': {},
                    'videos': {},
                    'audio': {}
                },
                'pwa': {
                    'manifest.json': self._get_pwa_manifest(),
                    'service-worker.js': self._get_service_worker(),
                }
            },
            'templates': {
                'achievements.html': self._get_template('achievements'),
                'base.html': self._get_template('base'),
                'cli_playground.html': self._get_template('cli_playground'),
                'error.html': self._get_template('error'),
                'import.html': self._get_template('import'),
                'index.html': self._get_template('index'),
                'quiz.html': self._get_template('quiz'),
                'review.html': self._get_template('review'),
                'settings.html': self._get_template('settings'),
                'stats.html': self._get_template('stats'),
                'auth': {
                    'login.html': self._get_auth_template('login'),
                    'register.html': self._get_auth_template('register'),
                    'profile.html': self._get_auth_template('profile'),
                },
                'learning': {
                    'dashboard.html': self._get_learning_template('dashboard'),
                    'study_plan.html': self._get_learning_template('study_plan'),
                    'flashcards.html': self._get_learning_template('flashcards'),
                    'simulation.html': self._get_learning_template('simulation'),
                },
                'admin': {}
            },
            'tests': {
                '__init__.py': self._get_init_content(),
                'unit': {
                    '__init__.py': self._get_init_content(),
                },
                'integration': {
                    '__init__.py': self._get_init_content(),
                },
                'e2e': {
                    '__init__.py': self._get_init_content(),
                },
                'fixtures': {}
            },
            'utils': {
                '__init__.py': self._get_init_content(),
                'cli_playground.py': self._get_util_template('cli_playground'),
                'config.py': self._get_util_template('config'),
                'database.py': self._get_util_template('database'),
                'validators.py': self._get_util_template('validators'),
                'cache.py': self._get_util_template('cache'),
                'monitoring.py': self._get_util_template('monitoring'),
                'deployment.py': self._get_util_template('deployment'),
            },
            'views': {
                '__init__.py': self._get_init_content(),
                'cli_view.py': self._get_view_template('cli'),
                'web_view.py': self._get_view_template('web'),
                'api_view.py': self._get_view_template('api'),
                'admin_view.py': self._get_view_template('admin'),
            },
            'vm_integration': {
                '__init__.py': self._get_init_content(),
                'controllers': {
                    '__init__.py': self._get_init_content(),
                },
                'models': {
                    '__init__.py': self._get_init_content(),
                },
                'templates': {}
            },
            'docker': {
                'Dockerfile': self._get_dockerfile(),
                'docker-compose.yml': self._get_docker_compose(),
                'scripts': {}
            },
            'docs': {
                'api': {},
                'deployment': {},
                'user_guide': {}
            },
            'config': {
                '__init__.py': self._get_init_content(),
                'development.py': self._get_config_template('development'),
                'production.py': self._get_config_template('production'),
                'testing.py': self._get_config_template('testing'),
            }
        }
        
        # Root level files
        self.root_files = {
            'main.py': self._get_main_template(),
            'requirements.txt': self._get_requirements(),
            'pyproject.toml': self._get_pyproject(),
            'alembic.ini': self._get_alembic_config(),
            '.env.example': self._get_env_example(),
            'README.md': self._get_readme(),
            '.gitignore': self._get_gitignore(),
        }
    
    def generate_structure(self) -> bool:
        """
        Generate the complete project structure.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Starting project structure generation at: {self.project_root}")
            
            # Create root directory
            self._create_directory(self.project_root)
            
            # Generate directory structure
            self._create_structure(self.project_root, self.directory_structure)
            
            # Create root level files
            self._create_root_files()
            
            # Copy existing files if they exist
            self._migrate_existing_files()
            
            self.logger.info("Project structure generation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate project structure: {e}", exc_info=True)
            return False
    
    def _create_structure(self, base_path: Path, structure: Dict) -> None:
        """Recursively create directory structure and files."""
        for name, content in structure.items():
            current_path = base_path / name
            
            if isinstance(content, dict):
                # It's a directory
                self._create_directory(current_path)
                self._create_structure(current_path, content)
            else:
                # It's a file
                self._create_file(current_path, content)
    
    def _create_directory(self, path: Path) -> None:
        """Create a directory with proper error handling."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {path}")
        except PermissionError:
            self.logger.error(f"Permission denied creating directory: {path}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating directory {path}: {e}")
            raise
    
    def _create_file(self, path: Path, content: str) -> None:
        """Create a file with content and proper error handling."""
        try:
            if self.preserve_existing and path.exists():
                self.logger.info(f"Preserving existing file: {path}")
                return
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.debug(f"Created file: {path}")
        except PermissionError:
            self.logger.error(f"Permission denied creating file: {path}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating file {path}: {e}")
            raise
    
    def _create_root_files(self) -> None:
        """Create root level configuration files."""
        for filename, content in self.root_files.items():
            file_path = self.project_root / filename
            self._create_file(file_path, content)
    
    def _migrate_existing_files(self) -> None:
        """Migrate existing files from current project if they exist."""
        migration_map = {
            'linux_plus_achievements.json': 'linux_plus_achievements.json',
            'linux_plus_history.json': 'linux_plus_history.json',
            'web_settings.json': 'web_settings.json',
            'data/questions.json': 'data/questions.json',
        }
        
        for source, destination in migration_map.items():
            source_path = self.base_path / source
            dest_path = self.project_root / destination
            
            if source_path.exists():
                try:
                    import shutil
                    shutil.copy2(source_path, dest_path)
                    self.logger.info(f"Migrated existing file: {source} -> {destination}")
                except Exception as e:
                    self.logger.warning(f"Failed to migrate {source}: {e}")
    
    # Template methods for generating initial file content
    def _get_init_content(self) -> str:
        """Generate __init__.py content."""
        return '"""Package initialization."""\n'
    
    def _get_main_template(self) -> str:
        """Generate main.py template."""
        return '''#!/usr/bin/env python3
"""
Linux Plus Study Tool V2 - Main Application Entry Point

Enhanced study tool with modern architecture, spaced repetition,
and comprehensive learning analytics.
"""

import sys
import logging
from pathlib import Path

# Ensure Python 3 compatibility
if sys.version_info < (3, 8):
    print("This application requires Python 3.8+. Please upgrade.")
    sys.exit(1)

def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s: %(message)s'
    )

def main():
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Application initialization will be implemented here
        logger.info("Linux Plus Study Tool V2 starting...")
        print("Welcome to Linux Plus Study Tool V2!")
        print("This is the enhanced version with modern features.")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    def _get_requirements(self) -> str:
        """Generate requirements.txt."""
        return '''# Core dependencies
Flask>=2.3.0
SQLAlchemy>=2.0.0
Flask-SQLAlchemy>=3.0.0
Flask-Login>=0.6.0
Flask-WTF>=1.1.0
bcrypt>=4.0.0
python-dotenv>=1.0.0

# Database
alembic>=1.12.0
psycopg2-binary>=2.9.0  # PostgreSQL support

# Caching and performance
redis>=4.6.0
celery>=5.3.0

# API and serialization
marshmallow>=3.20.0
Flask-CORS>=4.0.0

# Monitoring and logging
sentry-sdk>=1.32.0

# Development and testing
pytest>=7.4.0
pytest-flask>=1.2.0
pytest-cov>=4.1.0
black>=23.7.0
flake8>=6.0.0

# Optional VM integration
libvirt-python>=9.7.0  # For VM management
paramiko>=3.3.0        # For SSH connections

# CLI enhancements
click>=8.1.0
rich>=13.5.0
'''
    
    def _get_controller_template(self, name: str) -> str:
        """Generate controller template."""
        class_name = f"{name.capitalize()}Controller"
        return f'''"""
{name.capitalize()} Controller - Business Logic Management

Handles {name} operations with enhanced error handling
and integration with modern learning algorithms.
"""

import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class {class_name}:
    """Enhanced {name} controller with modern architecture."""
    
    def __init__(self):
        """Initialize {name} controller."""
        self.logger = logger
        self.logger.info(f"{class_name} initialized")
    
    # Implementation will be added during migration
    pass
'''
    
    def _get_model_template(self, name: str) -> str:
        """Generate model template."""
        class_name = f"{name.capitalize().replace('_', '')}"
        return f'''"""
{name.capitalize()} Model - Data Management

Enhanced model with SQLAlchemy ORM support and
backward compatibility with JSON-based storage.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import logging

Base = declarative_base()
logger = logging.getLogger(__name__)

class {class_name}(Base):
    """Enhanced {name} model with ORM support."""
    
    __tablename__ = '{name}s'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields will be added during migration
    
    def __repr__(self):
        return f"<{class_name}(id={{self.id}})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for JSON compatibility."""
        return {{
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }}
'''
    
    def _get_api_endpoint_template(self, name: str) -> str:
        """Generate API endpoint template."""
        return f'''"""
{name.capitalize()} API Endpoints

RESTful API endpoints for {name} operations with
comprehensive validation and error handling.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
import logging

logger = logging.getLogger(__name__)

{name}_bp = Blueprint('{name}', __name__, url_prefix='/api/v1/{name}')

@{name}_bp.route('/', methods=['GET'])
@login_required
def get_{name}_list():
    """Get list of {name} items."""
    try:
        # Implementation will be added
        return jsonify({{'message': 'Not implemented yet'}}), 501
    except Exception as e:
        logger.error(f"Error in get_{name}_list: {{e}}")
        return jsonify({{'error': 'Internal server error'}}), 500

@{name}_bp.route('/<int:item_id>', methods=['GET'])
@login_required
def get_{name}_item(item_id):
    """Get specific {name} item."""
    try:
        # Implementation will be added
        return jsonify({{'message': 'Not implemented yet'}}), 501
    except Exception as e:
        logger.error(f"Error in get_{name}_item: {{e}}")
        return jsonify({{'error': 'Internal server error'}}), 500
'''
    
    def _get_template(self, name: str) -> str:
        """Generate HTML template."""
        title = name.replace('_', ' ').title()
        return f'''{{%- extends "base.html" %}}

{{%- block title %}}{title}{{%- endblock %}}

{{%- block content %}}
<div class="container">
    <h1>{title}</h1>
    <p>Enhanced {name} interface with modern features.</p>
    <!-- Implementation will be migrated from existing templates -->
</div>
{{%- endblock %}}

{{%- block scripts %}}
<script src="{{{{ url_for('static', filename='js/modules/{name}.js') }}}}"></script>
{{%- endblock %}}
'''
    
    def _get_css_template(self) -> str:
        """Generate CSS template."""
        return '''/* Linux Plus Study Tool V2 - Enhanced Styles */

:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    --success-color: #059669;
    --error-color: #dc2626;
    --warning-color: #d97706;
    --background-color: #f8fafc;
    --text-color: #1e293b;
    --border-color: #e2e8f0;
}

/* Base styles with modern enhancements */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: var(--background-color);
    color: var(--text-color);
    line-height: 1.6;
}

/* Enhanced component styles will be added during migration */
'''
    
    def _get_js_template(self, name: str) -> str:
        """Generate JavaScript template."""
        return f'''/**
 * {name.upper()} Module - Enhanced JavaScript
 * 
 * Modern ES6+ JavaScript with modular architecture
 * and comprehensive error handling.
 */

class {name.capitalize()}Manager {{
    constructor() {{
        this.initialized = false;
        this.init();
    }}
    
    async init() {{
        try {{
            console.log('{name.capitalize()}Manager initializing...');
            // Enhanced initialization logic will be added
            this.initialized = true;
        }} catch (error) {{
            console.error(`{name.capitalize()}Manager initialization failed:`, error);
        }}
    }}
}}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {{
    window.{name}Manager = new {name.capitalize()}Manager();
}});

export {{ {name.capitalize()}Manager }};
'''
    
    # Additional template methods would go here...
    # (I'll add placeholders for the remaining methods to keep the code manageable)
    
    def _get_service_template(self, name: str) -> str:
        return f'"""Service layer for {name} operations."""\n# Implementation pending'
    
    def _get_util_template(self, name: str) -> str:
        return f'"""Utility functions for {name}."""\n# Implementation pending'
    
    def _get_view_template(self, name: str) -> str:
        return f'"""View layer for {name} interface."""\n# Implementation pending'
    
    def _get_algorithm_template(self, name: str) -> str:
        return f'"""Algorithm implementation for {name}."""\n# Implementation pending'
    
    def _get_security_template(self, name: str) -> str:
        return f'"""Security utilities for {name}."""\n# Implementation pending'
    
    def _get_integration_template(self, name: str) -> str:
        return f'"""Integration utilities for {name}."""\n# Implementation pending'
    
    def _get_schema_template(self, name: str) -> str:
        return f'"""Database schema for {name}."""\n# Implementation pending'
    
    def _get_middleware_template(self, name: str) -> str:
        return f'"""Middleware for {name}."""\n# Implementation pending'
    
    def _get_auth_template(self, name: str) -> str:
        return f'<!-- Auth template for {name} -->\n<!-- Implementation pending -->'
    
    def _get_learning_template(self, name: str) -> str:
        return f'<!-- Learning template for {name} -->\n<!-- Implementation pending -->'
    
    def _get_theme_template(self, name: str) -> str:
        return f'/* {name.capitalize()} theme styles */\n/* Implementation pending */'
    
    def _get_js_module_template(self, name: str) -> str:
        return f'// {name.capitalize()} module\n// Implementation pending'
    
    def _get_config_template(self, name: str) -> str:
        return f'"""Configuration for {name} environment."""\n# Implementation pending'
    
    def _get_pwa_manifest(self) -> str:
        return '''{}'''  # JSON placeholder
    
    def _get_service_worker(self) -> str:
        return '// Service worker implementation pending'
    
    def _get_dockerfile(self) -> str:
        return '''FROM python:3.11-slim
# Docker configuration pending'''
    
    def _get_docker_compose(self) -> str:
        return '''version: '3.8'
# Docker Compose configuration pending'''
    
    def _get_pyproject(self) -> str:
        return '''[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "linux-plus-study-v2"
version = "2.0.0"
description = "Enhanced Linux Plus certification study tool"
'''
    
    def _get_alembic_config(self) -> str:
        return '''# Alembic configuration
[alembic]
script_location = data/migrations
'''
    
    def _get_env_example(self) -> str:
        return '''# Environment variables example
FLASK_ENV=development
DATABASE_URL=sqlite:///linux_plus.db
SECRET_KEY=your-secret-key-here
'''
    
    def _get_readme(self) -> str:
        return '''# Linux Plus Study Tool V2

Enhanced version with modern architecture and advanced learning features.

## Setup Instructions

1. Create virtual environment: `python -m venv venv`
2. Activate: `source venv/bin/activate` (Linux/Mac) or `venv\\Scripts\\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Run application: `python main.py`

## New Features

- Spaced repetition system
- Adaptive learning algorithms
- Modern web interface
- API support
- Enhanced analytics

More documentation coming soon.
'''
    
    def _get_gitignore(self) -> str:
        return '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
*.log
.env
linux_plus.db
'''

def main():
    """Main execution function with user interaction."""
    print("Linux Plus Study Tool V2 - Project Structure Generator")
    print("=" * 55)
    
    try:
        # Get user preferences
        base_path = input("Enter base directory (press Enter for current directory): ").strip()
        if not base_path:
            base_path = None
        
        preserve = input("Preserve existing files? (Y/n): ").strip().lower()
        preserve_existing = preserve != 'n'
        
        # Initialize generator
        generator = ProjectStructureGenerator(base_path, preserve_existing)
        
        # Confirm generation
        print(f"\nWill create project structure at: {generator.project_root}")
        confirm = input("Proceed? (Y/n): ").strip().lower()
        
        if confirm == 'n':
            print("Operation cancelled.")
            return
        
        # Generate structure
        success = generator.generate_structure()
        
        if success:
            print("\n✅ Project structure generated successfully!")
            print(f"📁 Location: {generator.project_root}")
            print("\n📋 Next steps:")
            print("1. Navigate to the new directory")
            print("2. Create virtual environment: python -m venv venv")
            print("3. Activate virtual environment")
            print("4. Install dependencies: pip install -r requirements.txt")
            print("5. Begin migration of existing code")
        else:
            print("\n❌ Project structure generation failed. Check logs for details.")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logging.error("Unexpected error in main", exc_info=True)

if __name__ == "__main__":
    main()