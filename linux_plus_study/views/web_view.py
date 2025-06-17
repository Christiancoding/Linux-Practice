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
import json
from datetime import datetime
import hashlib
import time
import logging
import traceback
from utils.cli_playground import get_cli_playground
import subprocess
import shlex
from utils.config import (
    QUICK_FIRE_QUESTIONS, QUICK_FIRE_TIME_LIMIT, MINI_QUIZ_QUESTIONS,
    POINTS_PER_CORRECT, POINTS_PER_INCORRECT, STREAK_BONUS_THRESHOLD, STREAK_BONUS_MULTIPLIER
)
from werkzeug.utils import secure_filename
import tempfile
import mimetypes

cli_playground = get_cli_playground()

class LinuxPlusStudyWeb:
    """Web interface using Flask + pywebview for desktop app experience."""
    
    def __init__(self, game_state, debug=False):
        self.game_state = game_state
        self.app = Flask(__name__, 
                        template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
                        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))
        self.debug = debug
        self.window = None

        # Add caching to reduce lag
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300  # Cache static files for 5 minutes
        self.app.config['TEMPLATES_AUTO_RELOAD'] = False  # Disable template auto-reload in production
        self.setup_cli_playground_routes(self.app)
        
        # Session configuration for better performance
        self.app.secret_key = 'your-secret-key-here'  # Add a proper secret key
        self.app.config['SESSION_TYPE'] = 'filesystem'
        self.app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

        from controllers.quiz_controller import QuizController
        from controllers.stats_controller import StatsController
        
        self.quiz_controller = QuizController(game_state)
        self.stats_controller = StatsController(game_state)
        self.current_category_filter = None
        self.current_question_data = None
        self.current_question_index = -1
        
        self.setup_routes()
    def _should_show_break_reminder(self):
        """Check if break reminder should be shown based on current settings."""
        disabled_modes = {'daily_challenge', 'pop_quiz', 'quick_fire', 'mini_quiz'}
        if self.quiz_controller.current_quiz_mode in disabled_modes:
            return False
        try:
            settings = self._load_web_settings()
            break_interval = settings.get('breakReminder', 10)
            
            # Check if break reminders are enabled (interval > 0) and threshold met
            return (break_interval > 0 and 
                    self.quiz_controller.questions_since_break >= break_interval)
        except:
            return False
    
    def _get_break_interval(self):
        """Get the current break reminder interval from settings."""
        try:
            settings = self._load_web_settings()
            return settings.get('breakReminder', 10)
        except:
            return 10

    def _load_web_settings(self):
        """Load settings from web_settings.json file."""
        try:
            if os.path.exists('web_settings.json'):
                with open('web_settings.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading web settings: {e}")
        
        # Return default settings if file doesn't exist or can't be loaded
        return {'focusMode': False, 'breakReminder': 10}

    def toggle_fullscreen(self, enable=True):
        """Toggle application window fullscreen."""
        try:
            if hasattr(self, 'window') and self.window:
                self.window.fullscreen = enable
                return {'success': True, 'fullscreen': enable}
            return {'success': False, 'error': 'Window not available'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def is_fullscreen(self):
        """Check if window is in fullscreen mode."""
        try:
            if hasattr(self, 'window') and self.window:
                return {'success': True, 'fullscreen': getattr(self.window, 'fullscreen', False)}
            return {'success': False, 'fullscreen': False}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    def setup_cli_playground_routes(self, app):
        """Setup CLI playground API routes"""
        
        # Store command history in memory (you could also use a file)
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

        @app.route('/api/cli/commands', methods=['GET'])
        def get_available_commands():
            """Get list of available CLI commands"""
            try:
                commands = list(cli_playground.safe_commands.keys())
                commands.sort()
                
                command_descriptions = {
                    'ls': 'List directory contents',
                    'pwd': 'Print working directory',
                    'cd': 'Change directory',
                    'echo': 'Display text',
                    'cat': 'Display file contents',
                    'head': 'Display first lines of file',
                    'tail': 'Display last lines of file',
                    'grep': 'Search for pattern in file',
                    'find': 'Find files',
                    'wc': 'Word, line, character count',
                    'sort': 'Sort lines in file',
                    'uniq': 'Remove duplicate lines',
                    'date': 'Display current date',
                    'whoami': 'Display current user',
                    'ps': 'Display running processes'
                }
                
                result = []
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
    def setup_export_import_routes(self):
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
                content_lines = []
                
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
                
                # Join content
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
                    }), 400
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"Linux_plus_QA_{timestamp}.json"
                
                # Prepare questions data for JSON export
                questions_data = []
                for i, q_data in enumerate(self.game_state.questions):
                    if len(q_data) < 5: 
                        continue
                    question_text, options, correct_answer_index, category, explanation = q_data
                    
                    question_obj = {
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
                export_data = {
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
        def import_questions():
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
                
                filename = secure_filename(file.filename)
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
                
                # Parse questions
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
                errors = []
                
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
    def _parse_json_questions(self, content):
        """
        Parse questions from JSON content with comprehensive format support.
        
        Args:
            content (str): JSON content string
            
        Returns:
            List[dict]: Normalized question dictionaries
            
        Raises:
            ValueError: If JSON format is invalid or unsupported
        """
        try:
            data = json.loads(content)
            questions = []
            
            # Handle different JSON formats
            if isinstance(data, list):
                # Direct list of questions
                for item in data:
                    if isinstance(item, dict):
                        questions.append(self._normalize_question_dict(item))
                    elif isinstance(item, (list, tuple)) and len(item) >= 4:
                        # Handle tuple format: (question, options, correct_index, category, explanation)
                        questions.append({
                            'question': str(item[0]),
                            'options': list(item[1]) if len(item) > 1 else [],
                            'correct_answer_index': int(item[2]) if len(item) > 2 else 0,
                            'category': str(item[3]) if len(item) > 3 else 'General',
                            'explanation': str(item[4]) if len(item) > 4 else ''
                        })
                            
            elif isinstance(data, dict):
                if 'questions' in data:
                    # Structured format with metadata
                    for item in data['questions']:
                        if isinstance(item, dict):
                            questions.append(self._normalize_question_dict(item))
                        elif isinstance(item, (list, tuple)) and len(item) >= 4:
                            questions.append({
                                'question': str(item[0]),
                                'options': list(item[1]) if len(item) > 1 else [],
                                'correct_answer_index': int(item[2]) if len(item) > 2 else 0,
                                'category': str(item[3]) if len(item) > 3 else 'General',
                                'explanation': str(item[4]) if len(item) > 4 else ''
                            })
                else:
                    # Single question object
                    questions.append(self._normalize_question_dict(data))
            
            return questions
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing JSON content: {e}")

    def _parse_markdown_questions(self, content):
        """
        Enhanced markdown parser for Linux+ study format with comprehensive validation.
        
        Handles format:
        **Q1.** (Category)
        Question text
        A. Option A
        B. Option B
        ...
        
        **A1.** C. Option text
        *Explanation:* Detailed explanation
        """
        questions = []
        lines = content.split('\n')
        
        # State tracking variables
        in_questions_section = False
        in_answers_section = False
        current_question = None
        current_options = []
        answers_dict = {}
        explanations_dict = {}
        
        # Enhanced parsing with robust error handling
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            try:
                # Section detection
                if line == "# Questions":
                    in_questions_section = True
                    in_answers_section = False
                    continue
                elif line == "# Answers":
                    in_questions_section = False
                    in_answers_section = True
                    continue
                elif line == "---":
                    in_questions_section = False
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
                    import re
                    question_match = re.match(r'\*\*Q(\d+)\.\*\*\s*\(([^)]+)\)', line)
                    if question_match:
                        question_number = int(question_match.group(1))
                        category = question_match.group(2).strip()
                        
                        # Get question text (next non-empty line)
                        i += 1
                        question_text = ""
                        while i < len(lines) and lines[i].strip():
                            question_line = lines[i].strip()
                            # Stop if we hit an option
                            if re.match(r'^[A-Z]\.\s', question_line):
                                i -= 1  # Back up to process this line as option
                                break
                            question_text += " " + question_line if question_text else question_line
                            i += 1
                        
                        current_question = {
                            'number': question_number,
                            'text': question_text.strip(),
                            'category': category
                        }
                        current_options = []
                
                # Option parsing
                elif in_questions_section and re.match(r'^[A-Z]\.\s', line):
                    option_text = line[3:].strip()  # Remove "A. ", "B. ", etc.
                    current_options.append(option_text)
                
                # Answer parsing
                elif in_answers_section and line.startswith("**A"):
                    # Format: **A1.** C. Option text
                    answer_match = re.match(r'\*\*A(\d+)\.\*\*\s*([A-Z])\.\s*(.*)', line)
                    if answer_match:
                        answer_number = int(answer_match.group(1))
                        correct_letter = answer_match.group(2)
                        correct_index = ord(correct_letter) - ord('A')
                        answers_dict[answer_number] = correct_index
                        
                        # Look for explanation on following lines
                        explanation = ""
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            if next_line.startswith("*Explanation:*"):
                                # Extract explanation text
                                explanation = next_line.replace("*Explanation:*", "").strip()
                                j += 1
                                # Continue reading explanation lines
                                while j < len(lines):
                                    exp_line = lines[j].strip()
                                    if exp_line.startswith("**A") or exp_line.startswith("**Q") or not exp_line:
                                        break
                                    explanation += " " + exp_line
                                    j += 1
                                break
                            elif next_line.startswith("**A") or not next_line:
                                break
                            j += 1
                        
                        explanations_dict[answer_number] = explanation.strip()
            
            except Exception as e:
                print(f"Warning: Error parsing line {i}: '{line}': {e}")
            
            i += 1
        
        # Add final question if exists
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
            question_num = question['question_number']
            if question_num in answers_dict:
                question['correct_answer_index'] = answers_dict[question_num]
            if question_num in explanations_dict:
                question['explanation'] = explanations_dict[question_num]
        
        return questions

    def _detect_and_eliminate_duplicates(self, new_questions, existing_questions=None):
        """
        Comprehensive duplicate detection and elimination system.
        
        Args:
            new_questions (list): Questions being imported
            existing_questions (list): Current questions in the system
            
        Returns:
            tuple: (filtered_questions, duplicate_report)
        """
        if existing_questions is None:
            existing_questions = self.game_state.questions
        
        # Convert existing questions to comparable format
        existing_set = set()
        for q_data in existing_questions:
            if len(q_data) >= 5:
                question_text, options, _, category, _ = q_data
                # Create normalized signature
                signature = self._create_question_signature(question_text, options, category)
                existing_set.add(signature)
        
        # Process new questions for duplicates
        filtered_questions = []
        duplicates_found = []
        internal_duplicates = set()
        
        for i, question in enumerate(new_questions):
            signature = self._create_question_signature(
                question['question'], 
                question['options'], 
                question['category']
            )
            
            # Check against existing questions
            if signature in existing_set:
                duplicates_found.append({
                    'type': 'existing_duplicate',
                    'question_number': i + 1,
                    'question_text': question['question'][:100] + '...' if len(question['question']) > 100 else question['question']
                })
                continue
            
            # Check for internal duplicates within import
            if signature in internal_duplicates:
                duplicates_found.append({
                    'type': 'internal_duplicate',
                    'question_number': i + 1,
                    'question_text': question['question'][:100] + '...' if len(question['question']) > 100 else question['question']
                })
                continue
            
            # Question is unique
            internal_duplicates.add(signature)
            filtered_questions.append(question)
        
        duplicate_report = {
            'total_processed': len(new_questions),
            'duplicates_found': len(duplicates_found),
            'unique_questions': len(filtered_questions),
            'duplicate_details': duplicates_found
        }
        
        return filtered_questions, duplicate_report

    def _create_question_signature(self, question_text, options, category):
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
        normalized_options = []
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

    def _normalize_question_dict(self, question_dict):
        """
        Normalize question dictionary to standard format with validation.
        
        Args:
            question_dict (dict): Raw question dictionary
            
        Returns:
            dict: Normalized question dictionary
        """
        try:
            # Handle different possible field names
            question_text = (
                question_dict.get('question') or 
                question_dict.get('question_text') or 
                question_dict.get('text') or 
                ''
            )
            
            options = (
                question_dict.get('options') or 
                question_dict.get('choices') or 
                question_dict.get('answers') or 
                []
            )
            
            # Handle different correct answer formats
            correct_answer_index = 0
            if 'correct_answer_index' in question_dict:
                correct_answer_index = int(question_dict['correct_answer_index'])
            elif 'correct_index' in question_dict:
                correct_answer_index = int(question_dict['correct_index'])
            elif 'correct_answer' in question_dict:
                # Try to find the index of the correct answer
                correct_answer = question_dict['correct_answer']
                if isinstance(correct_answer, str) and len(correct_answer) == 1 and correct_answer.isalpha():
                    # Letter format (A, B, C, D)
                    correct_answer_index = ord(correct_answer.upper()) - ord('A')
                elif isinstance(correct_answer, str) and correct_answer in options:
                    # Full text match
                    correct_answer_index = options.index(correct_answer)
            
            # Validate correct_answer_index
            if not (0 <= correct_answer_index < len(options)) and options:
                correct_answer_index = 0
            
            category = (
                question_dict.get('category') or 
                question_dict.get('topic') or 
                question_dict.get('subject') or 
                'General'
            )
            
            explanation = (
                question_dict.get('explanation') or 
                question_dict.get('rationale') or 
                question_dict.get('details') or 
                ''
            )
            
            return {
                'question': str(question_text),
                'options': [str(opt) for opt in options],
                'correct_answer_index': correct_answer_index,
                'category': str(category),
                'explanation': str(explanation)
            }
            
        except Exception as e:
            print(f"Warning: Error normalizing question: {e}")
            return {
                'question': str(question_dict.get('question', 'Invalid question')),
                'options': ['A', 'B', 'C', 'D'],
                'correct_answer_index': 0,
                'category': 'General',
                'explanation': ''
            }

    def _add_question_to_pool(self, question_tuple):
        """
        Add a question tuple to the current question pool with enhanced integration.
        
        Args:
            question_tuple (tuple): Question data in tuple format
        """
        try:
            # Method 1: Try using question manager if available
            if hasattr(self.game_state, 'question_manager') and self.game_state.question_manager:
                from models.question import Question
                try:
                    question_obj = Question.from_tuple(question_tuple)
                    self.game_state.question_manager.add_question(question_obj)
                    return True
                except Exception as e:
                    print(f"Warning: Question manager failed: {e}")
            
            # Method 2: Direct integration with game state
            if hasattr(self.game_state, 'questions'):
                # Ensure questions is a list
                if not isinstance(self.game_state.questions, list):
                    self.game_state.questions = list(self.game_state.questions)
                
                # Add the new question
                self.game_state.questions.append(question_tuple)
                
                # Update categories if possible
                if hasattr(self.game_state, 'categories') and len(question_tuple) > 3:
                    if isinstance(self.game_state.categories, set):
                        self.game_state.categories.add(question_tuple[3])
                    elif isinstance(self.game_state.categories, list):
                        if question_tuple[3] not in self.game_state.categories:
                            self.game_state.categories.append(question_tuple[3])
                
                return True
            
            # Method 3: Fallback - store in temporary container
            if not hasattr(self.game_state, '_imported_questions'):
                self.game_state._imported_questions = []
            self.game_state._imported_questions.append(question_tuple)
            
            print(f"Warning: Question added to temporary storage. Manual integration may be required.")
            return True
            
        except Exception as e:
            print(f"Error adding question to pool: {e}")
            return False
    def _simulate_command(self, command):
        """Simulate common commands with educational examples"""
        
        # Create sample files content
        sample_files = {
            'sample.txt': 'Hello Linux Plus student!\nThis is a sample text file.\nPractice your command line skills here.\nGood luck with your certification!',
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

    def _get_help_text(self):
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
    def reset_quiz_state(self):
        """Reset quiz state variables."""
        self.quiz_active = False
        self.current_quiz_mode = None
        self.current_category_filter = None
        self.current_question_data = None
        self.current_question_index = -1
        self.current_streak = 0
        self.quick_fire_start_time = None
        self.quick_fire_questions_answered = 0
    def setup_routes(self):
        """Setup Flask routes for the web interface."""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/quiz')
        def quiz_page():
            return render_template('quiz.html')
        
        @self.app.route('/stats')
        def stats_page():
            return render_template('stats.html')
        
        @self.app.route('/achievements')
        def achievements_page():
            return render_template('achievements.html')
        
        @self.app.route('/review')
        def review_page():
            return render_template('review.html')
        
        @self.app.route('/settings')
        def settings_page():
            return render_template('settings.html')
        
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
        @self.app.route('/cli-playground')
        def cli_playground_page():
            """CLI Playground page"""
            return render_template('cli_playground.html', 
                                title='CLI Playground',
                                active_page='cli_playground')
        
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
        
        @self.app.route('/api/end_quiz', methods=['POST'])
        def api_end_quiz():
            try:
                if not self.quiz_controller.quiz_active:
                    return jsonify({'success': True, 'message': 'No active quiz session'})
                
                result = self.quiz_controller.force_end_session()
                
                return jsonify({'success': True, **result})
                
            except Exception as e:
                print(f"Error in end_quiz: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
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
        
        # Special mode starters - simplified
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
        
        # Other API routes remain the same...
        @self.app.route('/api/statistics')
        def api_statistics():
            try:
                return jsonify(self.stats_controller.get_detailed_statistics())
            except Exception as e:
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/achievements')
        def api_achievements():
            try:
                return jsonify(self.stats_controller.get_achievements_data())
            except Exception as e:
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/leaderboard')
        def api_leaderboard():
            try:
                return jsonify(self.stats_controller.get_leaderboard_data())
            except Exception as e:
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/clear_statistics', methods=['POST'])
        def api_clear_statistics():
            try:
                success = self.stats_controller.clear_statistics()
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/review_incorrect')
        def api_review_incorrect():
            try:
                return jsonify(self.stats_controller.get_review_questions_data())
            except Exception as e:
                return jsonify({'error': str(e)})

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
        
        @self.app.errorhandler(404)
        def not_found_error(error):
            return render_template('error.html', error="Page not found"), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return render_template('error.html', error="Internal server error"), 500
        
        @self.app.route('/api/save_settings', methods=['POST'])
        def api_save_settings():
            try:
                data = request.get_json()
                settings = {
                    'focusMode': data.get('focusMode', False),
                    'breakReminder': data.get('breakReminder', 10),
                    'timestamp': time.time()
                }
                
                # Save to a simple file (you could also use the game_state)
                import json
                with open('web_settings.json', 'w') as f:
                    json.dump(settings, f)
                
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/load_settings')
        def api_load_settings():
            try:
                import json
                try:
                    with open('web_settings.json', 'r') as f:
                        settings = json.load(f)
                    return jsonify({'success': True, 'settings': settings})
                except FileNotFoundError:
                    # Return defaults
                    return jsonify({'success': True, 'settings': {'focusMode': False, 'breakReminder': 10}})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        # Add these routes in the setup_routes method after the existing routes

        @self.app.route('/api/set_fullscreen', methods=['POST'])
        def api_set_fullscreen():
            try:
                data = request.get_json()
                enable = data.get('enable', True)
                result = self.toggle_fullscreen(enable)
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/get_fullscreen_status')
        def api_get_fullscreen_status():
            try:
                result = self.is_fullscreen()
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
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
        self.setup_export_import_routes()
    def handle_api_errors(f):
        def wrapper(*args, **kwargs):
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
    def _get_help_text(self):
        """Get help text for CLI playground commands."""
        help_func = cli_playground.safe_commands.get('help', lambda args: "No help available")
        return help_func([])  # Pass empty args list

    def _simulate_command(self, command):
        """Simulate command execution using the CLI playground."""
        try:
            return cli_playground.process_command(command)
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
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
        self.game_state.save_achievements()
        
        # Close the webview window
        if self.window:
            self.window.destroy()