#!/usr/bin/env python3
"""
Database utilities for file operations in the Linux+ Study Game.
Handles loading and saving of history, achievements, questions, and exports.
"""

import json
import os
from datetime import datetime
from utils.config import (
    HISTORY_FILE, ACHIEVEMENTS_FILE, SAMPLE_QUESTIONS,
    COLOR_INFO, COLOR_ERROR, COLOR_WARNING, COLOR_RESET
)


class DatabaseManager:
    """Handles all file I/O operations for the study game."""
    
    @staticmethod
    def load_history(history_file=HISTORY_FILE, default_history_func=None):
        """
        Load study history from file if it exists.
        
        Args:
            history_file (str): Path to history file
            default_history_func (callable): Function that returns default history structure
            
        Returns:
            dict: Study history data
        """
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                
                # Ensure all default keys exist if default_history_func provided
                if default_history_func:
                    default = default_history_func()
                    for key, default_value in default.items():
                        history.setdefault(key, default_value)
                
                # Basic type validation
                if not isinstance(history.get("questions"), dict): 
                    history["questions"] = {}
                if not isinstance(history.get("categories"), dict): 
                    history["categories"] = {}
                if not isinstance(history.get("sessions"), list): 
                    history["sessions"] = []
                if not isinstance(history.get("incorrect_review"), list): 
                    history["incorrect_review"] = []
                    
                return history
                
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"{COLOR_INFO} History file not found or invalid. Starting fresh. {COLOR_RESET}")
            return default_history_func() if default_history_func else {}
            
        except Exception as e:
            print(f"{COLOR_ERROR} Error loading history file '{history_file}': {e} {COLOR_RESET}")
            print(f"{COLOR_WARNING} Starting with empty history. {COLOR_RESET}")
            return default_history_func() if default_history_func else {}

    @staticmethod
    def save_history(history_data, history_file=HISTORY_FILE):
        """
        Save study history to file.
        
        Args:
            history_data (dict): History data to save
            history_file (str): Path to history file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2)
            return True
            
        except IOError as e:
            print(f"{COLOR_ERROR} Error saving history: {e} {COLOR_RESET}")
            return False
            
        except Exception as e:
            print(f"{COLOR_ERROR} An unexpected error occurred during history save: {e} {COLOR_RESET}")
            return False

    @staticmethod
    def load_achievements(achievements_file=ACHIEVEMENTS_FILE):
        """
        Load achievements from file.
        
        Args:
            achievements_file (str): Path to achievements file
            
        Returns:
            dict: Achievements data
        """
        try:
            with open(achievements_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "badges": [],
                "points_earned": 0,
                "days_studied": set(),
                "questions_answered": 0,
                "streaks_achieved": 0,
                "perfect_sessions": 0
            }

    @staticmethod
    def save_achievements(achievements_data, achievements_file=ACHIEVEMENTS_FILE):
        """
        Save achievements to file.
        
        Args:
            achievements_data (dict): Achievements data to save
            achievements_file (str): Path to achievements file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert set to list for JSON serialization
            achievements_copy = achievements_data.copy()
            if isinstance(achievements_copy.get("days_studied"), set):
                achievements_copy["days_studied"] = list(achievements_copy["days_studied"])
            
            with open(achievements_file, 'w', encoding='utf-8') as f:
                json.dump(achievements_copy, f, indent=2)
            return True
            
        except Exception as e:
            print(f"{COLOR_ERROR} Error saving achievements: {e} {COLOR_RESET}")
            return False

    @staticmethod
    def load_questions(questions_file="linux_plus_questions.json"):
        """
        Load questions from file and combine with sample questions.
        
        Args:
            questions_file (str): Path to additional questions file
            
        Returns:
            list: Combined list of questions
        """
        # Start with sample questions
        all_questions = list(SAMPLE_QUESTIONS)
        
        # Try to load additional questions from file
        try:
            with open(questions_file, 'r', encoding='utf-8') as f:
                file_questions = json.load(f)
                if isinstance(file_questions, list):
                    all_questions.extend(file_questions)
                    
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"{COLOR_INFO} No additional questions file found. Using built-in questions. {COLOR_RESET}")
            
        except Exception as e:
            print(f"{COLOR_WARNING} Error loading questions file: {e} {COLOR_RESET}")
            
        return all_questions

    @staticmethod
    def export_history_json(history_data, filename=None):
        """
        Export study history to JSON file.
        
        Args:
            history_data (dict): History data to export
            filename (str): Output filename, auto-generated if None
            
        Returns:
            tuple: (success: bool, filepath: str)
        """
        if filename is None:
            filename = f"linux_plus_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            export_path = os.path.abspath(filename)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2)
            return True, export_path
            
        except IOError as e:
            print(f"{COLOR_ERROR} Error exporting history: {e} {COLOR_RESET}")
            return False, ""
            
        except Exception as e:
            print(f"{COLOR_ERROR} An unexpected error occurred during history export: {e} {COLOR_RESET}")
            return False, ""

    @staticmethod
    def export_questions_markdown(questions_data, filename=None):
        """
        Export questions and answers to Markdown file.
        
        Args:
            questions_data (list): List of question tuples
            filename (str): Output filename, auto-generated if None
            
        Returns:
            tuple: (success: bool, filepath: str)
        """
        if filename is None:
            filename = f"Linux_plus_QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        try:
            export_path = os.path.abspath(filename)
            
            with open(filename, 'w', encoding='utf-8') as f:
                # Write Questions Section
                f.write("# Questions\n\n")
                for i, q_data in enumerate(questions_data):
                    if len(q_data) < 5:
                        continue
                    question_text, options, _, category, _ = q_data
                    f.write(f"**Q{i+1}.** ({category})\n")
                    f.write(f"{question_text}\n")
                    for j, option in enumerate(options):
                        f.write(f"   {chr(ord('A') + j)}. {option}\n")
                    f.write("\n")

                f.write("---\n\n")

                # Write Answers Section
                f.write("# Answers\n\n")
                for i, q_data in enumerate(questions_data):
                    if len(q_data) < 5:
                        continue
                    _, options, correct_answer_index, _, explanation = q_data
                    
                    if 0 <= correct_answer_index < len(options):
                        correct_option_letter = chr(ord('A') + correct_answer_index)
                        correct_option_text = options[correct_answer_index]
                        
                        f.write(f"**A{i+1}.** {correct_option_letter}. {correct_option_text}\n")
                        if explanation:
                            explanation_lines = explanation.split('\n')
                            f.write("   *Explanation:*")
                            first_line = True
                            for line in explanation_lines:
                                if not first_line:
                                    f.write("   ")
                                f.write(f" {line.strip()}\n")
                                first_line = False
                        f.write("\n\n")
                    else:
                        f.write(f"**A{i+1}.** Error: Invalid correct answer index.\n\n")
            
            return True, export_path
            
        except IOError as e:
            print(f"{COLOR_ERROR} Error exporting Q&A: {e} {COLOR_RESET}")
            return False, ""
            
        except Exception as e:
            print(f"{COLOR_ERROR} An unexpected error occurred during Q&A export: {e} {COLOR_RESET}")
            return False, ""

    @staticmethod
    def export_questions_json(questions_data, filename=None):
        """
        Export questions and answers to JSON file.
        
        Args:
            questions_data (list): List of question tuples
            filename (str): Output filename, auto-generated if None
            
        Returns:
            tuple: (success: bool, filepath: str)
        """
        if filename is None:
            filename = f"Linux_plus_QA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            export_path = os.path.abspath(filename)
            
            # Prepare questions data for JSON export
            questions_list = []
            for i, q_data in enumerate(questions_data):
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
                questions_list.append(question_obj)

            # Create the final JSON structure
            export_data = {
                "metadata": {
                    "title": "Linux+ Study Questions",
                    "export_date": datetime.now().isoformat(),
                    "total_questions": len(questions_list),
                    "categories": sorted(list(set(q["category"] for q in questions_list)))
                },
                "questions": questions_list
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True, export_path
            
        except IOError as e:
            print(f"{COLOR_ERROR} Error exporting Q&A: {e} {COLOR_RESET}")
            return False, ""
            
        except Exception as e:
            print(f"{COLOR_ERROR} An unexpected error occurred during Q&A export: {e} {COLOR_RESET}")
            return False, ""

    @staticmethod
    def file_exists(filepath):
        """Check if a file exists."""
        return os.path.isfile(filepath)

    @staticmethod
    def create_backup(filepath, backup_suffix=".backup"):
        """
        Create a backup copy of a file.
        
        Args:
            filepath (str): Path to file to backup
            backup_suffix (str): Suffix to add to backup filename
            
        Returns:
            bool: True if backup created successfully
        """
        try:
            if os.path.isfile(filepath):
                backup_path = filepath + backup_suffix
                import shutil
                shutil.copy2(filepath, backup_path)
                return True
            return False
        except Exception as e:
            print(f"{COLOR_ERROR} Error creating backup: {e} {COLOR_RESET}")
            return False