#!/usr/bin/env python3
"""
Web View for the Linux+ Study Game using Flask + pywebview.
Creates a desktop app with modern web interface.
"""

import webview
import threading
import time
from flask import Flask, render_template, request, jsonify, send_from_directory, session, send_file, flash, redirect, url_for
import os
from vm_integration.utils.snapshot_manager import SnapshotManager
from pathlib import Path
import json
from datetime import datetime
import hashlib
import time
import logging
import traceback
import atexit
from utils.cli_playground import get_cli_playground
import subprocess
import shlex
import re  # Add the missing import for regular expressions
try:
    from vm_integration.utils.vm_manager import VMManager
except ImportError:
    VMManager = None
from vm_integration.utils.ssh_manager import SSHManager
try:
    import libvirt  # type: ignore
except ImportError:
    libvirt = None
    logging.warning("libvirt-python not available. VM functionality will be limited.")

# Add proper type imports
from typing import Any, Dict, List, Optional, Union, Tuple, Set, TypeVar, Callable, Generator, cast, TypedDict, Literal, Protocol, runtime_checkable

try:
    from utils.database import initialize_database_pool, get_database_manager, cleanup_database_connections, DatabasePoolManager
except ImportError as e:
    logging.error(f"Database utilities import failed: {e}")
    # Import the real DatabasePoolManager for type hints
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from utils.database import DatabasePoolManager
        from controllers.stats_controller import DetailedStatistics, FormattedLeaderboardEntry, ReviewQuestionsData
    
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
import tempfile
import mimetypes
from typing import Any, Dict, Optional

# Define TypedDict for question object structure
class QuestionExportDict(TypedDict):
    """Type definition for question export data structure."""
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

cli_playground = get_cli_playground()

def setup_database_for_web() -> Optional["DatabasePoolManager"]:
    """Initialize database connection pooling for web mode."""
    try:
        # Determine database type from configuration or environment
        db_type = os.environ.get('DATABASE_TYPE', 'sqlite')
        enable_pooling = get_config_value('web', 'enable_db_pooling', True)
        
        # Initialize connection pool
        db_manager = initialize_database_pool(db_type, enable_pooling)
        
        # Log pool status
        if db_manager is not None:
            pool_status = db_manager.get_pool_status()
            if pool_status.get("pooling_enabled"):
                print(f"Database pooling enabled - Pool size: {pool_status.get('pool_size', 'N/A')}")
            else:
                print("Database pooling disabled (SQLite or manual override)")
        else:
            print("Database manager not initialized")
            
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
            from controllers.stats_controller import StatsController, ReviewQuestionsData  # Import the type
            
            self.quiz_controller = QuizController(game_state)
            
            # Load and apply settings to quiz controller
            settings = self._load_web_settings()
            if hasattr(self.quiz_controller, 'update_settings'):
                self.quiz_controller.update_settings(settings)
            
            self.stats_controller: StatsControllerProtocol = StatsController(game_state)
            # Runtime check is now valid since we added @runtime_checkable
            if not isinstance(self.stats_controller, StatsControllerProtocol):
                raise TypeError("StatsController does not implement StatsControllerProtocol")
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
        
        # Setup export/import routes
        self.setup_export_import_routes()
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
        """Load settings from web_settings.json file."""
        try:
            if os.path.exists('web_settings.json'):
                with open('web_settings.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading web settings: {e}")
        # Return default settings if file doesn't exist or can't be loaded
        return {'focusMode': False, 'breakReminder': 10}

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
                data = request.get_json()
                command = data.get('command', '').strip()
                
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
                        correct_option_text = match.group(3).strip()
                        
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
            return render_template('index.html')
        # Store reference to make it clear the route is being used
        self.index_handler = index
        
        @self.app.route('/quiz')
        def quiz_page():
            return render_template('quiz.html')
        # Store reference to make it clear the route is being used
        self.quiz_page_handler = quiz_page
        
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
        
        @self.app.route('/api/status')
        @self.app.route('/api/status')
        def api_status():
            try:
                # Use quiz controller as single source of truth
                status = self.quiz_controller.get_session_status()
                return jsonify({
                    'quiz_active': status['quiz_active'],
                    'total_questions': len(self.game_state.questions),
                    'categories': sorted(list(self.game_state.categories)),
                    'session_score': status['session_score'],
                    'session_total': status['session_total'],
                    'current_streak': status['current_streak'],
                    'total_points': self.game_state.achievements.get('points_earned', 0),
                    'session_points': self.game_state.session_points,
                    'quiz_mode': status['mode']
                })
            except Exception as e:
                return jsonify({
                    'quiz_active': False,
                    'total_questions': len(self.game_state.questions),
                    'categories': sorted(list(self.game_state.categories)),
                    'session_score': 0,
                    'session_total': 0,
                    'current_streak': 0,
                    'total_points': 0,
                    'session_points': 0,
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
        
        @self.app.route('/api/start_quiz', methods=['POST'])
        def api_start_quiz():
            try:
                data = request.get_json()
                quiz_mode = data.get('mode', 'standard')
                category = data.get('category')
                
                # Normalize category filter
                category_filter = None if category == "All Categories" else category
                
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
                    question_data = current_question['question_data']
                    q_text, options, _, category, _ = question_data
                    
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
                
                # No current question, so get the next one
                result = self.quiz_controller.get_next_question(self.quiz_controller.category_filter)
                
                if result is None:
                    return jsonify({'quiz_complete': True})
                
                # Store current question info (this is cached automatically by get_next_question)
                self.current_question_data = result['question_data']
                self.current_question_index = result['original_index']
                
                # Format response for web interface
                q_text, options, _, category, _ = result['question_data']
                
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
                

        @self.app.route('/api/submit_answer', methods=['POST'])
        def api_submit_answer():
            try:
                data = request.get_json()
                user_answer_index = data.get('answer_index')
                
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
                
                # Clear current question cache after processing
                self.quiz_controller.clear_current_question_cache()
                
                return jsonify(result)
                
            except Exception as e:
                print(f"Error in submit_answer: {e}")
                return jsonify({'error': str(e)})
        
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
        
        @self.app.route('/api/statistics')
        def api_statistics():
            try:
                return jsonify(self.stats_controller.get_detailed_statistics())
            except Exception as e:
                return jsonify({'error': str(e)})
        
        # Store reference to the route function
        self.api_statistics_handler = api_statistics
        
        @self.app.route('/api/achievements')
        def api_achievements():
            try:
                return jsonify(self.stats_controller.get_achievements_data())
            except Exception as e:
                return jsonify({'error': str(e)})
        
        # Store reference to the route function
        self.api_achievements_handler = api_achievements
        
        @self.app.route('/api/leaderboard')
        def api_leaderboard():
            try:
                return jsonify(self.stats_controller.get_leaderboard_data())
            except Exception as e:
                return jsonify({'error': str(e)})
        
        # Store reference to the route function
        self.api_leaderboard_handler = api_leaderboard
        
        @self.app.route('/api/clear_statistics', methods=['POST'])
        def api_clear_statistics():
            try:
                success = self.stats_controller.clear_statistics()
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        # Store reference to the route function
        self.api_clear_statistics_handler = api_clear_statistics
        
        @self.app.route('/api/review_incorrect')
        def api_review_incorrect():
            try:
                return jsonify(self.stats_controller.get_review_questions_data())
            except Exception as e:
                return jsonify({'error': str(e)})

        # Store reference to the route function
        self.api_review_incorrect_handler = api_review_incorrect

        @self.app.route('/api/remove_from_review', methods=['POST'])
        def api_remove_from_review():
            try:
                data = request.get_json()
                question_text = data.get('question_text')
                if not question_text:
                    return jsonify({'success': False, 'error': 'No question text provided'})
                
                success = self.stats_controller.remove_from_review_list(question_text)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # Store reference to the route function
        self.api_remove_from_review_handler = api_remove_from_review

        @self.app.route('/api/export_history')
        def api_export_history():
            try:
                from flask import make_response
                
                export_data = self.game_state.study_history.copy()
                export_data["export_metadata"] = {
                    "export_date": datetime.now().isoformat(),
                    "total_questions_in_pool": len(self.game_state.questions),
                    "categories_available": list(self.game_state.categories)
                }
                
                response = make_response(json.dumps(export_data, indent=2))
                response.headers['Content-Type'] = 'application/json'
                response.headers['Content-Disposition'] = f'attachment; filename=linux_plus_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                
                return response
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        self.export_history_handler = api_export_history
        @self.app.errorhandler(404)
        def not_found_error(error: Any) -> Tuple[Any, int]:
            return render_template('error.html', error="Page not found"), 404

        @self.app.errorhandler(500)
        def internal_error(error: Any) -> Tuple[Any, int]:
            return render_template('error.html', error="Internal server error"), 500
            
        # Store references to error handlers to prevent "not accessed" warnings
        self.not_found_error_handler = not_found_error
        self.internal_error_handler = internal_error

        @self.app.route('/api/load_settings')
        def api_load_settings():
            try:
                import json
                try:
                    with open('web_settings.json', 'r') as f:
                        settings = json.load(f)
                    
                    # Ensure all required fields exist with defaults
                    default_settings: Dict[str, Union[bool, int]] = {
                        'focusMode': False,
                        'breakReminder': 10,
                        'debugMode': False,
                        'pointsPerQuestion': 10,
                        'streakBonus': 5,
                        'maxStreakBonus': 50
                    }
                    
                    for key, default_value in default_settings.items():
                        if key not in settings:
                            settings[key] = default_value
                    
                    return jsonify({'success': True, 'settings': settings})
                except FileNotFoundError:
                    # Return comprehensive defaults
                    default_settings: Dict[str, Union[bool, int]] = {
                        'focusMode': False,
                        'breakReminder': 10,
                        'debugMode': False,
                        'pointsPerQuestion': 10,
                        'streakBonus': 5,
                        'maxStreakBonus': 50
                    }
                    return jsonify({'success': True, 'settings': default_settings})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        self.api_load_settings_handler = api_load_settings
        @self.app.route('/api/save_settings', methods=['POST'])
        def api_save_settings():
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'success': False, 'error': 'No data provided'})
                
                # Validate required fields
                required_fields = ['focusMode', 'breakReminder', 'debugMode', 'pointsPerQuestion', 'streakBonus', 'maxStreakBonus']
                for field in required_fields:
                    if field not in data:
                        return jsonify({'success': False, 'error': f'Missing field: {field}'})
                
                # Validate values
                if data['maxStreakBonus'] < data['streakBonus']:
                    data['maxStreakBonus'] = data['streakBonus']
                
                # Save to web_settings.json
                import json
                with open('web_settings.json', 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Apply settings to controllers and game state
                success = self._apply_settings_to_game_state(data)
                if not success:
                    return jsonify({'success': False, 'error': 'Failed to apply settings to game state'})
                
                return jsonify({'success': True, 'settings': data})
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
                
        # Store reference to make it clear the route is being used
        self.api_save_settings_handler = api_save_settings

        @self.app.route('/api/set_fullscreen', methods=['POST'])
        def api_set_fullscreen():
            try:
                data = request.get_json()
                enable = data.get('enable', True)
                result = self.toggle_fullscreen(enable)
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_set_fullscreen_handler = api_set_fullscreen

        @self.app.route('/api/get_fullscreen_status')
        def api_get_fullscreen_status():
            try:
                result = self.is_fullscreen()
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_get_fullscreen_status_handler = api_get_fullscreen_status
                
        @self.app.route('/api/question-count')
        def get_question_count():
            """Get the current number of questions available."""
            try:
                count = len(self.game_state.questions)
                return jsonify({
                    'success': True,
                    'count': count
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        # Store reference to make it clear the route is being used
        self.get_question_count_handler = get_question_count
        
        @self.app.route('/api/quiz_results')
        def api_quiz_results():
            """Get the results of the completed quiz session."""
            try:
                # Get results from the quiz controller
                results = self.quiz_controller.get_quiz_results()
                
                if results is None:
                    return jsonify({
                        'success': False,
                        'error': 'No quiz results available'
                    })
                
                return jsonify({
                    'success': True,
                    **results
                })
                
            except Exception as e:
                print(f"Error getting quiz results: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
        # Store reference to make it clear the route is being used
        self.api_quiz_results_handler = api_quiz_results

        @self.app.route('/api/session_summary')
        def api_session_summary():
            """Get a summary of the current/last quiz session."""
            try:
                summary = self.quiz_controller.get_session_summary()
                print(f"Session summary: {summary}")
                if summary is None:
                    return jsonify({
                        'success': False,
                        'error': 'No session summary available'
                    })
                
                return jsonify({
                    'success': True,
                    **summary
                })
                
            except Exception as e:
                print(f"Error getting session summary: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
        # Store reference to make it clear the route is being used
        self.api_session_summary_handler = api_session_summary
        
        @self.app.route('/vm_playground')
        def vm_playground():
            """Render VM management playground interface."""
            return render_template('vm_playground.html')
        # Store reference to make it clear the route is being used
        self.vm_playground_handler = vm_playground

        @self.app.route('/api/vm/start_ttyd', methods=['POST'])
        def api_start_ttyd():
            """API endpoint to start ttyd server on the VM with OS detection."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                data = request.get_json() or {}
                vm_name = data.get('vm_name', 'ubuntu-practice')  # Default VM name
                port = data.get('port', 7682)  # Default ttyd port
                
                # Detect OS type from VM name
                vm_name_lower = vm_name.lower()
                is_windows = any(keyword in vm_name_lower for keyword in ['win', 'windows', 'w10', 'w11'])
                
                if is_windows:
                    vm_manager = VMManager()
                    try:
                        domain = vm_manager.find_vm(vm_name)
                    except Exception as e:
                        return jsonify({'success': False, 'error': f'VM {vm_name} not found: {e}'})
                    
                    if not domain.isActive():
                        return jsonify({'success': False, 'error': f'VM {vm_name} is not running'})
                    
                    vm_ip = vm_manager.get_vm_ip(vm_name)
                    
                    return jsonify({
                        'success': False,
                        'error': 'ttyd is not supported on Windows VMs',
                        'suggestions': [
                            'Windows VMs require different remote access methods',
                            'Enable SSH first with: Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0',
                            'Or use Remote Desktop Protocol (RDP)',
                            f'RDP URL: rdp://{vm_ip}:3389'
                        ],
                        'rdp_url': f'rdp://{vm_ip}:3389',
                        'ssh_setup_commands': [
                            'Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0',
                            'Start-Service sshd',
                            'Set-Service -Name sshd -StartupType "Automatic"',
                            'New-NetFirewallRule -Name sshd -DisplayName "OpenSSH Server" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22'
                        ]
                    })
                
                # Linux VM ttyd setup (existing logic)
                vm_manager = VMManager()
                ssh_manager = SSHManager()
                
                # Get VM and check if running
                try:
                    domain = vm_manager.find_vm(vm_name)
                except Exception as e:
                    return jsonify({'success': False, 'error': f'VM {vm_name} not found: {e}'})
                
                if not domain.isActive():
                    return jsonify({'success': False, 'error': f'VM {vm_name} is not running'})
                
                vm_ip = vm_manager.get_vm_ip(vm_name)
                
                # SSH key path (adjust as needed)
                from pathlib import Path
                ssh_key_path = Path.home() / '.ssh' / 'id_ed25519'
                
                # Try different users for Linux VMs
                users_to_try = ['roo', 'root', 'ubuntu', 'vagrant', 'user']
                working_user = None
                
                # Find a working SSH user
                for username in users_to_try:
                    try:
                        test_result = ssh_manager.run_ssh_command(
                            host=vm_ip,
                            username=username,
                            key_path=ssh_key_path,
                            command="echo 'test'",
                            timeout=5
                        )
                        if test_result.get('exit_status') == 0:
                            working_user = username
                            break
                    except Exception:
                        continue
                
                if not working_user:
                    return jsonify({
                        'success': False,
                        'error': f'SSH connection failed for all attempted users: {users_to_try}',
                        'suggestions': [
                            'Check if SSH service is running: sudo systemctl status ssh',
                            'Verify SSH key is installed in ~/.ssh/authorized_keys',
                            'Check firewall rules: sudo ufw status'
                        ]
                    })
                
                # Check if ttyd is already running
                check_cmd = f"pgrep -f 'ttyd.*{port}'"
                check_result = ssh_manager.run_ssh_command(
                    host=vm_ip,
                    username=working_user,
                    key_path=ssh_key_path,
                    command=check_cmd,
                    timeout=10
                )
                
                if check_result.get('exit_status') == 0:
                    return jsonify({
                        'success': True,
                        'message': f'ttyd is already running on port {port}',
                        'url': f'http://{vm_ip}:{port}',
                        'username': working_user
                    })
                
                # Install ttyd if not present (run in background)
                install_cmd = "which ttyd || (sudo apt update && sudo apt install -y ttyd)"
                install_result = ssh_manager.run_ssh_command(
                    host=vm_ip,
                    username=working_user,
                    key_path=ssh_key_path,
                    command=install_cmd,
                    timeout=120  # Allow time for package installation
                )
                
                if install_result.get('exit_status') != 0:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to install ttyd: {install_result.get("stderr", "Unknown error")}'
                    })
                
                # Start ttyd in background with the requested command
                ttyd_cmd = f"sudo ttyd -p {port} -W -R bash"
                start_cmd = f"nohup {ttyd_cmd} > /dev/null 2>&1 & echo $!"
                
                start_result = ssh_manager.run_ssh_command(
                    host=vm_ip,
                    username=working_user,
                    key_path=ssh_key_path,
                    command=start_cmd,
                    timeout=10
                )
                
                if start_result.get('exit_status') == 0:
                    # Give ttyd a moment to start up
                    import time
                    time.sleep(2)
                    
                    # Verify ttyd is running
                    verify_result = ssh_manager.run_ssh_command(
                        host=vm_ip,
                        username=working_user,
                        key_path=ssh_key_path,
                        command=check_cmd,
                        timeout=5
                    )
                    
                    if verify_result.get('exit_status') == 0:
                        return jsonify({
                            'success': True,
                            'message': f'ttyd started successfully on port {port}',
                            'url': f'http://{vm_ip}:{port}',
                            'pid': start_result.get('stdout', '').strip(),
                            'username': working_user
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': 'ttyd failed to start or is not responding'
                        })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to start ttyd: {start_result.get("stderr", "Unknown error")}'
                    })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # Store reference to make it clear the route is being used
        self.api_start_ttyd_handler = api_start_ttyd

        @self.app.route('/full_terminal')
        def full_terminal():
            """Render full terminal access with ttyd integration."""
            return render_template('full_terminal.html')
        # Store reference to make it clear the route is being used
        self.full_terminal_handler = full_terminal

        @self.app.route('/debug_terminal')
        def debug_terminal():
            """Debug terminal functionality."""
            return render_template('debug_terminal.html')
        # Store reference to make it clear the route is being used
        self.debug_terminal_handler = debug_terminal

        @self.app.route('/terminal_test')
        def terminal_test():
            """Standalone terminal test page."""
            return render_template('terminal_test.html')
        # Store reference to make it clear the route is being used
        self.terminal_test_handler = terminal_test

        @self.app.route('/vm_test')
        def vm_test():
            """Render VM test page for debugging."""
            return render_template('vm_test.html')
        # Store reference to make it clear the route is being used
        self.vm_test_handler = vm_test

        @self.app.route('/api/vm/list', methods=['GET'])
        def api_vm_list():
            """API endpoint to list all VMs with enhanced error handling."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                # Check if libvirt is available
                try:
                    import libvirt  # type: ignore
                except ImportError:
                    return jsonify({
                        'success': False, 
                        'error': 'libvirt-python not installed. Please install with: pip install libvirt-python'
                    })
                
                # Check if VM manager can be initialized
                try:
                    vm_manager = VMManager()
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to initialize VM manager: {str(e)}'
                    })
                
                # Try to connect to libvirt
                try:
                    conn = vm_manager.connect_libvirt()
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to connect to libvirt: {str(e)}. Make sure libvirt is running.'
                    })
                
                vms: List[Dict[str, Any]] = []
                try:
                    # Get defined VMs with proper type annotation
                    defined_vms: List[str] = cast(List[str], conn.listDefinedDomains())
                    
                    # Get running VMs with proper type annotation
                    running_vm_ids = cast(List[int], conn.listDomainsID())
                    running_vms: List[str] = []
                    for vm_id in running_vm_ids:
                        try:
                            # Add proper type annotation for libvirt function
                            domain = cast(Any, conn).lookupByID(vm_id)
                            running_vms.append(str(domain.name()))
                        except Exception as e:
                            if hasattr(self, 'logger'):
                                self.logger.warning(f"Could not get running VM with ID {vm_id}: {e}")
            
                    # Combine all VMs with proper typing
                    all_vm_names: Set[str] = set(defined_vms + running_vms)
            
                    for vm_name in all_vm_names:
                        try:
                            # Add proper type annotation for libvirt function
                            domain = cast(Any, conn).lookupByName(vm_name)
                            is_active = bool(domain.isActive())
                            
                            vm_info: Dict[str, Any] = {
                                'name': vm_name,
                                'status': 'running' if is_active else 'stopped',
                                'id': domain.ID() if is_active else None
                            }
                            
                            # Try to get IP if running
                            if is_active:
                                try:
                                    vm_info['ip'] = vm_manager.get_vm_ip(vm_name)
                                except Exception as e:
                                    if hasattr(self, 'logger'):
                                        self.logger.debug(f"Could not get IP for VM {vm_name}: {e}")
                                    vm_info['ip'] = 'Unknown'
                            else:
                                vm_info['ip'] = 'Not running'
                            
                            vms.append(vm_info)
                            
                        except Exception as e:
                            if hasattr(self, 'logger'):
                                self.logger.warning(f"Error processing VM {vm_name}: {e}")
                            # Add error VM entry
                            vms.append({
                                'name': vm_name,
                                'status': 'error',
                                'error': str(e)
                            })
            
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'Error listing VMs: {str(e)}'
                    })
                finally:
                    try:
                        conn.close()
                    except:
                        pass
            
                return jsonify({
                    'success': True, 
                    'vms': sorted(vms, key=lambda x: x.get('name', ''))
                })
                
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.error(f"Unexpected error in VM list API: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': f'Unexpected error: {str(e)}'
                })
        # Store reference to make it clear the route is being used
        self.api_vm_list_handler = api_vm_list

        @self.app.route('/api/vm/start', methods=['POST'])
        def api_vm_start():
            """API endpoint to start a VM."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                data = request.get_json()
                vm_name = data.get('vm_name')
                
                if not vm_name:
                    return jsonify({'success': False, 'error': 'VM name is required'})
                
                vm_manager = VMManager()
                domain = vm_manager.find_vm(vm_name)
                
                if domain.isActive():
                    return jsonify({'success': False, 'error': f'VM {vm_name} is already running'})
                
                vm_manager.start_vm(vm_name)
                
                return jsonify({'success': True, 'message': f'VM {vm_name} started successfully'})
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # Store reference to make it clear the route is being used
        self.api_vm_start_handler = api_vm_start

        @self.app.route('/api/vm/stop', methods=['POST'])
        def api_vm_stop():
            """API endpoint to stop a VM."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                data = request.get_json()
                vm_name = data.get('vm_name')
                force = data.get('force', False)
                
                if not vm_name:
                    return jsonify({'success': False, 'error': 'VM name is required'})
                
                vm_manager = VMManager()
                domain = vm_manager.find_vm(vm_name)
                
                if not domain.isActive():
                    return jsonify({'success': False, 'error': f'VM {vm_name} is not running'})
                
                vm_manager.shutdown_vm(vm_name, force=force)
                
                action = 'force stopped' if force else 'shutdown initiated'
                return jsonify({'success': True, 'message': f'VM {vm_name} {action}'})
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # Store reference to make it clear the route is being used
        self.api_vm_stop_handler = api_vm_stop

        @self.app.route('/api/vm/execute', methods=['POST'])
        def api_vm_execute():
            """API endpoint to execute commands on a VM via SSH with OS detection."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                data = request.get_json()
                vm_name = data.get('vm_name')
                command = data.get('command')
                
                if not vm_name or not command:
                    return jsonify({'success': False, 'error': 'VM name and command are required'})
                
                vm_manager = VMManager()
                ssh_manager = SSHManager()
                
                # Get VM and check if running
                domain = vm_manager.find_vm(vm_name)
                
                if not domain.isActive():
                    return jsonify({'success': False, 'error': f'VM {vm_name} is not running'})
                
                vm_ip = vm_manager.get_vm_ip(vm_name)
                
                # Detect OS type from VM name
                vm_name_lower = vm_name.lower()
                is_windows = any(keyword in vm_name_lower for keyword in ['win', 'windows', 'w10', 'w11'])
                
                if is_windows:
                    return jsonify({
                        'success': False,
                        'error': 'Windows VMs require SSH to be enabled first',
                        'suggestions': [
                            'Enable SSH: Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0',
                            'Start SSH service: Start-Service sshd',
                            'Allow firewall: New-NetFirewallRule -Name sshd -DisplayName "OpenSSH Server" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22',
                            f'Alternative: Use RDP at rdp://{vm_ip}:3389'
                        ],
                        'rdp_url': f'rdp://{vm_ip}:3389'
                    })
                
                # Execute command via SSH (Linux VMs)
                from pathlib import Path
                ssh_key_path = Path.home() / '.ssh' / 'id_ed25519'
                
                # Try different users for Linux VMs
                users_to_try = ['roo', 'root', 'ubuntu', 'vagrant', 'user']
                successful_result = None
                
                for username in users_to_try:
                    try:
                        # Check if the command requires interactive mode (TTY)
                        interactive_commands = ['vim', 'nano', 'htop', 'top', 'man', 'less', 'more', 'vi']
                        is_interactive = any(cmd in command.lower() for cmd in interactive_commands)
                        
                        if is_interactive:
                            # Use interactive SSH method for commands that need TTY
                            result = ssh_manager.run_interactive_ssh_command(
                                host=vm_ip,
                                username=username,
                                key_path=ssh_key_path,
                                command=command,
                                timeout=60,  # Longer timeout for interactive commands
                                verbose=True
                            )
                        else:
                            # Use regular SSH method for non-interactive commands
                            result = ssh_manager.run_ssh_command(
                                host=vm_ip,
                                username=username,
                                key_path=ssh_key_path,
                                command=command,
                                timeout=30,
                                verbose=True
                            )
                        
                        # If successful, break the loop
                        if result.get('error') is None and result.get('exit_status') == 0:
                            successful_result = result
                            successful_result['username'] = username
                            break
                            
                    except Exception as e:
                        # Try next user
                        continue
                
                if successful_result:
                    return jsonify({
                        'success': True,
                        'output': successful_result.get('stdout', ''),
                        'error': successful_result.get('stderr', ''),
                        'exit_status': successful_result.get('exit_status', 0),
                        'username': successful_result.get('username', 'unknown')
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'SSH connection failed for all attempted users: {users_to_try}',
                        'suggestions': [
                            'Check if SSH service is running: sudo systemctl status ssh',
                            'Verify SSH key is installed in ~/.ssh/authorized_keys',
                            'Check firewall rules: sudo ufw status',
                            'Verify VM is fully booted and network is configured'
                        ]
                    })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # Store reference to make it clear the route is being used
        self.api_vm_execute_handler = api_vm_execute

        @self.app.route('/api/vm/status', methods=['GET'])
        def api_vm_status():
            """API endpoint to get detailed VM status."""
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
                
                is_active = bool(domain.isActive())
                status_info: Dict[str, Any] = {
                    'name': vm_name,
                    'status': 'running' if is_active else 'stopped',
                    'id': domain.ID() if is_active else None,
                    'ip': None,
                    'uptime': None
                }
                
                # Try to get IP if running
                if is_active:
                    try:
                        status_info['ip'] = vm_manager.get_vm_ip(vm_name)
                    except Exception:
                        status_info['ip'] = 'Unknown'
                
                return jsonify({'success': True, 'status': status_info})
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_vm_status_handler = api_vm_status
        
        @self.app.route('/api/vm/details', methods=['GET'])
        def api_vm_details():
            """API endpoint to get detailed VM information."""
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
                
                is_active = bool(domain.isActive())
                
                # Get VM info
                info = domain.info()
                
                # Format memory more intelligently
                def format_memory(memory_kb):
                    """Format memory from KB to human readable format"""
                    if not memory_kb:
                        return 'Unknown'
                    
                    memory_mb = memory_kb // 1024
                    if memory_mb >= 1024:
                        memory_gb = memory_mb / 1024
                        return f"{memory_gb:.1f} GB"
                    else:
                        return f"{memory_mb} MB"
                
                vm_details = {
                    'name': vm_name,
                    'status': 'running' if is_active else 'stopped',
                    'id': domain.ID() if is_active else None,
                    'memory': format_memory(info[1]) if info else 'Unknown',
                    'cpu': str(info[3]) if info else 'Unknown',
                    'ip': None
                }
                
                # Try to get IP if running
                if is_active:
                    try:
                        vm_details['ip'] = vm_manager.get_vm_ip(vm_name)
                    except Exception:
                        vm_details['ip'] = 'Unknown'
                
                return jsonify({
                    'success': True, 
                    'vm': vm_details
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_vm_details_handler = api_vm_details

        @self.app.route('/api/vm/create', methods=['POST'])
        def api_vm_create():
            """API endpoint to create a new VM."""
            if not VMManager:
                return jsonify({
                    'success': False,
                    'error': 'VM Manager not available. Please check libvirt installation.'
                })
            try:
                data = request.get_json()
                vm_name = data.get('name')
                template = data.get('template', 'ubuntu-22.04')
                memory = data.get('memory', 2)
                cpus = data.get('cpus', 1)
                disk = data.get('disk', 20)
                auto_start = data.get('auto_start', False)
                
                if not vm_name:
                    return jsonify({'success': False, 'error': 'VM name is required'})
                
                # Validate VM name (alphanumeric, hyphens, underscores only)
                import re
                if not re.match(r'^[a-zA-Z0-9_-]+$', vm_name):
                    return jsonify({
                        'success': False, 
                        'error': 'VM name must contain only alphanumeric characters, hyphens, and underscores'
                    })
                
                vm_manager = VMManager()
                
                # Check if VM already exists
                try:
                    vm_manager.find_vm(vm_name)
                    return jsonify({
                        'success': False,
                        'error': f'VM "{vm_name}" already exists'
                    })
                except Exception:
                    # VM doesn't exist, we can create it
                    pass
                
                # Create VM using VMManager
                try:
                    success = vm_manager.create_vm(
                        vm_name=vm_name,
                        memory_gb=int(memory),
                        cpus=int(cpus),
                        disk_gb=int(disk)
                    )
                    
                    if not success:
                        return jsonify({
                            'success': False,
                            'error': 'Failed to create VM'
                        })
                    
                    # Auto-start if requested
                    if auto_start:
                        try:
                            vm_manager.start_vm(vm_name)
                            message = f'VM "{vm_name}" created and started successfully'
                        except Exception as start_error:
                            message = f'VM "{vm_name}" created successfully but failed to start: {start_error}'
                    else:
                        message = f'VM "{vm_name}" created successfully (not started)'
                    
                    return jsonify({
                        'success': True,
                        'message': message,
                        'vm_info': {
                            'name': vm_name,
                            'template': template,
                            'memory': f'{memory} GB',
                            'cpus': cpus,
                            'disk': f'{disk} GB',
                            'auto_started': auto_start
                        }
                    })
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to create VM: {str(e)}'
                    })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        # Store reference to make it clear the route is being used
        self.api_vm_create_handler = api_vm_create

        @self.app.route('/api/vm/challenges', methods=['GET'])
        def api_vm_challenges():
            """API endpoint to list available challenges."""
            try:
                from vm_integration.controllers.vm_controller import list_available_challenges
                challenges = list_available_challenges()
                return jsonify({
                    'success': True,
                    'challenges': challenges
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/vm/run_challenge', methods=['POST'])
        def api_vm_run_challenge():
            """API endpoint to run a challenge."""
            try:
                data = request.get_json()
                challenge_id = data.get('challenge_id')
                vm_name = data.get('vm_name', 'ubuntu-practice')
                
                if not challenge_id:
                    return jsonify({
                        'success': False,
                        'error': 'Challenge ID is required'
                    }), 400
                
                from vm_integration.controllers.vm_controller import run_challenge_workflow
                result = run_challenge_workflow(challenge_id=challenge_id, vm_name=vm_name)
                
                return jsonify({
                    'success': True,
                    'result': result
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

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
                    snapshots = snapshot_manager.list_snapshots(domain)
                except Exception as e:
                    self.logger.debug(f"Error listing snapshots: {e}")
                    snapshots = []
                
                return jsonify({
                    'success': True,
                    'snapshots': sorted(snapshots, key=lambda x: x.get('name', ''))
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
                data = request.get_json()
                vm_name = data.get('vm_name')
                snapshot_name = data.get('snapshot_name')
                description = data.get('description', '')
                
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
                data = request.get_json()
                vm_name = data.get('vm_name')
                snapshot_name = data.get('snapshot_name')
                
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
                data = request.get_json()
                vm_name = data.get('vm_name')
                snapshot_name = data.get('snapshot_name')
                
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
        @self.app.route('/api/vm/setup_user', methods=['POST'])
        def api_vm_setup_user():
            """API endpoint to setup VM user."""
            try:
                data = request.get_json()
                vm_name = data.get('vm_name', 'ubuntu-practice')
                new_user = data.get('new_user', 'student')
                
                from vm_integration.controllers.vm_controller import setup_vm_user
                result = setup_vm_user(vm_name=vm_name, new_user=new_user)
                
                return jsonify({
                    'success': True,
                    'result': result
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/vm/create_template', methods=['POST'])
        def api_vm_create_template():
            """API endpoint to create challenge template."""
            try:
                data = request.get_json()
                template_name = data.get('template_name')
                
                if not template_name:
                    return jsonify({
                        'success': False,
                        'error': 'Template name is required'
                    }), 400
                
                from vm_integration.controllers.vm_controller import create_challenge_template
                result = create_challenge_template(template_name)
                
                return jsonify({
                    'success': True,
                    'result': result
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/vm/validate_challenge', methods=['POST'])
        def api_vm_validate_challenge():
            """API endpoint to validate challenge file."""
            try:
                data = request.get_json()
                challenge_path = data.get('challenge_path')
                
                if not challenge_path:
                    return jsonify({
                        'success': False,
                        'error': 'Challenge path is required'
                    }), 400
                
                from vm_integration.controllers.vm_controller import validate_challenge
                result = validate_challenge(challenge_path)
                
                return jsonify({
                    'success': True,
                    'result': result
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    def handle_api_errors(self, f: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logging.error(f"API Error in {f.__name__}: {str(e)}")
                logging.error(traceback.format_exc())
                return jsonify({
                    'error': f'Server error: {str(e)}',
                    'success': False
                }), 500
        wrapper.__name__ = f.__name__
        return wrapper
    
    def run_flask_app(self):
        """Run the Flask app in a separate thread."""
        self.app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    
    def start(self):
        """Start the web interface in a desktop window."""
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=self.run_flask_app, daemon=True)
        flask_thread.start()
        
        # Wait a moment for Flask to start
        time.sleep(1)
        
        # Create the desktop window
        window = webview.create_window(
            title='Linux+ Study Game',
            url='http://127.0.0.1:5000',
            width=1200,
            height=900,
            min_size=(800, 600),
            resizable=True
        )
        
        # Store window reference for fullscreen control
        self.window = window
        
        # Start the webview (this blocks until window is closed)
        webview.start(debug=self.debug)
    
    def quit_app(self):
        """Clean shutdown of the application."""
        # Save any pending data
        self.game_state.save_history()
        # Add runtime check for save_achievements
        if hasattr(self.game_state, "save_achievements") and callable(self.game_state.save_achievements):
            self.game_state.save_achievements()
        
        # Close the webview window
        if self.window:
            self.window.destroy()