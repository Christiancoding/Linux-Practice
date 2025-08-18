#!/usr/bin/env python3
"""
Web View for the Linux+ Study Game using Flask + pywebview.
Creates a desktop app with modern web interface.
"""

import webview
import threading
import time
import os
import requests
from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime
import logging
import traceback
import atexit
import secrets
import hashlib
#from utils.cli_playground import get_cli_playground
import subprocess
import shlex
import re
from urllib.parse import urlparse
#try:
#    from vm_integration.utils.vm_manager import VMManager
#except ImportError:
#    VMManager = None

#from vm_integration.utils.ssh_manager import SSHManager
try:
    import libvirt  # type: ignore
except ImportError:
    libvirt = None
    logging.warning("libvirt-python not available. VM functionality will be limited.")

# Add proper type imports
from typing import Any, Dict, List, Optional, Union, Tuple, Set, cast, TypedDict, Protocol, runtime_checkable, Callable

try:
    from utils.database import initialize_database_pool, get_database_manager, cleanup_database_connections, DatabasePoolManager
except ImportError as e:
    logging.error(f"Database utilities import failed: {e}")
    # Import the real DatabasePoolManager for type hints
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from utils.database import DatabasePoolManager
        from controllers.stats_controller import DetailedStatistics, ReviewQuestionsData
    
    # Define fallback functions with proper type annotations
    def initialize_database_pool(db_type: str = "sqlite", enable_pooling: bool = True) -> "DatabasePoolManager":
        # This will never actually return None in practice, but we need to satisfy the type checker
        raise ImportError("Database utilities not available")
    
    def get_database_manager() -> Optional["DatabasePoolManager"]:
        return None
    
    def cleanup_database_connections() -> None:
        pass

from utils.config import get_config_value
from werkzeug.utils import secure_filename
from typing import Any, Dict, Optional
from utils.persistence_manager import get_persistence_manager

# Define TypedDict for question object structure
class QuestionExportDict(TypedDict):
    """Type definition for question export data structure."""
    id: int
    question: str
    options: List[str]
    correct_answer_index: int
    correct_answer_letter: str
    correct_answer_text: str
    category: str
    explanation: str

# TypedDict for API request data
class QuizStartRequestData(TypedDict, total=False):
    """Type definition for quiz start request data."""
    mode: str
    category: Optional[str]
    num_questions: Optional[int]

class AnswerSubmissionData(TypedDict, total=False):
    """Type definition for answer submission data."""
    answer_index: int

class CategoryRequestData(TypedDict, total=False):
    """Type definition for category-based request data."""
    category: Optional[str]

class VMRequestData(TypedDict, total=False):
    """Type definition for VM-related request data."""
    vm_name: Optional[str]
    snapshot_name: Optional[str]
    description: str
    port: int
    name: Optional[str]

class CommandRequestData(TypedDict, total=False):
    """Type definition for command execution request data."""
    command: str

class SettingsRequestData(TypedDict):
    """Type definition for settings request data."""
    focusMode: bool
    breakReminder: bool
    debugMode: bool
    pointsPerQuestion: int
    streakBonus: int
    maxStreakBonus: int

class FullscreenRequestData(TypedDict, total=False):
    """Type definition for fullscreen request data."""
    enable: bool

class RemoveFromReviewData(TypedDict, total=False):
    """Type definition for remove from review request data."""
    question_text: str

class TTYDRequestData(TypedDict, total=False):
    """Type definition for ttyd request data."""
    vm_name: str
    port: int
    id: int
    question: str
    category: str
    options: List[str]
    correct_answer_index: int
    correct_answer_letter: str
    correct_answer_text: str
    explanation: str

class ExportMetadataDict(TypedDict):
    """Type definition for export metadata structure."""
    title: str
    export_date: str
    total_questions: int
    categories: List[str]

class ExportDataDict(TypedDict):
    """Type definition for full export data structure."""
    metadata: ExportMetadataDict
    questions: List[QuestionExportDict]

#cli_playground = get_cli_playground()

def setup_database_for_web() -> Optional["DatabasePoolManager"]:
    """Initialize database connection pooling for web mode."""
    try:
        # Determine database type from configuration or environment
        db_type = os.environ.get('DATABASE_TYPE', 'sqlite')
        enable_pooling = get_config_value('web', 'enable_db_pooling', True)
        
        # Initialize connection pool
        db_manager = initialize_database_pool(db_type, enable_pooling)
        
        # Log pool status
        pool_status = db_manager.get_pool_status()
        if pool_status.get("pooling_enabled"):
            print(f"Database pooling enabled - Pool size: {pool_status.get('pool_size', 'N/A')}")
        else:
            print("Database pooling disabled (SQLite or manual override)")
            
        return db_manager
    except ImportError:
        print("Database utilities not available - running without connection pooling")
        return None
    except Exception as e:
        print(f"Failed to setup database pooling: {e}")
        return None

# Add this class definition after the other type definitions
@runtime_checkable
class StatsControllerProtocol(Protocol):
    """Protocol defining the interface for StatsController."""
    def get_detailed_statistics(self) -> "DetailedStatistics": ...
    def get_achievements_data(self) -> Dict[str, Union[List[Any], Dict[str, Any], int]]: ...
    def get_leaderboard_data(self) -> List[Any]: ...
    def clear_statistics(self) -> bool: ...
    def get_review_questions_data(self) -> "ReviewQuestionsData": ...  # Updated return type
    def remove_from_review_list(self, question_text: str) -> bool: ...
    def cleanup_missing_review_questions(self, missing_questions: List[str]) -> int: ...


# Initialize analytics for current session
def get_current_user_id():
    from flask import session
    # Try to get user_id from session, if not present, default to anonymous
    # This prevents automatic random user creation and maintains consistency
    return session.get('user_id', 'anonymous')

def ensure_analytics_user_sync():
    """Analytics removed - placeholder function."""
    return 'anonymous', None

class LinuxPlusStudyWeb:
    """Web interface using Flask + pywebview for desktop app experience."""
    
    def __init__(self, game_state: Any, debug: bool = False):
        self.game_state = game_state
        self.app = Flask(__name__, 
                        template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
                        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))
        self.debug = debug
        self.window = None
        
        # Initialize with proper type annotations
        self.cli_history: List[str] = []
        self.current_category_filter: Optional[str] = None
        self.current_question_data: Any = None
        self.current_question_index: int = -1
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Add caching to reduce lag
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300  # Cache static files for 5 minutes
        self.app.config['TEMPLATES_AUTO_RELOAD'] = False  # Disable template auto-reload in production
    
        # Generate secure secret key
        import secrets
        self.app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
    
        # Session configuration for better performance
        self.app.config['SESSION_TYPE'] = 'filesystem'
        self.app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

        # Initialize controllers with proper error handling
        try:
            from controllers.quiz_controller import QuizController
            from controllers.stats_controller import StatsController
            
            self.quiz_controller = QuizController(game_state)
            
            # Load and apply settings to quiz controller
            settings = self._load_web_settings()
            if hasattr(self.quiz_controller, 'update_settings'):
                self.quiz_controller.update_settings(settings)
            
            self.stats_controller: StatsControllerProtocol = StatsController(game_state)
        except ImportError as e:
            self.logger.error(f"Failed to import controllers: {e}")
            raise ImportError(f"Controller import failed: {e}")
        except Exception as e:
            self.logger.error(f"Failed to initialize controllers: {e}")
            raise RuntimeError(f"Controller initialization failed: {e}")
    
        # Setup CLI playground routes first
        self.setup_cli_playground_routes(self.app)
        
        # Setup all routes
        self.setup_routes()
        
        # Setup VM routes
        self.setup_vm_routes()
        
        # Setup export/import routes
        self.setup_export_import_routes()
        
        # Analytics removed
    def set_debug_mode(self, enabled: bool = True):
        """Toggle debug mode for the application."""
        self.debug = enabled
        self.app.config['DEBUG'] = enabled
        return {'success': True, 'debug': enabled}
    def _should_show_break_reminder(self) -> bool:
        """Check if break reminder should be shown based on current settings."""
        disabled_modes = {'daily_challenge', 'pop_quiz', 'quick_fire', 'mini_quiz'}
        if self.quiz_controller.current_quiz_mode in disabled_modes:
            return False
        try:
            settings: Dict[str, Any] = self._load_web_settings()
            break_interval = int(settings.get('breakReminder', 10))
            # Check if break reminders are enabled (interval > 0) and threshold met
            return (break_interval > 0 and 
                    self.quiz_controller.questions_since_break >= break_interval)
        except Exception:
            return False

    def _get_break_interval(self) -> int:
        """Get the current break reminder interval from settings."""
        try:
            settings: Dict[str, Any] = self._load_web_settings()
            return int(settings.get('breakReminder', 10))
        except Exception:
            return 10

    def _load_web_settings(self) -> Dict[str, Any]:
        """Load settings from web_settings.json file using persistence manager."""
        try:
            persistence_manager = get_persistence_manager()
            return persistence_manager.load_settings()
        except Exception as e:
            print(f"Error loading web settings: {e}")
        # Return default settings if file doesn't exist or can't be loaded
        return {'focusMode': False, 'breakReminder': 10}

    def _ensure_settings_applied(self) -> None:
        """Ensure current settings are applied to quiz controller."""
        try:
            settings = self._load_web_settings()
            if hasattr(self.quiz_controller, 'update_settings'):
                self.quiz_controller.update_settings(settings)
        except Exception as e:
            print(f"Error ensuring settings applied: {e}")

    def _apply_settings_to_game_state(self, settings: Dict[str, Any]) -> bool:
        """Apply settings changes to the current game state and controllers."""
        try:
            # Update quiz controller settings
            if hasattr(self.quiz_controller, 'update_settings'):
                self.quiz_controller.update_settings(settings)
            # Update debug mode
            if settings.get('debugMode', False):
                self.app.config['DEBUG'] = True
                self.debug = True
            else:
                self.app.config['DEBUG'] = False
                self.debug = False
            # Update game state scoring settings
            if hasattr(self.game_state, 'update_scoring_settings'):
                self.game_state.update_scoring_settings(
                    points_per_question=int(settings.get('pointsPerQuestion', 10)),
                    streak_bonus=int(settings.get('streakBonus', 5)),
                    max_streak_bonus=int(settings.get('maxStreakBonus', 50))
                )
            return True
        except Exception as e:
            print(f"Error applying settings to game state: {e}")
            return False

    def toggle_fullscreen(self, enable: bool = True) -> Dict[str, Any]:
        """Toggle application window fullscreen."""
        try:
            if hasattr(self, 'window') and self.window:
                self.window.fullscreen = enable
                return {'success': True, 'fullscreen': enable}
            return {'success': False, 'error': 'Window not available'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def is_fullscreen(self) -> Dict[str, Any]:
        """Check if window is in fullscreen mode."""
        try:
            if hasattr(self, 'window') and self.window:
                return {'success': True, 'fullscreen': getattr(self.window, 'fullscreen', False)}
            return {'success': False, 'fullscreen': False}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def setup_app_teardown(self, app: Flask) -> None:
        """Setup application teardown handlers for proper cleanup."""

        @app.teardown_appcontext
        def close_db_session(error: Optional[BaseException]) -> None:
            """Close database session after each request."""
            try:
                db_manager = get_database_manager()
                if db_manager and hasattr(db_manager, 'scoped_session_factory') and db_manager.scoped_session_factory:
                    db_manager.scoped_session_factory.remove()
            except Exception as e:
                logging.error(f"Error closing database session: {e}")
        
        # Store reference to prevent "not accessed" warning
        self.close_db_session_handler = close_db_session

        @app.teardown_request
        def cleanup_request(exception: Optional[BaseException] = None) -> None:
            """Clean up resources after each request."""
            try:
                if exception:
                    logging.error(f"Request error: {exception}")
            except Exception as e:
                logging.error(f"Error in request cleanup: {e}")
        
        # Store reference to prevent "not accessed" warning
        self.cleanup_request_handler = cleanup_request
    
    # Register cleanup on application shutdown
    import atexit
    atexit.register(cleanup_database_connections)
    def setup_cli_playground_routes(self, app: Flask) -> None:
        """Setup CLI playground API routes"""
        
        # Store command history in memory with proper type annotation
        self.cli_history = []
        
        @app.route('/api/cli/execute', methods=['POST'])
        def execute_cli_command():
            try:
                data = cast(CommandRequestData, request.get_json() or {})
                command: str = data.get('command', '').strip()
                
                if not command:
                    return jsonify({'success': False, 'error': 'No command provided'})
                
                # Add to history
                self.cli_history.append(command)
                
                # Handle built-in commands
                if command == 'clear':
                    return jsonify({'success': True, 'output': 'CLEAR_SCREEN'})
                
                if command == 'help':
                    help_text = self._get_help_text()
                    return jsonify({'success': True, 'output': help_text})
                
                # Handle simulated file system commands
                output = self._simulate_command(command)
                if output is not None:
                    return jsonify({'success': True, 'output': output})
                
                # For real system commands (restricted set)
                allowed_commands = ['ls', 'pwd', 'whoami', 'date', 'echo', 'cat', 'grep', 'find', 'wc', 'head', 'tail']
                cmd_parts = shlex.split(command)
                
                if not cmd_parts or cmd_parts[0] not in allowed_commands:
                    return jsonify({
                        'success': False, 
                        'error': f'Command "{cmd_parts[0] if cmd_parts else command}" not available in this sandbox environment.\nType "help" to see available commands.'
                    })
                
                # Execute safe command
                try:
                    result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=10)
                    output = result.stdout if result.returncode == 0 else result.stderr
                    return jsonify({'success': True, 'output': output})
                except subprocess.TimeoutExpired:
                    return jsonify({'success': False, 'error': 'Command timed out'})
                except Exception as e:
                    return jsonify({'success': False, 'error': f'Error: {str(e)}'})
                    
            except Exception as e:
                return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

        # Store reference to prevent "not accessed" warning
        self.execute_cli_command_handler = execute_cli_command

        @app.route('/api/cli/clear', methods=['POST'])
        def clear_cli_history():
            """Clear CLI command history"""
            try:
                self.cli_history = []
                
                return jsonify({
                    'success': True,
                    'message': 'History cleared'
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Server error: {str(e)}'
                })

        # Store reference to prevent "not accessed" warning
        self.clear_cli_history_handler = clear_cli_history

        @app.route('/api/cli/commands', methods=['GET'])
        def get_available_commands():
            """Get list of available CLI commands"""
            try:
                commands = list(cli_playground.safe_commands.keys())
                commands.sort()
                
                command_descriptions = {
                    # Basic File Operations
                    'ls': 'List directory contents',
                    'pwd': 'Print working directory',
                    'cd': 'Change directory',
                    'cat': 'Display file contents',
                    'mkdir': 'Create directory',
                    'touch': 'Create empty file',
                    'rm': 'Remove file',
                    'cp': 'Copy file',
                    'mv': 'Move/rename file',
                    
                    # Text Processing & Search
                    'grep': 'Search for pattern in file',
                    'head': 'Display first lines of file',
                    'tail': 'Display last lines of file',
                    'wc': 'Word, line, character count',
                    'sort': 'Sort lines in file',
                    'uniq': 'Remove duplicate lines',
                    'echo': 'Display text',
                    'find': 'Find files and directories',
                    
                    # System Information
                    'whoami': 'Display current user',
                    'date': 'Display current date and time',
                    'ps': 'Display running processes',
                    'df': 'Show filesystem usage',
                    'free': 'Show memory usage',
                    'uptime': 'Show system uptime',
                    'uname': 'Display system information',
                    'top': 'Show system resource usage',
                    
                    # Interface & Utilities
                    'help': 'Show available commands',
                    'clear': 'Clear terminal screen',
                    'history': 'Show command history',
                    
                    # Linux+ Boot & System Management
                    'grub2-install': 'Install GRUB2 bootloader',
                    'grub2-mkconfig': 'Generate GRUB configuration',
                    'update-grub': 'Update GRUB configuration (Debian)',
                    'mkinitrd': 'Create initial ramdisk image',
                    'dracut': 'Create initramfs image',
                    
                    # Linux+ Service & Process Management  
                    'systemctl': 'Control systemd services',
                    'journalctl': 'View systemd journal logs',
                    
                    # Linux+ Network & Security
                    'nmap': 'Network mapper and port scanner',
                    'firewall-cmd': 'Firewall configuration utility',
                    'iptables': 'Advanced firewall rules',
                    
                    # Linux+ Hardware & Modules
                    'lsmod': 'List loaded kernel modules',
                    'modprobe': 'Load/unload kernel modules',
                    'lsblk': 'List block devices',
                    'fdisk': 'Disk partitioning utility',
                    
                    # Linux+ Filesystem Operations
                    'mount': 'Mount filesystem',
                    'umount': 'Unmount filesystem'
                }
                
                result: List[Dict[str, str]] = []
                for cmd in commands:
                    result.append({
                        'command': cmd,
                        'description': command_descriptions.get(cmd, 'No description available')
                    })
                
                return jsonify({
                    'success': True,
                    'commands': result
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error loading commands: {str(e)}'
                })
        
        # Store reference to prevent "not accessed" warning
        self.get_available_commands_handler = get_available_commands

        @app.route('/api/cli/history', methods=['GET'])
        def get_cli_history():
            """Get CLI command history"""
            try:
                return jsonify({
                    'success': True,
                    'history': self.cli_history
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error loading history: {str(e)}'
                })
        
        # Store reference to prevent "not accessed" warning
        self.get_cli_history_handler = get_cli_history

        @app.route('/api/admin/switch_user', methods=['POST'])
        def switch_user():
            """Admin endpoint to switch current session user for testing demo data"""
            try:
                from flask import session
                data = request.get_json()
                user_id = data.get('user_id')
                
                if not user_id:
                    return jsonify({
                        'success': False,
                        'error': 'user_id is required'
                    })
                
                # Check if user exists in analytics data
                from services.simple_analytics import get_analytics_manager
                analytics = get_analytics_manager()
                user_data = analytics.get_user_data(user_id)
                
                if not user_data:
                    return jsonify({
                        'success': False,
                        'error': f'User {user_id} not found in analytics data'
                    })
                
                # Switch session to this user
                session['user_id'] = user_id
                
                return jsonify({
                    'success': True,
                    'message': f'Switched to user {user_id}',
                    'user_data': {
                        'user_id': user_id,
                        'total_questions': user_data.get('total_questions', 0),
                        'accuracy': user_data.get('accuracy', 0),
                        'total_sessions': user_data.get('total_sessions', 0),
                        'xp': user_data.get('xp', 0)
                    }
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error switching user: {str(e)}'
                })

        @app.route('/api/admin/list_users', methods=['GET'])
        def list_demo_users():
            """Admin endpoint to list available demo users"""
            try:
                from flask import session
                from services.simple_analytics import get_analytics_manager
                analytics = get_analytics_manager()
                
                # Get all users from analytics using the public method
                users = []
                analytics_data = analytics.get_all_profiles()  # Use the correct public method
                
                for user_id, user_data in analytics_data.items():
                    if user_data.get('total_questions', 0) > 0:  # Only users with data
                        users.append({
                            'user_id': user_id,
                            'total_questions': user_data.get('total_questions', 0),
                            'accuracy': user_data.get('accuracy', 0),
                            'total_sessions': user_data.get('total_sessions', 0),
                            'xp': user_data.get('xp', 0)
                        })
                
                # Sort by total questions descending
                try:
                    users.sort(key=lambda x: x['total_questions'], reverse=True)
                except (TypeError, ValueError, KeyError) as e:
                    print(f"Warning: Could not sort users by total_questions: {e}")
                    # Users will remain in original order
                
                return jsonify({
                    'success': True,
                    'users': users,
                    'current_user': session.get('user_id', 'anonymous')
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error listing users: {str(e)}'
                })

        # Store references to prevent "not accessed" warning
        self.switch_user_handler = switch_user
        self.list_demo_users_handler = list_demo_users
    
    def setup_vm_routes(self) -> None:
        """Setup routes for VM management functionality."""
        
        # Try to import VMManager to check if VM functionality is available
        try:
            from vm_integration.utils.vm_manager import VMManager
        except ImportError:
            self.logger.warning("VM management features not available - vm_integration module not found")
            VMManager = None
        
        @self.app.route('/api/vm/snapshots', methods=['GET'])
        def api_vm_snapshots():
            """API endpoint to list VM snapshots."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                vm_name = request.args.get('vm_name')
                
                if not vm_name:
                    return jsonify({'success': False, 'error': 'VM name is required'})
                
                vm_manager = VMManager()
                domain = vm_manager.find_vm(vm_name)
                
                # Get snapshots using the SnapshotManager
                from vm_integration.utils.snapshot_manager import SnapshotManager
                snapshot_manager = SnapshotManager()
                
                try:
                    # Use the correct method name
                    snapshots = snapshot_manager.list_snapshots(domain)
                    return jsonify({
                        'success': True,
                        'snapshots': snapshots
                    })
                except Exception as e:
                    self.logger.debug(f"Error listing snapshots: {e}")
                    return jsonify({
                        'success': True,
                        'snapshots': []  # Return empty list instead of error
                    })
                
            except Exception as e:
                self.logger.error(f"Error listing snapshots: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_vm_snapshots_handler = api_vm_snapshots

        @self.app.route('/api/vm/create_snapshot', methods=['POST'])
        def api_vm_create_snapshot():
            """API endpoint to create a VM snapshot."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                data = cast(VMRequestData, request.get_json() or {})
                vm_name: Optional[str] = data.get('vm_name')
                snapshot_name: Optional[str] = data.get('snapshot_name')
                description: str = data.get('description', '')
                
                if not vm_name or not snapshot_name:
                    return jsonify({'success': False, 'error': 'VM name and snapshot name are required'})
                
                vm_manager = VMManager()
                domain = vm_manager.find_vm(vm_name)
                
                from vm_integration.utils.snapshot_manager import SnapshotManager
                snapshot_manager = SnapshotManager()
                
                # Use the create_external_snapshot method
                success = snapshot_manager.create_external_snapshot(domain, snapshot_name, description)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Snapshot {snapshot_name} created for VM {vm_name}'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to create snapshot'
                    })
                
            except Exception as e:
                self.logger.error(f"Error creating snapshot: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_vm_create_snapshot_handler = api_vm_create_snapshot

        @self.app.route('/api/vm/restore_snapshot', methods=['POST'])
        def api_vm_restore_snapshot():
            """API endpoint to restore a VM from snapshot."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                data = cast(VMRequestData, request.get_json() or {})
                vm_name: Optional[str] = data.get('vm_name')
                snapshot_name: Optional[str] = data.get('snapshot_name')
                
                if not vm_name or not snapshot_name:
                    return jsonify({'success': False, 'error': 'VM name and snapshot name are required'})
                
                vm_manager = VMManager()
                domain = vm_manager.find_vm(vm_name)
                
                from vm_integration.utils.snapshot_manager import SnapshotManager
                snapshot_manager = SnapshotManager()
                
                # Use the revert_to_snapshot method
                success = snapshot_manager.revert_to_snapshot(domain, snapshot_name)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'VM {vm_name} restored from snapshot {snapshot_name}'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to restore snapshot'
                    })
                
            except Exception as e:
                self.logger.error(f"Error restoring snapshot: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_vm_restore_snapshot_handler = api_vm_restore_snapshot

        @self.app.route('/api/vm/delete_snapshot', methods=['POST'])
        def api_vm_delete_snapshot():
            """API endpoint to delete a VM snapshot."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                data = cast(VMRequestData, request.get_json() or {})
                vm_name: Optional[str] = data.get('vm_name')
                snapshot_name: Optional[str] = data.get('snapshot_name')
                
                if not vm_name or not snapshot_name:
                    return jsonify({'success': False, 'error': 'VM name and snapshot name are required'})
                
                vm_manager = VMManager()
                domain = vm_manager.find_vm(vm_name)
                
                from vm_integration.utils.snapshot_manager import SnapshotManager
                snapshot_manager = SnapshotManager()
                
                # Use the delete_external_snapshot method
                success = snapshot_manager.delete_external_snapshot(domain, snapshot_name)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Snapshot {snapshot_name} deleted from VM {vm_name}'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to delete snapshot'
                    })
                
            except Exception as e:
                self.logger.error(f"Error deleting snapshot: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_vm_delete_snapshot_handler = api_vm_delete_snapshot
    
    def setup_export_import_routes(self) -> None:
        """Setup routes for export and import functionality."""
        
        @self.app.route('/export/qa/md')
        def export_qa_markdown():
            """Export questions and answers to Markdown format with proper download headers."""
            try:
                if not self.game_state.questions:
                    return jsonify({
                        'success': False,
                        'message': 'No questions are currently loaded to export.'
                    }), 400
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"Linux_plus_QA_{timestamp}.md"
                
                # Create content in memory instead of temporary file
                content_lines: List[str] = []
                
                # Write Questions Section
                content_lines.append("# Questions\n")
                for i, q_data in enumerate(self.game_state.questions):
                    if len(q_data) < 5: 
                        continue
                    question_text, options, _, category, _ = q_data
                    content_lines.append(f"**Q{i+1}.** ({category})")
                    content_lines.append(f"{question_text}")
                    for j, option in enumerate(options):
                        content_lines.append(f"   {chr(ord('A') + j)}. {option}")
                    content_lines.append("")

                content_lines.append("---\n")

                # Write Answers Section
                content_lines.append("# Answers\n")
                for i, q_data in enumerate(self.game_state.questions):
                    if len(q_data) < 5: 
                        continue
                    _, options, correct_answer_index, _, explanation = q_data
                    if 0 <= correct_answer_index < len(options):
                        correct_option_letter = chr(ord('A') + correct_answer_index)
                        correct_option_text = options[correct_answer_index]
                        content_lines.append(f"**A{i+1}.** {correct_option_letter}. {correct_option_text}")
                        if explanation:
                            explanation_lines = explanation.split('\n')
                            content_lines.append("   *Explanation:*")
                            for line in explanation_lines:
                                content_lines.append(f"   {line.strip()}")
                        content_lines.append("")
                    else:
                        content_lines.append(f"**A{i+1}.** Error: Invalid correct answer index.")
                        content_lines.append("")
                
                # Join content with proper type annotation
                content = '\n'.join(content_lines)
                
                # Create response with proper headers
                from flask import Response
                response = Response(
                    content,
                    mimetype='text/markdown',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"',
                        'Content-Type': 'text/markdown; charset=utf-8',
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    }
                )
                
                return response
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error exporting Q&A to Markdown: {str(e)}'
                }), 500
        
        # Store reference to make it clear the route is being used
        self.export_qa_markdown_handler = export_qa_markdown

        @self.app.route('/export/qa/json')
        def export_qa_json():
            """Export questions and answers to JSON format with proper download headers."""
            try:
                if not self.game_state.questions:
                    return jsonify({
                        'success': False,
                        'message': 'No questions are currently loaded to export.'
                    }, 400)
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"Linux_plus_QA_{timestamp}.json"
                
                # Prepare questions data for JSON export
                questions_data: List[QuestionExportDict] = []
                for i, q_data in enumerate(self.game_state.questions):
                    if len(q_data) < 5: 
                        continue
                    question_text, options, correct_answer_index, category, explanation = q_data
                    
                    question_obj: QuestionExportDict = {
                        "id": i + 1,
                        "question": question_text,
                        "category": category,
                        "options": options,
                        "correct_answer_index": correct_answer_index,
                        "correct_answer_letter": chr(ord('A') + correct_answer_index) if 0 <= correct_answer_index < len(options) else "Invalid",
                        "correct_answer_text": options[correct_answer_index] if 0 <= correct_answer_index < len(options) else "Invalid index",
                        "explanation": explanation if explanation else ""
                    }
                    questions_data.append(question_obj)

                # Create the final JSON structure
                export_data: ExportDataDict = {
                    "metadata": {
                        "title": "Linux+ Study Questions",
                        "export_date": datetime.now().isoformat(),
                        "total_questions": len(questions_data),
                        "categories": sorted(list(set(q["category"] for q in questions_data)))
                    },
                    "questions": questions_data
                }
                
                # Convert to JSON string
                json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
                
                # Create response with proper headers
                from flask import Response
                response = Response(
                    json_content,
                    mimetype='application/json',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"',
                        'Content-Type': 'application/json; charset=utf-8',
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    }
                )
                
                return response
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error exporting Q&A to JSON: {str(e)}'
                }), 500
        
        # Store reference to make it clear the route is being used
        self.export_qa_json_handler = export_qa_json

        @self.app.route('/import/questions', methods=['GET', 'POST'])
        def import_questions_route():
            """Enhanced import with duplicate detection and comprehensive reporting."""
            if request.method == 'GET':
                return render_template('import.html')
            
            try:
                # File validation (existing code...)
                if 'file' not in request.files:
                    return jsonify({'success': False, 'message': 'No file was uploaded.'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'success': False, 'message': 'No file was selected.'}), 400
                
                # Handle potentially None filename
                filename = secure_filename(file.filename or "")
                file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
                
                if file_ext not in ['json', 'md']:
                    return jsonify({
                        'success': False,
                        'message': 'Only JSON and Markdown (.md) files are supported.'
                    }), 400
                
                # File size validation
                file.seek(0, 2)
                file_size = file.tell()
                file.seek(0)
                
                if file_size > 10 * 1024 * 1024:  # 10MB limit
                    return jsonify({
                        'success': False,
                        'message': 'File size too large. Maximum size is 10MB.'
                    }), 400
                
                # Read and parse content
                try:
                    file_content = file.read().decode('utf-8')
                except UnicodeDecodeError:
                    return jsonify({
                        'success': False,
                        'message': 'File encoding error. Please ensure the file is UTF-8 encoded.'
                    }), 400
                
                # Parse questions with proper type handling
                imported_questions: List[Dict[str, Any]] = []
                if file_ext == 'json':
                    imported_questions = self._parse_json_questions(file_content)
                elif file_ext == 'md':
                    imported_questions = self._parse_markdown_questions(file_content)
                
                if not imported_questions:
                    return jsonify({
                        'success': False,
                        'message': 'No valid questions found in the uploaded file.'
                    }), 400
                
                # Apply duplicate detection
                filtered_questions, duplicate_report = self._detect_and_eliminate_duplicates(imported_questions)
                
                # Add questions to system
                total_added = 0
                errors: List[str] = []
                
                for question_data in filtered_questions:
                    try:
                        # Validate question structure
                        if not question_data.get('question', '').strip():
                            errors.append(f"Question with empty text skipped")
                            continue
                        
                        if not question_data.get('options') or len(question_data['options']) < 2:
                            errors.append(f"Question with insufficient options skipped")
                            continue
                        
                        # Convert to tuple format
                        question_tuple = (
                            question_data.get('question', ''),
                            question_data.get('options', []),
                            question_data.get('correct_answer_index', 0),
                            question_data.get('category', 'General'),
                            question_data.get('explanation', '')
                        )
                        
                        if self._add_question_to_pool(question_tuple):
                            total_added += 1
                        else:
                            errors.append(f"Failed to add question to pool")
                            
                    except Exception as e:
                        errors.append(f"Error processing question: {str(e)}")
                        continue
                
                # Prepare comprehensive response
                response_message = f'Successfully imported {total_added} unique questions from {filename}.'
                
                if duplicate_report['duplicates_found'] > 0:
                    response_message += f'\n{duplicate_report["duplicates_found"]} duplicates were detected and skipped.'
                
                if errors:
                    response_message += f'\n{len(errors)} questions had processing errors.'
                
                return jsonify({
                    'success': True,
                    'message': response_message,
                    'total_imported': total_added,
                    'duplicate_report': duplicate_report,
                    'errors': errors[:10] if errors else []  # Limit error details
                })
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Import error: {error_details}")
                
                return jsonify({
                    'success': False,
                    'message': f'Error importing questions: {str(e)}'
                }), 500
                
        # Store reference to make it clear the route is being used
        self.import_questions_handler = import_questions_route
    def _parse_json_questions(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse questions from JSON content with comprehensive format support.
        
        Args:
            content: JSON content string
            
        Returns:
            List of normalized question dictionaries
            
        Raises:
            ValueError: If JSON format is invalid or unsupported
        """
        try:
            data = json.loads(content)
            questions: List[Dict[str, Any]] = []
            
            # Handle different JSON formats
            if isinstance(data, list):
                # Direct list of questions
                data_list = cast(List[Any], data)
                for item in data_list:
                    if isinstance(item, dict):
                        # Cast to expected dict type to help type checker
                        item_dict = cast(Dict[str, Any], item)
                        questions.append(self._normalize_question_dict(item_dict))
                    elif isinstance(item, (list, tuple)):
                        # Handle tuple format: (question, options, correct_index, category, explanation)
                        # Cast to sequence of Any to help type checker
                        item_seq = cast(Tuple[Any, ...], item)
                        if len(item_seq) >= 4:
                            questions.append({
                                'question': str(item_seq[0]),
                                'options': list(item_seq[1]) if len(item_seq) > 1 else [],
                                'correct_answer_index': int(item_seq[2]) if len(item_seq) > 2 else 0,
                                'category': str(item_seq[3]) if len(item_seq) > 3 else 'General',
                                'explanation': str(item_seq[4]) if len(item_seq) > 4 else ''
                            })
                            
            elif isinstance(data, dict):
                if 'questions' in data:
                    # Structured format with metadata
                    questions_data = cast(List[Any], data['questions'])
                    for item in questions_data:
                        if isinstance(item, dict):
                            item_dict = cast(Dict[str, Any], item)
                            questions.append(self._normalize_question_dict(item_dict))
                        elif isinstance(item, (list, tuple)):
                            # Handle tuple format: (question, options, correct_index, category, explanation)
                            item_seq = cast(Tuple[Any, ...], item)
                            if len(item_seq) >= 4:
                                questions.append({
                                    'question': str(item_seq[0]),
                                    'options': list(item_seq[1]) if len(item_seq) > 1 else [],
                                    'correct_answer_index': int(item_seq[2]) if len(item_seq) > 2 else 0,
                                    'category': str(item_seq[3]) if len(item_seq) > 3 else 'General',
                                    'explanation': str(item_seq[4]) if len(item_seq) > 4 else ''
                                })
                else:
                    # Single question object
                    single_question = cast(Dict[str, Any], data)
                    questions.append(self._normalize_question_dict(single_question))
            
            return questions
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing JSON content: {e}")

    def _parse_markdown_questions(self, content: str) -> List[Dict[str, Any]]:
        """
        Enhanced markdown parser for Linux+ study format with comprehensive validation.
        
        Args:
            content: Markdown content string
            
        Returns:
            List of normalized question dictionaries
        """
        questions: List[Dict[str, Any]] = []
        lines = content.split('\n')
        
        # State tracking variables
        in_questions_section = False
        in_answers_section = False
        current_question: Optional[Dict[str, Any]] = None
        current_options: List[str] = []
        answers_dict: Dict[int, int] = {}
        explanations_dict: Dict[int, str] = {}
        
        # Enhanced parsing with robust error handling
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            try:
                # Section detection
                if line == "# Questions":
                    in_questions_section = True
                    in_answers_section = False
                    i += 1
                    continue
                elif line == "# Answers":
                    in_questions_section = False
                    in_answers_section = True
                    i += 1
                    continue
                elif line == "---":
                    in_questions_section = False
                    i += 1
                    continue
                
                # Question parsing
                elif in_questions_section and line.startswith("**Q"):
                    # Save previous question if exists
                    if current_question and current_options:
                        questions.append({
                            'question_number': current_question['number'],
                            'question': current_question['text'],
                            'options': current_options.copy(),
                            'category': current_question['category'],
                            'correct_answer_index': 0,  # Will be set from answers
                            'explanation': ''  # Will be set from answers
                        })
                    
                    # Parse new question header
                    # Format: **Q1.** (Category)
                    match = re.match(r'\*\*Q(\d+)\.\*\*\s*\(([^)]*)\)', line)
                    if match:
                        question_number = int(match.group(1))
                        category = match.group(2).strip()
                        
                        # Read question text (next line)
                        i += 1
                        if i < len(lines):
                            question_text = lines[i].strip()
                            current_question = {
                                'number': question_number,
                                'text': question_text,
                                'category': category
                            }
                            current_options = []
                
                # Option parsing
                elif in_questions_section and current_question and re.match(r'^\s*[A-Z]\.\s*', line):
                    option_text = re.sub(r'^\s*[A-Z]\.\s*', '', line).strip()
                    if option_text:
                        current_options.append(option_text)
                
                # Answer parsing
                elif in_answers_section and line.startswith("**A"):
                    # Format: **A1.** C. Option text
                    match = re.match(r'\*\*A(\d+)\.\*\*\s*([A-Z])\.\s*(.*)', line)
                    if match:
                        answer_number = int(match.group(1))
                        correct_letter = match.group(2)
                        
                        # Convert letter to index (A=0, B=1, etc.)
                        correct_index = ord(correct_letter) - ord('A')
                        answers_dict[answer_number] = correct_index;
                        
                        # Look for explanation in next lines
                        explanation_lines: List[str] = []
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            if next_line.startswith('*Explanation:*'):
                                j += 1
                                while j < len(lines) and not lines[j].strip().startswith('**A'):
                                    explanation_lines.append(lines[j].strip())
                                    j += 1
                                break
                            elif next_line.startswith('**A'):
                                break
                            j += 1
                        
                        if explanation_lines:
                            explanations_dict[answer_number] = '\n'.join(explanation_lines).strip()
                
                i += 1
                
            except Exception as e:
                print(f"Warning: Error parsing line {i}: {line[:50]}... - {str(e)}")
                i += 1
                continue
        
        # Save last question if exists
        if current_question and current_options:
            questions.append({
                'question_number': current_question['number'],
                'question': current_question['text'],
                'options': current_options.copy(),
                'category': current_question['category'],
                'correct_answer_index': 0,
                'explanation': ''
            })
        
        # Apply answers and explanations
        for question in questions:
            q_num = question['question_number']
            if q_num in answers_dict:
                question['correct_answer_index'] = answers_dict[q_num]
            if q_num in explanations_dict:
                question['explanation'] = explanations_dict[q_num]
        
        return questions

    def _detect_and_eliminate_duplicates(self, imported_questions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Detect and eliminate duplicate questions based on question text similarity.
        
        Args:
            imported_questions: List of imported questions
            
        Returns:
            Tuple containing filtered questions and duplicate report
        """
        existing_questions: List[str] = [q[0] if isinstance(q, (list, tuple)) else q.get('text', '') 
                            for q in self.game_state.questions]
        
        unique_questions: List[Dict[str, Any]] = []
        duplicates_found = 0
        total_processed = len(imported_questions)
        
        for question in imported_questions:
            question_text = question.get('question', '').strip().lower()
            
            # Check against existing questions
            is_duplicate = False
            for existing_text in existing_questions:
                if self._is_similar_question(question_text, existing_text.lower()):
                    is_duplicate = True
                    break
            
            # Check against already processed questions in this import
            if not is_duplicate:
                for processed_question in unique_questions:
                    processed_text = processed_question.get('question', '').strip().lower()
                    if self._is_similar_question(question_text, processed_text):
                        is_duplicate = True
                        break
            
            if is_duplicate:
                duplicates_found += 1
            else:
                unique_questions.append(question)
        
        duplicate_report = {
            'total_processed': total_processed,
            'duplicates_found': duplicates_found,
            'unique_added': len(unique_questions)
        }
        
        return unique_questions, duplicate_report

    def _create_question_signature(self, question_text: str, options: List[str], category: str) -> str:
        """
        Generate normalized signature for duplicate detection.
        
        Uses multiple factors to create robust duplicate identification:
        - Normalized question text (case-insensitive, whitespace-normalized)
        - Option count and content
        - Category matching
        """
        import hashlib
        import re
        
        # Normalize question text
        normalized_question = re.sub(r'\s+', ' ', question_text.lower().strip())
        normalized_question = re.sub(r'[^\w\s]', '', normalized_question)  # Remove punctuation
        
        # Normalize options
        normalized_options: List[str] = []
        for option in options:
            normalized_option = re.sub(r'\s+', ' ', option.lower().strip())
            normalized_option = re.sub(r'[^\w\s]', '', normalized_option)
            normalized_options.append(normalized_option)
        
        # Create signature components
        signature_components = [
            normalized_question,
            str(len(options)),
            '|'.join(sorted(normalized_options)),
            category.lower().strip()
        ]
        
        # Generate hash signature
        signature_string = '###'.join(signature_components)
        return hashlib.md5(signature_string.encode('utf-8')).hexdigest()

    def _normalize_question_dict(self, question_dict: Dict[str, Any]) -> Dict[str, Union[str, List[str], int]]:
        """
        Normalize a question dictionary to standard format.
        
        Args:
            question_dict (dict): Raw question dictionary
            
        Returns:
            dict: Normalized question dictionary
        """
        # Handle different key variations
        question_text = (
            question_dict.get('question') or 
            question_dict.get('text') or 
            question_dict.get('question_text', '')
        ).strip()
        
        options = question_dict.get('options', [])
        if not isinstance(options, list):
            options = []
        
        # Handle different correct answer formats
        correct_index = 0
        if 'correct_answer_index' in question_dict:
            correct_index = int(question_dict['correct_answer_index'])
        elif 'correct_answer' in question_dict:
            # Try to convert correct_answer to index
            correct_answer = question_dict['correct_answer']
            if isinstance(correct_answer, str) and len(correct_answer) == 1:
                # Convert letter to index (A=0, B=1, etc.)
                correct_index = ord(correct_answer.upper()) - ord('A')
            elif isinstance(correct_answer, (int, str)):
                correct_index = int(correct_answer)
        
        category = question_dict.get('category', 'General').strip()
        explanation = question_dict.get('explanation', '').strip()
        
        return {
            'question': question_text,
            'options': options,
            'correct_answer_index': correct_index,
            'category': category,
            'explanation': explanation
        }

    def _is_similar_question(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """
        Check if two question texts are similar enough to be considered duplicates.
        
        Args:
            text1: First question text
            text2: Second question text
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if questions are similar enough to be duplicates
        """
        if not text1 or not text2:
            return False
            
        # Simple similarity check - can be enhanced with more sophisticated algorithms
        # Remove common words and punctuation for comparison
        import re
        
        def clean_text(text: str) -> str:
            # Remove punctuation and extra spaces
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            # Remove common words
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'what', 'which', 'how', 'when', 'where', 'why'}
            words = [word for word in text.split() if word not in common_words and len(word) > 2]
            return ' '.join(words)
        
        clean1 = clean_text(text1)
        clean2 = clean_text(text2)
        
        if not clean1 or not clean2:
            return text1.strip() == text2.strip()
        
        # Calculate Jaccard similarity
        words1 = set(clean1.split())
        words2 = set(clean2.split())
        
        if not words1 and not words2:
            return True
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return False
            
        similarity = intersection / union
        return similarity >= threshold

    def _add_question_to_pool(self, question_tuple: Tuple[str, List[str], int, str, str]) -> bool:
        """
        Add a question tuple to the game state question pool.
        
        Args:
            question_tuple (tuple): Question in tuple format
                                   (text, options, correct_index, category, explanation)
            
        Returns:
            bool: True if question was added successfully
        """
        try:
            # Validate tuple format (length check only since type is guaranteed)
            if len(question_tuple) < 4:
                return False
            
            text, options, correct_index, category = question_tuple[:4]
            explanation = question_tuple[4] if len(question_tuple) > 4 else ""
            
            # Validate question data
            if not text or not text.strip():
                return False
            
            if not options or len(options) < 2:
                return False
            
            if not (0 <= correct_index < len(options)):
                return False
            
            if not category or not category.strip():
                category = "General"
            
            # Add to game state
            validated_tuple = (text.strip(), list(options), int(correct_index), 
                             category.strip(), explanation.strip())
            
            # Add to questions list
            self.game_state.questions.append(validated_tuple)
            
            # Update categories
            self.game_state.categories.add(category.strip())
            
            # Update question manager if it exists
            if hasattr(self.game_state, 'question_manager'):
                from models.question import Question
                question_obj = Question(text.strip(), list(options), int(correct_index), 
                                      category.strip(), explanation.strip())
                self.game_state.question_manager.questions.append(question_obj)
                self.game_state.question_manager.categories.add(category.strip())
            
            return True
            
        except Exception as e:
            print(f"Error adding question to pool: {str(e)}")
            return False
    def _simulate_command(self, command: str) -> Optional[str]:
        """Simulate common commands with educational examples"""
        
        # Create sample files content
        sample_files = {
            'sample.txt': 'Hello Linux Plus student!\nThis is a sample text file.\nPractice your command line skills here.\nGood luck with your certification!',
            'log.txt': 'INFO: System started\nERROR: Failed to connect\nINFO: Retrying connection\nWARNING: Low disk space\nINFO: Connection established',
            'log.txt': 'INFO: System started\nERROR: Failed to connect\nINFO: Retrying connection\nWARNING: Low disk space\nINFO: Connection established',
            'data.csv': 'name,age,city\nJohn,25,New York\nJane,30,Los Angeles\nBob,35,Chicago',
            'config.conf': '[database]\nhost=localhost\nport=5432\nname=mydb\n\n[logging]\nlevel=INFO\nfile=/var/log/app.log'
        }
        
        cmd_parts = command.split()
        if not cmd_parts:
            return None
        
        base_cmd = cmd_parts[0]
        
        # Simulate ls command
        if base_cmd == 'ls':
            if len(cmd_parts) == 1:
                return 'sample.txt  log.txt  data.csv  config.conf  docs/  scripts/'
            else:
                return 'sample.txt  log.txt  data.csv  config.conf'
        
        # Simulate cat command
        elif base_cmd == 'cat' and len(cmd_parts) > 1:
            filename = cmd_parts[1]
            if filename in sample_files:
                return sample_files[filename]
            else:
                return f'cat: {filename}: No such file or directory'
        
        # Simulate grep command
        elif base_cmd == 'grep' and len(cmd_parts) >= 3:
            pattern = cmd_parts[1].strip('"\'')
            filename = cmd_parts[2]
            if filename in sample_files:
                lines = sample_files[filename].split('\n')
                matches = [line for line in lines if pattern.lower() in line.lower()]
                return '\n'.join(matches) if matches else f'grep: no matches found for "{pattern}"'
            else:
                return f'grep: {filename}: No such file or directory'
        
        # Simulate wc command
        elif base_cmd == 'wc' and len(cmd_parts) > 1:
            filename = cmd_parts[1]
            if filename in sample_files:
                content = sample_files[filename]
                lines = len(content.split('\n'))
                words = len(content.split())
                chars = len(content)
                return f'{lines:8} {words:8} {chars:8} {filename}'
            else:
                return f'wc: {filename}: No such file or directory'
        
        return None  # Command not simulated, try real execution

    def _get_help_text(self) -> str:
        """Get comprehensive help text"""
        return """Linux Plus CLI Playground - Available Commands:

    FILE OPERATIONS:
    ls                    - List files and directories
    cat <file>           - Display file contents
    head <file>          - Show first 10 lines of file
    tail <file>          - Show last 10 lines of file

    TEXT PROCESSING:
    grep <pattern> <file> - Search for pattern in file
    wc <file>            - Count lines, words, and characters

    SYSTEM INFO:
    pwd                  - Show current directory path
    whoami              - Display current username
    date                - Show current date and time

    UTILITIES:
    echo "text"         - Display text
    find . -name "*.txt" - Find files by pattern
    clear               - Clear terminal screen
    help                - Show this help message

    SAMPLE FILES AVAILABLE:
    sample.txt          - Basic text file
    log.txt             - Log file with different message types
    data.csv            - CSV data file
    config.conf         - Configuration file

    EXAMPLES:
    cat sample.txt              - View sample file
    grep "ERROR" log.txt        - Find error messages
    wc data.csv                 - Count lines in CSV
    echo "Hello World"          - Print text
    find . -name "*.txt"        - Find all .txt files

    This is a safe educational environment. Not all Linux commands are available.
    Type commands above to practice Linux command line skills!"""
    def reset_quiz_state(self) -> None:
        """Reset quiz state variables."""
        self.quiz_active = False
        self.current_quiz_mode = None
        self.current_category_filter = None
        self.current_question_data = None
        self.current_question_index = -1
        self.current_streak = 0
        self.quick_fire_start_time = None
        self.quick_fire_questions_answered = 0
    def setup_routes(self) -> None:
        """Setup Flask routes for the web interface."""
        
        @self.app.route('/')
        def index():
            # Get analytics data for server-side rendering
            try:
                from services.simple_analytics import get_analytics_manager
                from flask import session
                
                user_id = session.get('user_id', 'anonymous')
                analytics = get_analytics_manager()
                dashboard_stats = analytics.get_dashboard_stats(user_id)
                
                # If no data, try demo user
                if dashboard_stats.get('questions_answered', 0) == 0:
                    demo_stats = analytics.get_dashboard_stats('demo_user_001')
                    if demo_stats.get('questions_answered', 0) > 0:
                        dashboard_stats = demo_stats
                
                return render_template('index.html', stats=dashboard_stats)
            except Exception as e:
                print(f"Error loading dashboard stats: {e}")
                return render_template('index.html', stats={
                    'level': 1, 'xp': 0, 'streak': 0, 'total_correct': 0, 'accuracy': 0
                })
        # Store reference to make it clear the route is being used
        self.index_handler = index
        
        @self.app.route('/quiz')
        def quiz_page():
            from utils.game_values import get_game_value_manager
            game_values = get_game_value_manager().get_all_config()
            return render_template('quiz.html', game_values=game_values)
        # Store reference to make it clear the route is being used
        self.quiz_page_handler = quiz_page

        @self.app.route('/practice')
        def practice_page():
            return render_template('practice.html')
        # Store reference to make it clear the route is being used
        self.practice_page_handler = practice_page

        @self.app.route('/about')
        def about_page():
            return render_template('about.html')
        # Store reference to make it clear the route is being used
        self.about_page_handler = about_page

        @self.app.route('/stats')
        def stats_page():
            return render_template('stats.html')
        # Store reference to make it clear the route is being used
        self.stats_page_handler = stats_page
        
        @self.app.route('/achievements')
        def achievements_page():
            return render_template('achievements.html')
        # Store reference to make it clear the route is being used
        self.achievements_page_handler = achievements_page
        
        @self.app.route('/review')
        def review_page():
            return render_template('review.html')
        # Store reference to make it clear the route is being used
        self.review_page_handler = review_page
        
        @self.app.route('/settings')
        def settings_page():
            return render_template('settings.html')
        # Store reference to make it clear the route is being used
        self.settings_page_handler = settings_page
        
        @self.app.route('/analytics')
        def analytics_page():
            try:
                from services.simple_analytics import get_analytics_manager
                from flask import session
                
                user_id = session.get('user_id', 'anonymous')
                analytics = get_analytics_manager()
                user_data = analytics.get_user_data(user_id)
                
                # Calculate recent achievements properly
                recent_achievements = []
                all_achievements = user_data.get('achievements', [])
                
                # Sort achievements by date and get last 3
                if all_achievements:
                    try:
                        # Ensure all achievements have a comparable earned_date
                        sorted_achievements = sorted(all_achievements, 
                                                   key=lambda x: x.get('earned_date', ''), 
                                                   reverse=True)
                        recent_achievements = sorted_achievements[:3]
                    except (TypeError, ValueError) as e:
                        print(f"Warning: Could not sort achievements: {e}")
                        # Fallback: just take the first 3 achievements
                        recent_achievements = all_achievements[:3]
                
                # Calculate study activity properly
                from datetime import datetime, timedelta
                today = datetime.now()
                
                # Generate last 7 days activity
                activity_data = []
                for i in range(7):
                    date = today - timedelta(days=i)
                    date_str = date.strftime('%Y-%m-%d')
                    
                    # Check if user was active on this date
                    active = False
                    questions_count = 0
                    
                    if user_data.get('last_activity'):
                        try:
                            last_activity = datetime.fromisoformat(user_data['last_activity'].replace('Z', '+00:00'))
                            if last_activity.date() == date.date():
                                active = True
                                # For today's activity, use a portion of total questions as estimate
                                if i == 0:  # Today
                                    questions_count = min(user_data.get('total_questions', 0), 10)
                        except Exception:
                            pass
                    
                    activity_data.insert(0, {
                        'date': date_str,
                        'active': active,
                        'questions': questions_count
                    })
                
                # Calculate performance overview changes
                total_questions = user_data.get('total_questions', 0)
                correct_answers = user_data.get('correct_answers', 0)
                accuracy = user_data.get('accuracy', 0.0)
                study_streak = user_data.get('study_streak', 0)
                
                # Estimate session count more accurately
                estimated_sessions = max(1, total_questions // 5) if total_questions > 0 else 0
                
                # Generate recent performance data
                recent_performance = []
                if total_questions > 0:
                    # Create sample recent sessions based on user's actual performance
                    sessions_to_show = min(5, estimated_sessions)
                    questions_per_session = max(1, total_questions // max(1, sessions_to_show))
                    
                    for i in range(sessions_to_show):
                        session_date = today - timedelta(days=i)
                        session_questions = min(questions_per_session, total_questions - (i * questions_per_session))
                        session_correct = round((session_questions * accuracy) / 100) if accuracy else 0
                        session_accuracy = (session_correct / session_questions) * 100 if session_questions > 0 else 0
                        
                        recent_performance.append({
                            'date': session_date.isoformat(),
                            'accuracy': session_accuracy,
                            'questions': session_questions,
                            'activity': 'quiz'
                        })
                
                # Build topic breakdown with numeric accuracies (template expects numbers, not dicts)
                from typing import Dict as _Dict, List as _List, Tuple as _Tuple
                topics_studied: _Dict[str, Any] = user_data.get('topics_studied', {}) or {}
                topic_breakdown: _Dict[str, float] = {}
                questions_per_topic: _Dict[str, int] = {}
                for topic, data in topics_studied.items():
                    if isinstance(topic, str):
                        if isinstance(data, dict):
                            total_t = int(data.get('total', data.get('questions', 0)) or 0)
                            correct_t = int(data.get('correct', 0) or 0)
                            acc_val: float = round((correct_t / total_t) * 100, 1) if total_t > 0 else 0.0
                            topic_breakdown[topic] = acc_val
                            questions_per_topic[topic] = int(data.get('questions', data.get('total', 0)) or 0)
                        else:
                            try:
                                topic_breakdown[topic] = float(data)  # type: ignore[arg-type]
                            except Exception:
                                topic_breakdown[topic] = 0.0
                            questions_per_topic[topic] = 0
                topic_breakdown_list: _List[_Tuple[str, float]] = sorted(topic_breakdown.items(), key=lambda x: x[1], reverse=True)
                
                # Prepare comprehensive stats for dashboard
                stats = {
                    'total_questions': total_questions,
                    'overall_accuracy': round(accuracy, 1),
                    'accuracy': round(accuracy, 1),  # ensure alias
                    'total_vm_commands': 0,  # VM commands not tracked in simple analytics
                    'study_streak': study_streak,
                    'total_sessions': estimated_sessions,
                    'recent_achievements': recent_achievements,
                    'recent_performance': recent_performance,
                    'activity_data': activity_data,
                    'topic_breakdown': topic_breakdown,
                    'topic_breakdown_list': topic_breakdown_list,
                    'questions_per_topic': questions_per_topic,
                    'activity_breakdown': {'quiz': estimated_sessions, 'practice': 0},
                    'level': user_data.get('level', 1),
                    'xp': user_data.get('xp', 0),
                    'display_name': user_data.get('display_name', user_id.replace('_', ' ').title()),
                    'certification_progress': user_data.get('certification_progress', 0)
                }
                
                return render_template('analytics_dashboard.html', stats=stats)
            except Exception as e:
                print(f"Error in analytics page: {e}")
                # Return template with empty stats on error
                empty_stats = {
                    'total_questions': 0,
                    'overall_accuracy': 0.0,
                    'accuracy': 0.0,
                    'total_vm_commands': 0,
                    'study_streak': 0,
                    'total_sessions': 0,
                    'recent_achievements': [],
                    'recent_performance': [],
                    'activity_data': [],
                    'topic_breakdown': {},
                    'topic_breakdown_list': [],
                    'questions_per_topic': {},
                    'activity_breakdown': {},
                    'level': 1,
                    'xp': 0,
                    'display_name': 'User',
                    'certification_progress': 0
                }
                return render_template('analytics_dashboard.html', stats=empty_stats)
        # Store reference to make it clear the route is being used
        self.analytics_page_handler = analytics_page
        
        @self.app.route('/profile-test')
        def profile_test():
            # Serve the HTML test file
            try:
                with open('profile_test.html', 'r') as f:
                    content = f.read()
                from flask import Response
                return Response(content, mimetype='text/html')
            except FileNotFoundError:
                return "Profile test page not found", 404
        # Store reference to make it clear the route is being used
        self.profile_test_handler = profile_test
        
        @self.app.route('/debug-settings')
        def debug_settings():
            # Serve the debug HTML file
            try:
                with open('debug_settings.html', 'r') as f:
                    content = f.read()
                from flask import Response
                return Response(content, mimetype='text/html')
            except FileNotFoundError:
                return "Debug settings page not found", 404
        # Store reference to make it clear the route is being used
        self.debug_settings_handler = debug_settings
        
        @self.app.route('/dashboard-test')
        def dashboard_test():
            return render_template('dashboard_test.html')
        # Store reference to make it clear the route is being used
        self.dashboard_test_handler = dashboard_test

        @self.app.route('/api/status')
        def api_status():
            try:
                # Use quiz controller as single source of truth
                status = self.quiz_controller.get_session_status()
                
                # Get analytics data for consistent scoring
                from services.simple_analytics import get_analytics_manager
                analytics = get_analytics_manager()
                user_data = analytics.get_user_data('anonymous')
                
                # Determine total questions based on quiz state
                total_questions = len(self.game_state.questions)  # Default to all available questions
                
                # If quiz is active and has a custom limit, use that instead
                if status['quiz_active'] and hasattr(self.quiz_controller, 'custom_question_limit') and self.quiz_controller.custom_question_limit:
                    total_questions = self.quiz_controller.custom_question_limit
                
                return jsonify({
                    'quiz_active': status['quiz_active'],
                    'total_questions': total_questions,
                    'categories': sorted(list(self.game_state.categories)),
                    'session_score': status['session_score'],
                    'session_total': status['session_total'],
                    'current_streak': status['current_streak'],
                    'total_points': user_data['xp'],  # Use analytics XP for total accumulated points
                    'session_points': self.game_state.session_points,  # Use actual session points
                    'quiz_mode': status['mode']
                })
            except Exception as e:
                # Get analytics data for consistent scoring even in error case
                from services.simple_analytics import get_analytics_manager
                analytics = get_analytics_manager()
                user_data = analytics.get_user_data('anonymous')
                
                return jsonify({
                    'quiz_active': False,
                    'total_questions': len(self.game_state.questions),
                    'categories': sorted(list(self.game_state.categories)),
                    'session_score': 0,
                    'session_total': 0,
                    'current_streak': 0,
                    'total_points': user_data.get('xp', 0),  # Use analytics XP for total
                    'session_points': 0,  # No session active, so 0 session points
                    'quiz_mode': None,
                    'error': str(e)
                })
        # Store reference to make it clear the route is being used
        self.api_status_handler = api_status

        @self.app.route('/cli-playground')
        def cli_playground_page():
            """CLI Playground page"""
            return render_template('cli_playground.html', 
                                title='CLI Playground',
                                active_page='cli_playground')
        # Store reference to make it clear the route is being used
        self.cli_playground_page_handler = cli_playground_page
        
        @self.app.route('/vm-playground')
        def vm_playground():
            """VM Playground page"""
            return render_template('vm_playground.html', 
                                title='VM Playground',
                                active_page='vm_playground')
        # Store reference to make it clear the route is being used
        self.vm_playground_handler = vm_playground
        
        @self.app.route('/api/start_quiz', methods=['POST'])
        def api_start_quiz():
            try:
                data = cast(QuizStartRequestData, request.get_json() or {})
                quiz_mode: str = data.get('mode', 'standard')
                category: Optional[str] = data.get('category')
                num_questions: Optional[int] = data.get('num_questions')
                
                # Normalize category filter

                category_filter = None if category == "All Categories" else category
                
                # Ensure current settings are applied to quiz controller
                self._ensure_settings_applied()
                
                # Store number of questions if provided BEFORE starting the session
                if num_questions and quiz_mode not in ['survival', 'exam']:
                    # Validate that num_questions is a valid positive integer
                    try:
                        num_questions_int = int(num_questions)
                        if num_questions_int > 0:
                            self.quiz_controller.custom_question_limit = num_questions_int
                        else:
                            print(f"Warning: Invalid num_questions value: {num_questions}")
                            self.quiz_controller.custom_question_limit = None
                    except (ValueError, TypeError):
                        print(f"Warning: Could not convert num_questions to int: {num_questions}")
                        self.quiz_controller.custom_question_limit = None
                else:
                    # Clear custom limit for modes that don't use it
                    self.quiz_controller.custom_question_limit = None
                
                # Force end any existing session to ensure clean state
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(
                    mode=quiz_mode,
                    category_filter=category_filter
                )
                
                # Store category filter in web interface for consistency
                self.current_category_filter = category_filter
                
                if result.get('session_active'):
                    return jsonify({'success': True, **result})
                else:
                    return jsonify({'success': False, 'error': 'Failed to start quiz session'})
                    
            except Exception as e:
                print(f"Error starting quiz: {e}")
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_start_quiz_handler = api_start_quiz

        # Initialize database pooling for web mode
        db_manager = setup_database_for_web()
        # Store reference to make it clear the variable is being used
        self.db_manager = db_manager

        # Setup teardown handlers
        self.setup_app_teardown(self.app)

        # Add a health check route for monitoring
        @self.app.route('/health/db')
        def database_health() -> Union[Dict[str, Any], Tuple[Dict[str, str], int]]:
            """Database health check endpoint."""
            try:
                db_manager = get_database_manager()
                if db_manager:
                    pool_status = db_manager.get_pool_status()
                    return {
                        "status": "healthy",
                        "database_type": db_manager.db_type,
                        "pool_status": pool_status
                    }
                else:
                    return {"status": "no_pooling", "message": "Database pooling not initialized"}
            except Exception as e:
                return {"status": "error", "message": str(e)}, 500
        # Store reference to make it clear the route is being used
        self.database_health_handler = database_health

        @self.app.route('/api/get_question')
        def api_get_question():
            try:
                if not self.quiz_controller.quiz_active:
                    return jsonify({'quiz_complete': True, 'error': 'No active quiz session'})
                
                # Check for break reminder before getting question
                if self._should_show_break_reminder():
                    return jsonify({
                        'break_reminder': True,
                        'questions_since_break': self.quiz_controller.questions_since_break,
                        'break_interval': self._get_break_interval()
                    })
                
                # First, check if there's already a current question (e.g., when returning to quiz tab)
                current_question = self.quiz_controller.get_current_question()
                
                if current_question is not None:
                    # Return the existing current question
                    try:
                        question_data_tuple = current_question['question_data']
                        
                        # Validate current question data structure
                        if not isinstance(question_data_tuple, (tuple, list)) or len(question_data_tuple) < 5:
                            print(f"ERROR: Invalid current question_data structure: {type(question_data_tuple)}")
                            return jsonify({'error': 'Invalid current question data format', 'quiz_complete': True})
                        
                        q_text, options, _, category, _ = question_data_tuple
                        
                        # Validate current question components
                        if not q_text or not isinstance(q_text, str):
                            print(f"ERROR: Invalid current question text: {type(q_text)} = {q_text}")
                            return jsonify({'error': 'Invalid current question text', 'quiz_complete': True})
                        
                        if not isinstance(options, list) or len(options) < 2:
                            print(f"ERROR: Invalid current question options: {type(options)} = {options}")
                            return jsonify({'error': 'Invalid current question options', 'quiz_complete': True})
                        
                        return jsonify({
                            'question': q_text,
                            'options': options,
                            'category': category,
                            'question_number': current_question.get('question_number', 1),
                            'total_questions': current_question.get('total_questions'),
                            'streak': current_question.get('streak', 0),
                            'mode': self.quiz_controller.current_quiz_mode,
                            'is_single_question': self.quiz_controller.current_quiz_mode in ['daily_challenge', 'pop_quiz'],
                            'quiz_complete': False,
                            'quick_fire_remaining': current_question.get('quick_fire_remaining'),
                            'break_reminder': False,
                            'returning_to_question': True  # Flag to indicate this is not a new question
                        })
                        
                    except (TypeError, ValueError, IndexError) as e:
                        print(f"ERROR: Failed to process current question: {e}")
                        print(f"Current question data: {current_question}")
                        return jsonify({'error': f'Failed to process current question: {str(e)}', 'quiz_complete': True})
                
                # No current question, so get the next one
                result = self.quiz_controller.get_next_question(self.quiz_controller.category_filter)
                
                if result is None:
                    return jsonify({'quiz_complete': True})
                
                # Store current question info (this is cached automatically by get_next_question)
                self.current_question_data = result['question_data']
                self.current_question_index = result['original_index']
                
                # Format response for web interface
                try:
                    question_data_tuple = result['question_data']
                    
                    # Validate tuple structure before unpacking
                    if not isinstance(question_data_tuple, (tuple, list)) or len(question_data_tuple) < 5:
                        print(f"ERROR: Invalid question_data structure: {type(question_data_tuple)} with length {len(question_data_tuple) if hasattr(question_data_tuple, '__len__') else 'N/A'}")
                        print(f"Question data: {question_data_tuple}")
                        return jsonify({'error': 'Invalid question data format', 'quiz_complete': True})
                    
                    q_text, options, correct_index, category, explanation = question_data_tuple
                    
                    # Enhanced validation
                    if not q_text or not isinstance(q_text, str):
                        print(f"ERROR: Invalid question text: {type(q_text)} = {q_text}")
                        return jsonify({'error': 'Invalid question text', 'quiz_complete': True})
                    
                    if not isinstance(options, list) or len(options) < 2:
                        print(f"ERROR: Invalid question options: {type(options)} = {options}")
                        print(f"Full question_data: {question_data_tuple}")
                        return jsonify({'error': 'Invalid question options format', 'quiz_complete': True})
                    
                    if not isinstance(correct_index, int) or correct_index < 0 or correct_index >= len(options):
                        print(f"ERROR: Invalid correct answer index: {correct_index} for {len(options)} options")
                        return jsonify({'error': 'Invalid answer index', 'quiz_complete': True})
                    
                except (TypeError, ValueError, IndexError) as e:
                    print(f"ERROR: Failed to unpack question data: {e}")
                    print(f"Question data type: {type(result.get('question_data', 'N/A'))}")
                    print(f"Question data: {result.get('question_data', 'N/A')}")
                    return jsonify({'error': f'Failed to parse question data: {str(e)}', 'quiz_complete': True})
                
                return jsonify({
                    'question': q_text,
                    'options': options,
                    'category': category,
                    'question_number': result.get('question_number', 1),
                    'total_questions': result.get('total_questions'),
                    'streak': result.get('streak', 0),
                    'mode': self.quiz_controller.current_quiz_mode,
                    'is_single_question': self.quiz_controller.current_quiz_mode in ['daily_challenge', 'pop_quiz'],
                    'quiz_complete': False,
                    'quick_fire_remaining': result.get('quick_fire_remaining'),
                    'break_reminder': False,
                    'returning_to_question': False  # Flag to indicate this is a new question
                })
                
            except Exception as e:
                print(f"Error in get_question: {e}")
                return jsonify({'error': str(e), 'quiz_complete': True})
        # Store reference to make it clear the route is being used
        self.api_get_question_handler = api_get_question

        @self.app.route('/api/acknowledge_break', methods=['POST'])
        def api_acknowledge_break():
            """Reset break counter when user acknowledges break reminder."""
            try:
                self.quiz_controller.reset_break_counter()
                return jsonify({'success': True})
            except Exception as e:
                print(f"Error acknowledging break: {e}")
                return jsonify({'success': False, 'error': str(e)})
                
        # Store reference to make it clear the route is being used
        self.api_acknowledge_break_handler = api_acknowledge_break
                

        @self.app.route('/api/submit_answer', methods=['POST'])
        def api_submit_answer():
            try:
                data = cast(AnswerSubmissionData, request.get_json() or {})
                user_answer_index: Optional[int] = data.get('answer_index')
                
                # Validate session and question state
                if not self.quiz_controller.quiz_active:
                    return jsonify({'error': 'No active quiz session'})
                
                # Get current question from controller
                current_question = self.quiz_controller.get_current_question()
                if current_question is None:
                    return jsonify({'error': 'No current question available'})
                
                question_data = current_question['question_data']
                question_index = current_question['original_index']
                
                result = self.quiz_controller.submit_answer(
                    question_data, 
                    user_answer_index, 
                    question_index
                )
                
                # Track analytics for this answer
                try:
                    user_id, analytics = ensure_analytics_user_sync()
                    if analytics and user_id:
                        # Use update_quiz_results for proper XP and achievement tracking
                        analytics.update_quiz_results(
                            user_id=user_id,
                            correct=result.get('is_correct', False),
                            topic=getattr(self.quiz_controller, 'category_filter', None) or question_data[3],  # Use question category
                            difficulty="intermediate"  # Default difficulty
                        )
                except Exception as e:
                    print(f"Error tracking analytics: {e}")
                
                # Clear current question cache after processing
                self.quiz_controller.clear_current_question_cache()
                
                return jsonify(result)
                
            except Exception as e:
                print(f"Error in submit_answer: {e}")
                return jsonify({'error': str(e)})
        
        # Store reference to the route function
        
        # Store reference to the route function
        self.api_submit_answer_handler = api_submit_answer
        
        @self.app.route('/api/end_quiz', methods=['POST'])
        def api_end_quiz():
            try:
                # If quiz is not active but we have saved results, return those
                if not self.quiz_controller.quiz_active:
                    if hasattr(self.quiz_controller, 'last_session_results') and self.quiz_controller.last_session_results:
                        return jsonify({'success': True, **self.quiz_controller.last_session_results})
                    else:
                        return jsonify({'success': True, 'message': 'No active quiz session'})
                
                # Quiz is still active, force end it
                result = self.quiz_controller.force_end_session()
                
                # Update analytics with actual session duration if available
                if 'session_duration' in result and 'session_total' in result:
                    try:
                        from services.simple_analytics import get_analytics_manager
                        from flask import session
                        
                        user_id = session.get('user_id', 'anonymous')
                        analytics = get_analytics_manager()
                        
                        print(f"🐛 DEBUG: About to call update_session_with_actual_time")
                        print(f"   user_id: {user_id}")
                        print(f"   actual_duration: {result['session_duration']}")
                        print(f"   questions_answered: {result['session_total']}")
                        
                        analytics.update_session_with_actual_time(
                            user_id=user_id,
                            actual_duration=result['session_duration'],
                            questions_answered=result['session_total']
                        )
                        print(f"✅ DEBUG: update_session_with_actual_time completed successfully")
                    except Exception as e:
                        print(f"❌ DEBUG: Error updating analytics with actual time: {e}")
                else:
                    print(f"🚨 DEBUG: Condition failed! result keys: {list(result.keys())}")
                    print(f"   session_duration in result: {'session_duration' in result}")
                    print(f"   session_total in result: {'session_total' in result}")
                    if 'session_duration' in result:
                        print(f"   session_duration value: {result['session_duration']}")
                    if 'session_total' in result:
                        print(f"   session_total value: {result['session_total']}")
                
                return jsonify({'success': True, **result})
                
            except Exception as e:
                print(f"Error in end_quiz: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to the route function
        self.api_end_quiz_handler = api_end_quiz
        
        @self.app.route('/api/quick_fire_status')
        def api_quick_fire_status():
            try:
                if self.quiz_controller.quick_fire_active:
                    result = self.quiz_controller.check_quick_fire_status()
                    return jsonify(result)
                else:
                    return jsonify({'active': False})
            except Exception as e:
                return jsonify({'active': False, 'error': str(e)})
        
        # Store reference to the route function
        self.api_quick_fire_status_handler = api_quick_fire_status
        
        @self.app.route('/api/start_quick_fire', methods=['POST'])
        def api_start_quick_fire():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="quick_fire")
                self.current_quiz_mode = "quick_fire"
                self.current_category_filter = None
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # Store reference to the route function
        self.api_start_quick_fire_handler = api_start_quick_fire

        @self.app.route('/api/start_daily_challenge', methods=['POST'])
        def api_start_daily_challenge():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="daily_challenge")
                self.current_quiz_mode = "daily_challenge"
                self.current_category_filter = None
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # Store reference to the route function
        self.api_start_daily_challenge_handler = api_start_daily_challenge

        @self.app.route('/api/start_pop_quiz', methods=['POST'])
        def api_start_pop_quiz():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="pop_quiz")
                self.current_quiz_mode = "pop_quiz"
                self.current_category_filter = None
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # Store reference to the route function
        self.api_start_pop_quiz_handler = api_start_pop_quiz

        @self.app.route('/api/start_mini_quiz', methods=['POST'])
        def api_start_mini_quiz():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="mini_quiz")
                self.current_quiz_mode = "mini_quiz"
                self.current_category_filter = None
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to the route function
        self.api_start_mini_quiz_handler = api_start_mini_quiz

        @self.app.route('/api/start_timed_challenge', methods=['POST'])
        def api_start_timed_challenge():
            try:
                data = cast(CategoryRequestData, request.get_json() or {})
                category: Optional[str] = data.get('category')
                category_filter: Optional[str] = None if category == "All Categories" else category
                
                # Handle custom question limit for timed mode
                if 'num_questions' in data:
                    try:
                        custom_question_limit = int(data['num_questions'])
                        if custom_question_limit > 0:
                            self.quiz_controller.custom_question_limit = custom_question_limit
                        else:
                            self.quiz_controller.custom_question_limit = None
                    except (ValueError, TypeError):
                        self.quiz_controller.custom_question_limit = None
                else:
                    self.quiz_controller.custom_question_limit = None

                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(
                    mode="timed", 
                    category_filter=category_filter
                )
                self.current_quiz_mode = "timed"
                self.current_category_filter = category_filter
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to the route function
        self.api_start_timed_challenge_handler = api_start_timed_challenge

        @self.app.route('/api/start_survival_mode', methods=['POST'])
        def api_start_survival_mode():
            try:
                data = cast(CategoryRequestData, request.get_json() or {})
                category: Optional[str] = data.get('category')
                category_filter: Optional[str] = None if category == "All Categories" else category

                # Handle custom question limit for survival mode (unlimited)
                # Survival mode typically doesn't use a limit, but we should clear any existing limit
                self.quiz_controller.custom_question_limit = None

                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="survival", category_filter=category_filter)
                self.current_quiz_mode = "survival"
                self.current_category_filter = category_filter
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to the route function
        self.api_start_survival_mode_handler = api_start_survival_mode

        @self.app.route('/api/start_exam_mode', methods=['POST'])
        def api_start_exam_mode():
            try:
                # Set exam mode to use 90 questions (standard Linux+ exam length)
                self.quiz_controller.custom_question_limit = 90
                
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="exam")
                self.current_quiz_mode = "exam"
                self.current_category_filter = None
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to the route function
        self.api_start_exam_mode_handler = api_start_exam_mode

        @self.app.route('/api/start_category_focus', methods=['POST'])
        def api_start_category_focus():
            try:
                data = cast(CategoryRequestData, request.get_json() or {})
                category: Optional[str] = data.get('category')
                
                if not category or category == "All Categories":
                    return jsonify({'success': False, 'error': 'Please select a specific category for Category Focus mode'})
                
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="category", category_filter=category)
                self.current_quiz_mode = "category"
                self.current_category_filter = category
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to make it clear the route is being used
        self.api_start_category_focus_handler = api_start_category_focus
        
        @self.app.route('/api/get_categories')
        def api_get_categories():
            """Get available question categories."""
            try:
                categories = sorted(list(self.game_state.question_manager.categories))
                return jsonify({
                    'success': True,
                    'categories': categories
                })
            except Exception as e:
                print(f"Error getting categories: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to make it clear the route is being used
        self.api_get_categories_handler = api_get_categories
        
        @self.app.route('/api/get_question_count')
        def api_get_question_count():
            """Get total count of available questions."""
            try:
                total_questions = self.game_state.get_question_count()
                return jsonify({
                    'success': True,
                    'total_questions': total_questions
                })
            except Exception as e:
                print(f"Error getting question count: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to make it clear the route is being used
        self.api_get_question_count_handler = api_get_question_count
        
        @self.app.route('/api/get_difficulties')
        def api_get_difficulties():
            """Get available difficulty levels."""
            try:
                # Since questions don't have difficulty levels in the current structure,
                # return standard difficulty levels for now
                difficulties = ['beginner', 'intermediate', 'advanced']
                return jsonify({
                    'success': True,
                    'difficulties': difficulties
                })
            except Exception as e:
                print(f"Error getting difficulties: {e}")
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_get_difficulties_handler = api_get_difficulties
        
        @self.app.route('/api/get_hint', methods=['POST'])
        def api_get_hint():
            """Get hint for current question by eliminating wrong answers."""
            try:
                # Check if quiz is active and has current question
                if not self.quiz_controller.quiz_active:
                    return jsonify({'success': False, 'error': 'No active quiz session'})
                
                # Get current question from controller
                current_question = self.quiz_controller.get_current_question()
                if current_question is None:
                    return jsonify({'success': False, 'error': 'No current question available'})
                
                question_data = current_question['question_data']
                _, options, correct_answer_index, _, _ = question_data
                
                # Find all incorrect answer indices
                incorrect_indices = [i for i in range(len(options)) if i != correct_answer_index]
                
                # Randomly select 2 incorrect answers to eliminate (or fewer if not enough options)
                import random
                eliminate_count = min(2, len(incorrect_indices))
                eliminate_indices = random.sample(incorrect_indices, eliminate_count)
                
                return jsonify({
                    'success': True,
                    'eliminate_indices': eliminate_indices,
                    'eliminated_count': eliminate_count
                })
                
            except Exception as e:
                print(f"Error getting hint: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to make it clear the route is being used
        self.api_get_hint_handler = api_get_hint
        
        @self.app.route('/api/dashboard')
        def api_dashboard():
            """API endpoint for dashboard data - single source of truth"""
            try:
                from services.simple_analytics import get_analytics_manager
                from services.time_tracking_service import get_time_tracker
                from flask import session
                
                analytics = get_analytics_manager()
                time_tracker = get_time_tracker()
                user_id = session.get('user_id', 'anonymous')
                
                # Get stats from simple analytics (single source of truth)
                stats = analytics.get_dashboard_stats(user_id)
                
                # Add time tracking data
                time_data = time_tracker.get_daily_summary()
                stats.update({
                    'quiz_time_today': time_data['quiz_time_today'],
                    'quiz_time_formatted': time_data['quiz_time_formatted'],
                })
                
                # Ensure we have all required fields for the frontend
                stats['success'] = True
                
                return jsonify(stats)
            except Exception as e:
                self.logger.error(f"Dashboard API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'questions_answered': 0,
                    'total_correct': 0,
                    'accuracy': 0,
                    'quiz_time_today': 0,
                    'quiz_time_formatted': '0s',
                    'streak': 0,
                    'level': 1,
                    'xp': 0
                })

        @self.app.route('/api/heatmap')
        def api_heatmap():
            """API endpoint for study activity heatmap data"""
            try:
                from services.simple_analytics import get_analytics_manager
                from flask import session
                
                analytics = get_analytics_manager()
                user_id = session.get('user_id', 'anonymous')
                
                # Get heatmap data from analytics
                heatmap_data = analytics.get_heatmap_data(user_id)
                
                return jsonify({
                    'success': True,
                    'heatmap_data': heatmap_data
                })
            except Exception as e:
                self.logger.error(f"Heatmap API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'heatmap_data': []
                })

        @self.app.route('/api/time-tracking')
        def api_time_tracking():
            """API endpoint for time tracking data"""
            try:
                from services.time_tracking_service import get_time_tracker
                
                time_tracker = get_time_tracker()
                stats = time_tracker.get_statistics()
                stats['success'] = True
                
                return jsonify(stats)
            except Exception as e:
                self.logger.error(f"Time tracking API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'quiz_time_today': 0,
                    'quiz_time_formatted': '0s',
                })

        @self.app.route('/api/analytics')
        def api_analytics():
            """API endpoint for analytics data - must match dashboard"""
            try:
                from services.simple_analytics import get_analytics_manager
                from flask import session
                
                analytics = get_analytics_manager()
                user_id = session.get('user_id', 'anonymous')
                
                # Get stats from same source as dashboard
                stats = analytics.get_analytics_stats(user_id)
                
                return jsonify({
                    'success': True,
                    'stats': stats
                })
            except Exception as e:
                self.logger.error(f"Analytics API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'stats': {}
                })

        @self.app.route('/api/statistics')
        def api_statistics():
            """API endpoint for statistics - uses same data as dashboard"""
            try:
                from services.simple_analytics import get_analytics_manager
                from flask import session
                
                analytics = get_analytics_manager()
                user_id = session.get('user_id', 'anonymous')
                
                # Use dashboard stats to ensure consistency
                stats = analytics.get_dashboard_stats(user_id)
                user_data = analytics.get_user_data(user_id)
                
                # Format topic data for statistics display
                def _format_category_stats(topics_studied):
                    categories = []
                    for topic, data in topics_studied.items():
                        if isinstance(data, dict):
                            categories.append({
                                'category': topic,
                                'correct': data.get('correct', 0),
                                'attempts': data.get('total', 0),
                                'accuracy': data.get('accuracy', 0)
                            })
                    return categories
                
                # Format for statistics page
                return jsonify({
                    'overall': {
                        'total_attempts': stats['total_questions'],
                        'total_correct': stats['total_correct'],
                        'overall_accuracy': stats['accuracy'],
                        'level': stats['level'],
                        'xp': stats['xp']
                    },
                    'categories': _format_category_stats(user_data.get('topics_studied', {})),
                    'questions': [],  # Would need question-level tracking
                    'success': True
                })
            except Exception as e:
                self.logger.error(f"Statistics API error: {e}")
                return jsonify({'error': str(e), 'success': False})

        @self.app.route('/api/achievements')
        def api_achievements():
            """API endpoint for achievements data"""
            try:
                # Load achievements data directly
                from models.achievements import AchievementSystem
                achievement_system = AchievementSystem()
                
                # Get current statistics
                from services.simple_analytics import get_analytics_manager
                from flask import session
                
                analytics = get_analytics_manager()
                user_id = session.get('user_id', 'anonymous')
                stats = analytics.get_dashboard_stats(user_id)
                user_data = analytics.get_user_data(user_id)
                
                # Get achievements data
                achievements_data = achievement_system.achievements
                badges = achievements_data.get("badges", [])
                total_points = achievements_data.get("points_earned", 0)
                questions_answered = achievements_data.get("questions_answered", 0)
                days_studied = len(achievements_data.get("days_studied", []))
                
                # Define all available achievements
                all_achievements = {
                    "First Steps": {
                        "name": "First Steps",
                        "description": "Complete your first quiz",
                        "category": "mastery",
                        "points": 10,
                        "unlocked": questions_answered > 0
                    },
                    "Speed Demon": {
                        "name": "Speed Demon", 
                        "description": "Answer 10 questions correctly in under 2 minutes",
                        "category": "speed",
                        "points": 25,
                        "unlocked": "speed_demon" in badges
                    },
                    "On Fire!": {
                        "name": "On Fire!",
                        "description": "Maintain a 7-day study streak",
                        "category": "streak", 
                        "points": 50,
                        "unlocked": days_studied >= 7
                    },
                    "Perfect Score": {
                        "name": "Perfect Score",
                        "description": "Get 100% accuracy on a 20-question quiz",
                        "category": "mastery",
                        "points": 100,
                        "unlocked": "perfect_session" in badges
                    },
                    "Night Owl": {
                        "name": "Night Owl",
                        "description": "Study between midnight and 3 AM",
                        "category": "special",
                        "points": 15,
                        "unlocked": "night_owl" in badges
                    },
                    "Linux Master": {
                        "name": "Linux Master",
                        "description": "Achieve 95% overall accuracy across 1000 questions",
                        "category": "legendary",
                        "points": 500,
                        "unlocked": questions_answered >= 1000 and stats.get('accuracy', 0) >= 95
                    },
                    "Category Expert": {
                        "name": "Category Expert",
                        "description": "Achieve 90% accuracy in any category",
                        "category": "mastery",
                        "points": 75,
                        "unlocked": stats.get('accuracy', 0) >= 90
                    },
                    "Streak Master": {
                        "name": "Streak Master",
                        "description": "Answer 5 questions correctly in a row",
                        "category": "streak",
                        "points": 25,
                        "unlocked": "streak_master" in badges
                    },
                    "Point Collector": {
                        "name": "Point Collector", 
                        "description": "Earn 500 points total",
                        "category": "mastery",
                        "points": 50,
                        "unlocked": "point_collector" in badges
                    },
                    "Dedicated Learner": {
                        "name": "Dedicated Learner",
                        "description": "Study for 3 different days", 
                        "category": "streak",
                        "points": 30,
                        "unlocked": "dedicated_learner" in badges
                    },
                    "Century Club": {
                        "name": "Century Club",
                        "description": "Answer 100 questions total",
                        "category": "mastery", 
                        "points": 100,
                        "unlocked": "century_club" in badges
                    },
                    "Quick Fire Champion": {
                        "name": "Quick Fire Champion",
                        "description": "Complete Quick Fire mode",
                        "category": "speed",
                        "points": 35,
                        "unlocked": "quick_fire_champion" in badges
                    },
                    "Daily Warrior": {
                        "name": "Daily Warrior",
                        "description": "Complete a daily challenge",
                        "category": "special",
                        "points": 25,
                        "unlocked": "daily_warrior" in badges
                    }
                }
                
                # Separate unlocked and locked achievements
                unlocked = []
                locked = []
                for achievement in all_achievements.values():
                    if achievement["unlocked"]:
                        unlocked.append(achievement)
                    else:
                        locked.append(achievement)
                
                # Calculate completion percentage
                completion_percentage = round((len(unlocked) / len(all_achievements)) * 100) if all_achievements else 0
                
                # Find rarest achievement (least unlocked)
                rarest_achievement = "Linux Master" if len(unlocked) > 0 else None
                
                return jsonify({
                    'total_points': total_points,
                    'questions_answered': questions_answered, 
                    'days_studied': days_studied,
                    'badges': badges,
                    'unlocked': unlocked,
                    'locked': locked,
                    'achievements': {
                        'unlocked': unlocked,
                        'locked': locked
                    },
                    'stats': {
                        'unlocked': len(unlocked),
                        'total': len(all_achievements),
                        'completion': completion_percentage,
                        'points': total_points,
                        'rarest': rarest_achievement,
                        'accuracy': stats.get('accuracy', 0),
                        'level': stats.get('level', 1)
                    },
                    'progress': {
                        'perfect_score': min(questions_answered, 20),
                        'linux_master': min(questions_answered, 1000),
                        'category_expert': stats.get('accuracy', 0)
                    },
                    'success': True
                })
            except Exception as e:
                self.logger.error(f"Achievements API error: {e}")
                return jsonify({
                    'total_points': 0,
                    'unlocked': [],
                    'locked': [],
                    'stats': {
                        'unlocked': 0,
                        'total': 45,
                        'completion': 0,
                        'points': 0,
                        'rarest': None
                    },
                    'error': str(e),
                    'success': False
                })

        # Profile Management API Routes
        @self.app.route('/api/profiles', methods=['GET'])
        def api_get_profiles():
            """Get all user profiles"""
            try:
                from services.simple_analytics import get_analytics_manager
                from flask import session
                
                analytics = get_analytics_manager()
                user_id = session.get('user_id', 'anonymous')
                
                # For now, just return the current user as a single profile
                # This can be expanded later for multi-profile support
                user_data = analytics.get_user_data(user_id)
                
                profiles = {
                    user_id: {
                        'name': user_data.get('display_name', 'Default Profile'),
                        'analytics': {
                            'sessions': user_data.get('sessions', []),
                            'total_questions': user_data.get('total_questions', 0),
                            'accuracy': user_data.get('accuracy', 0),
                        }
                    }
                }
                
                return jsonify({
                    'success': True,
                    'profiles': profiles,
                    'current_profile': user_id
                })
            except Exception as e:
                self.logger.error(f"Get profiles error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/profiles', methods=['POST'])
        def api_create_profile():
            """Create a new user profile"""
            try:
                data = request.get_json() or {}
                profile_name = data.get('name', '').strip()
                
                if not profile_name:
                    return jsonify({'success': False, 'error': 'Profile name is required'})
                
                # For now, just return success - multi-profile support can be added later
                return jsonify({
                    'success': True, 
                    'message': 'Profile creation will be available in a future update',
                    'profile_id': 'new_profile_id'
                })
            except Exception as e:
                self.logger.error(f"Create profile error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/profiles/switch', methods=['POST'])
        def api_switch_profile():
            """Switch to a different profile"""
            try:
                data = request.get_json() or {}
                profile_id = data.get('profile_id')
                
                if not profile_id:
                    return jsonify({'success': False, 'error': 'Profile ID is required'})
                
                # For now, just return success - actual switching can be implemented later
                from flask import session
                session['user_id'] = profile_id
                
                return jsonify({'success': True, 'message': 'Profile switched successfully'})
            except Exception as e:
                self.logger.error(f"Switch profile error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/profiles/<profile_id>/rename', methods=['PUT'])
        def api_rename_profile(profile_id):
            """Rename a user profile"""
            try:
                data = request.get_json() or {}
                new_name = data.get('name', '').strip()
                
                if not new_name:
                    return jsonify({'success': False, 'error': 'New name is required'})
                
                from services.simple_analytics import get_analytics_manager
                analytics = get_analytics_manager()
                user_data = analytics.get_user_data(profile_id)
                user_data['display_name'] = new_name
                analytics._update_user_data(profile_id, user_data)
                
                return jsonify({'success': True, 'message': 'Profile renamed successfully'})
            except Exception as e:
                self.logger.error(f"Rename profile error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/profiles/<profile_id>/reset', methods=['POST'])
        def api_reset_profile(profile_id):
            """Reset profile data"""
            try:
                from services.simple_analytics import get_analytics_manager
                analytics = get_analytics_manager()
                
                # Reset user data to defaults
                default_data = analytics._get_default_user_data()
                default_data['display_name'] = f'Profile {profile_id}'
                analytics._update_user_data(profile_id, default_data)
                
                return jsonify({'success': True, 'message': 'Profile data reset successfully'})
            except Exception as e:
                self.logger.error(f"Reset profile error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/clear_statistics', methods=['POST'])
        def api_clear_statistics():
            """Clear all statistics data across all profiles"""
            try:
                self.logger.info("Starting clear statistics operation")
                
                # Clear statistics using the stats controller
                if hasattr(self, 'stats_controller') and self.stats_controller:
                    success = self.stats_controller.clear_statistics()
                    if not success:
                        return jsonify({'success': False, 'error': 'Failed to clear statistics via controller'})
                else:
                    self.logger.warning("Stats controller not available, attempting direct clear")
                
                # Clear analytics database records
                try:
                    from utils.database import get_database_manager
                    from models.analytics import Analytics
                    
                    db_manager = get_database_manager()
                    if db_manager and db_manager.session_factory:
                        session = db_manager.session_factory()
                        try:
                            # Clear all analytics records
                            deleted_count = session.query(Analytics).delete()
                            session.commit()
                            self.logger.info(f"Cleared {deleted_count} analytics records")
                        except Exception as db_error:
                            session.rollback()
                            self.logger.error(f"Database clear error: {db_error}")
                            return jsonify({'success': False, 'error': f'Database clear failed: {str(db_error)}'})
                        finally:
                            session.close()
                    else:
                        self.logger.warning("Database manager not available for analytics clear")
                except Exception as analytics_error:
                    self.logger.error(f"Analytics clear error: {analytics_error}")
                    # Don't fail completely if analytics clear fails
                
                # Clear simple analytics data
                try:
                    from services.simple_analytics import get_analytics_manager
                    analytics = get_analytics_manager()
                    if analytics:
                        # Reset all user data to defaults
                        analytics.user_data = {}
                        analytics._save_data(analytics.user_data)
                        self.logger.info("Cleared simple analytics user data")
                except Exception as simple_analytics_error:
                    self.logger.error(f"Simple analytics clear error: {simple_analytics_error}")
                
                # Reset game state if available
                try:
                    if hasattr(self, 'game_state') and self.game_state:
                        self.game_state.reset_all_data()
                        self.logger.info("Reset game state data")
                except Exception as game_state_error:
                    self.logger.error(f"Game state reset error: {game_state_error}")
                
                # Reset quiz controller if available
                try:
                    if hasattr(self, 'quiz_controller') and self.quiz_controller:
                        self.quiz_controller.force_end_session()
                        self.logger.info("Reset quiz controller session")
                except Exception as quiz_controller_error:
                    self.logger.error(f"Quiz controller reset error: {quiz_controller_error}")
                
                # Clear time tracking data
                try:
                    from services.time_tracking_service import get_time_tracker
                    time_tracker = get_time_tracker()
                    time_tracker.reset_all_data()
                    self.logger.info("Reset time tracking data")
                except Exception as time_tracking_error:
                    self.logger.error(f"Time tracking reset error: {time_tracking_error}")
                
                # Clear JSON data files (achievements, history)
                try:
                    import os
                    import json
                    from utils.config import ACHIEVEMENTS_FILE, HISTORY_FILE
                    
                    # Reset achievements file
                    if os.path.exists(ACHIEVEMENTS_FILE):
                        with open(ACHIEVEMENTS_FILE, 'w') as f:
                            json.dump({}, f, indent=2)
                        self.logger.info("Reset achievements file")
                    
                    # Reset history file  
                    if os.path.exists(HISTORY_FILE):
                        with open(HISTORY_FILE, 'w') as f:
                            json.dump({}, f, indent=2)
                        self.logger.info("Reset history file")
                        
                except Exception as file_reset_error:
                    self.logger.error(f"File reset error: {file_reset_error}")
                
                self.logger.info("Clear statistics operation completed successfully")
                return jsonify({
                    'success': True, 
                    'message': 'All statistics and progress data have been cleared successfully'
                })
                
            except Exception as e:
                self.logger.error(f"Clear statistics error: {e}", exc_info=True)
                return jsonify({
                    'success': False, 
                    'error': f'Failed to clear statistics: {str(e)}'
                })

        @self.app.route('/api/profiles/<profile_id>', methods=['DELETE'])
        def api_delete_profile(profile_id):
            """Delete a user profile"""
            try:
                # For now, prevent deletion of the current user
                from flask import session
                current_user_id = session.get('user_id', 'anonymous')
                
                if profile_id == current_user_id:
                    return jsonify({'success': False, 'error': 'Cannot delete the active profile'})
                
                # Profile deletion can be implemented later
                return jsonify({
                    'success': True, 
                    'message': 'Profile deletion will be available in a future update'
                })
            except Exception as e:
                self.logger.error(f"Delete profile error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        # Review API Routes
        @self.app.route('/api/review_incorrect')
        def api_review_incorrect():
            """Get questions marked for review"""
            try:
                review_data = self.stats_controller.get_review_questions_data()
                
                # Convert to regular dict to allow additional fields
                result = dict(review_data)
                
                # Clean up missing questions automatically
                if review_data['missing_questions']:
                    questions_cleaned = self.stats_controller.cleanup_missing_review_questions(
                        review_data['missing_questions']
                    )
                    # Re-fetch data after cleanup
                    updated_review_data = self.stats_controller.get_review_questions_data()
                    result.update(updated_review_data)
                    result['cleanup_performed'] = True
                    result['questions_cleaned'] = questions_cleaned
                else:
                    result['cleanup_performed'] = False
                    result['questions_cleaned'] = 0
                
                return jsonify(result)
            except Exception as e:
                self.logger.error(f"Review incorrect API error: {e}")
                return jsonify({
                    'has_questions': False,
                    'questions': [],
                    'missing_questions': [],
                    'cleanup_performed': False,
                    'questions_cleaned': 0,
                    'error': str(e)
                })

        @self.app.route('/api/remove_from_review', methods=['POST'])
        def api_remove_from_review():
            """Remove a question from the review list"""
            try:
                data = cast(Dict[str, Any], request.get_json() or {})
                question_text = str(data.get('question_text', '')).strip()
                
                if not question_text:
                    return jsonify({'success': False, 'error': 'Question text is required'})
                
                success = self.stats_controller.remove_from_review_list(question_text)
                
                if success:
                    return jsonify({'success': True, 'message': 'Question removed from review list'})
                else:
                    return jsonify({'success': False, 'error': 'Question not found in review list'})
            except Exception as e:
                self.logger.error(f"Remove from review API error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/cleanup_review_list', methods=['POST'])
        def api_cleanup_review_list():
            """Clean up the review list by removing missing questions"""
            try:
                review_data = self.stats_controller.get_review_questions_data()
                
                if review_data['missing_questions']:
                    questions_cleaned = self.stats_controller.cleanup_missing_review_questions(
                        review_data['missing_questions']
                    )
                    return jsonify({
                        'success': True,
                        'questions_cleaned': questions_cleaned,
                        'message': f'Cleaned up {questions_cleaned} outdated question(s)'
                    })
                else:
                    return jsonify({
                        'success': True,
                        'questions_cleaned': 0,
                        'message': 'No cleanup needed - all questions are current'
                    })
            except Exception as e:
                self.logger.error(f"Cleanup review list API error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/load_game_values', methods=['GET'])
        def api_load_game_values():
            """Load game values configuration"""
            try:
                from utils.game_values import get_game_value_manager
                game_values = get_game_value_manager()
                config = game_values.get_all_config()
                return jsonify({'success': True, 'values': config})
            except Exception as e:
                self.logger.error(f"Load game values error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/save_game_values', methods=['POST'])
        def api_save_game_values():
            """Save game values configuration"""
            try:
                from utils.game_values import get_game_value_manager
                data = request.get_json() or {}
                game_values = get_game_value_manager()
                
                success = game_values.update_settings(**data)
                if success:
                    return jsonify({'success': True, 'message': 'Game values saved successfully'})
                else:
                    return jsonify({'success': False, 'error': 'Failed to save game values'})
            except Exception as e:
                self.logger.error(f"Save game values error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/reset_game_values', methods=['POST'])
        def api_reset_game_values():
            """Reset game values to defaults"""
            try:
                from utils.game_values import get_game_value_manager
                game_values = get_game_value_manager()
                success = game_values.reset_to_defaults()
                if success:
                    return jsonify({'success': True, 'message': 'Game values reset to defaults'})
                else:
                    return jsonify({'success': False, 'error': 'Failed to reset game values'})
            except Exception as e:
                self.logger.error(f"Reset game values error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/create_achievement', methods=['POST'])
        def api_create_achievement():
            """Create a custom achievement"""
            try:
                data = request.get_json() or {}
                name = data.get('name', '').strip()
                description = data.get('description', '').strip()
                condition_type = data.get('condition_type', '')
                condition_value = int(data.get('condition_value', 0))
                xp_reward = int(data.get('xp_reward', 0))
                
                if not all([name, description, condition_type]):
                    return jsonify({'success': False, 'error': 'All fields are required'})
                
                if condition_type not in ['questions', 'points', 'streaks', 'days']:
                    return jsonify({'success': False, 'error': 'Invalid condition type'})
                
                from models.achievements import AchievementSystem
                achievement_system = AchievementSystem()
                
                success = achievement_system.create_custom_achievement(
                    name, description, condition_type, condition_value, xp_reward
                )
                
                if success:
                    achievement_system.save_achievements()
                    return jsonify({'success': True, 'message': 'Achievement created successfully'})
                else:
                    return jsonify({'success': False, 'error': 'Achievement with this name already exists'})
                    
            except ValueError as e:
                return jsonify({'success': False, 'error': 'Invalid numeric values'})
            except Exception as e:
                self.logger.error(f"Create achievement error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/get_custom_achievements', methods=['GET'])
        def api_get_custom_achievements():
            """Get all custom achievements"""
            try:
                from models.achievements import AchievementSystem
                achievement_system = AchievementSystem()
                achievements = achievement_system.get_custom_achievements()
                return jsonify({'success': True, 'achievements': achievements})
            except Exception as e:
                self.logger.error(f"Get custom achievements error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/delete_achievement', methods=['POST'])
        def api_delete_achievement():
            """Delete a custom achievement"""
            try:
                data = request.get_json() or {}
                name = data.get('name', '').strip()
                
                if not name:
                    return jsonify({'success': False, 'error': 'Achievement name is required'})
                
                from models.achievements import AchievementSystem
                achievement_system = AchievementSystem()
                
                success = achievement_system.delete_custom_achievement(name)
                if success:
                    achievement_system.save_achievements()
                    return jsonify({'success': True, 'message': 'Achievement deleted successfully'})
                else:
                    return jsonify({'success': False, 'error': 'Achievement not found'})
                    
            except Exception as e:
                self.logger.error(f"Delete achievement error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/get_system_settings', methods=['GET'])
        def api_get_system_settings():
            """Get system settings including focus mode and break reminders"""
            try:
                from utils.game_values import get_game_value_manager
                game_values = get_game_value_manager()
                system_settings = game_values.get_value('system', None, {})
                
                # Add backward compatibility with web_settings.json
                try:
                    import json
                    from pathlib import Path
                    web_settings_file = Path("web_settings.json")
                    if web_settings_file.exists():
                        with open(web_settings_file, 'r') as f:
                            web_settings = json.load(f)
                            system_settings.update({
                                'focus_mode_enabled': web_settings.get('focusMode', False),
                                'break_reminder_interval': web_settings.get('breakReminder', 15)
                            })
                except Exception as e:
                    self.logger.warning(f"Could not load web_settings.json: {e}")
                
                return jsonify({'success': True, 'settings': system_settings})
            except Exception as e:
                self.logger.error(f"Get system settings error: {e}")
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/save_system_settings', methods=['POST'])
        def api_save_system_settings():
            """Save system settings including focus mode and break reminders"""
            try:
                from utils.game_values import get_game_value_manager
                data = request.get_json() or {}
                game_values = get_game_value_manager()
                
                success = game_values.update_settings(system=data)
                
                # Also update web_settings.json for backward compatibility
                try:
                    import json
                    from pathlib import Path
                    web_settings_file = Path("web_settings.json")
                    web_settings = {}
                    if web_settings_file.exists():
                        with open(web_settings_file, 'r') as f:
                            web_settings = json.load(f)
                    
                    web_settings.update({
                        'focusMode': data.get('focus_mode_enabled', False),
                        'breakReminder': data.get('break_reminder_interval', 15)
                    })
                    
                    with open(web_settings_file, 'w') as f:
                        json.dump(web_settings, f, indent=2)
                        
                except Exception as e:
                    self.logger.warning(f"Could not update web_settings.json: {e}")
                
                if success:
                    return jsonify({'success': True, 'message': 'System settings saved successfully'})
                else:
                    return jsonify({'success': False, 'error': 'Failed to save system settings'})
                    
            except Exception as e:
                self.logger.error(f"Save system settings error: {e}")
                return jsonify({'success': False, 'error': str(e)})