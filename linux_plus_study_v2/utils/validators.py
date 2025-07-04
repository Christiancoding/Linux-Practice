#!/usr/bin/env python3
"""
Validation utilities for the Linux+ Study Game.
Handles input validation, data validation, and user choice validation.
"""

import os
from typing import Union, Tuple, Optional, List, Dict, Any, Type, Literal


class InputValidator:
    """Handles validation of user inputs and data structures."""
    
    @staticmethod
    def validate_quiz_answer(user_input: str, num_options: int, allow_skip: bool = True, allow_quit: bool = True) -> Tuple[bool, Optional[Union[int, str]], str]:
        """
        Validate user answer input for quiz questions.
        
        Args:
            user_input (str): Raw user input
            num_options (int): Number of available options
            allow_skip (bool): Whether 's' (skip) is allowed
            allow_quit (bool): Whether 'q' (quit) is allowed
            
        Returns:
            tuple: (is_valid: bool, processed_value: int|str, error_message: str)
        """
        if not user_input:
            return False, None, "Input must be a string"
        
        cleaned_input = user_input.lower().strip()
        
        # Check for special commands
        if allow_quit and cleaned_input == 'q':
            return True, 'q', ""
        
        if allow_skip and cleaned_input == 's':
            return True, 's', ""
        
        # Validate numeric input
        try:
            choice = int(cleaned_input)
            if 1 <= choice <= num_options:
                return True, choice - 1, ""  # Return 0-based index
            else:
                return False, None, f"Please enter a number between 1 and {num_options}"
        except ValueError:
            valid_options = ["a number"]
            if allow_skip:
                valid_options.append("'s' to skip")
            if allow_quit:
                valid_options.append("'q' to quit")
            
            return False, None, f"Invalid input. Please enter {' or '.join(valid_options)}"

    @staticmethod
    def validate_category_choice(user_input: str, num_categories: int, allow_back: bool = True) -> Tuple[bool, Optional[Union[int, str]], str]:
        """
        Validate category selection input.
        
        Args:
            user_input (str): Raw user input
            num_categories (int): Number of available categories (excluding "All Categories")
            allow_back (bool): Whether 'b' (back) is allowed
            
        Returns:
            tuple: (is_valid: bool, processed_value: int|str, error_message: str)
        """
        if not user_input:
            return False, None, "Input must be a string"
        
        cleaned_input = user_input.lower().strip()
        
        # Check for back command
        if allow_back and cleaned_input == 'b':
            return True, 'b', ""
        
        # Validate numeric input (0 = All Categories, 1+ = specific categories)
        try:
            choice = int(cleaned_input)
            if 0 <= choice <= num_categories:
                return True, choice, ""
            else:
                return False, None, f"Please enter a number between 0 and {num_categories}"
        except ValueError:
            valid_options = ["a number"]
            if allow_back:
                valid_options.append("'b' to go back")
            
            return False, None, f"Invalid input. Please enter {' or '.join(valid_options)}"

    @staticmethod
    def validate_yes_no(user_input: str, default: Optional[str] = None) -> Tuple[bool, Optional[bool], str]:
        """
        Validate yes/no input.
        
        Args:
            user_input (str): Raw user input
            default (str): Default value if input is empty ('yes' or 'no')
            
        Returns:
            tuple: (is_valid: bool, processed_value: bool, error_message: str)
        """
        if not user_input:
            return False, None, "Input must be a string"
        
        cleaned_input = user_input.lower().strip()
        
        # Handle empty input with default
        if not cleaned_input and default:
            return True, default.lower() == 'yes', ""
        
        # Check valid yes/no responses
        yes_responses = ['yes', 'y', 'true', '1']
        no_responses = ['no', 'n', 'false', '0']
        
        if cleaned_input in yes_responses:
            return True, True, ""
        elif cleaned_input in no_responses:
            return True, False, ""
        else:
            return False, None, "Please enter 'yes' or 'no'"

    @staticmethod
    def validate_menu_choice(user_input: str, valid_choices: List[str]) -> Tuple[bool, Optional[str], str]:
        """
        Validate menu choice against a list of valid options.
        
        Args:
            user_input (str): Raw user input
            valid_choices (list): List of valid choice strings
            
        Returns:
            tuple: (is_valid: bool, processed_value: str, error_message: str)
        """
        if not user_input:
            return False, None, "Input must be a string"
        
        cleaned_input = user_input.strip()
        
        if cleaned_input in valid_choices:
            return True, cleaned_input, ""
        else:
            return False, None, f"Please enter one of: {', '.join(valid_choices)}"

    @staticmethod
    def validate_filename(filename: str, required_extension: Optional[str] = None) -> Tuple[bool, Optional[str], str]:
        """
        Validate filename for export operations.
        
        Args:
            filename (str): Filename to validate
            required_extension (str): Required file extension (e.g., '.json')
            
        Returns:
            tuple: (is_valid: bool, processed_filename: str, error_message: str)
        """
        if not filename:
            return False, None, "Filename must be a string"
        
        cleaned_filename = filename.strip()
        
        if not cleaned_filename:
            return False, None, "Filename cannot be empty"
        
        # Check for invalid characters (basic check)
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in cleaned_filename for char in invalid_chars):
            return False, None, f"Filename contains invalid characters: {invalid_chars}"
        
        # Add required extension if specified and missing
        if required_extension:
            if not cleaned_filename.lower().endswith(required_extension.lower()):
                cleaned_filename += required_extension
        
        return True, cleaned_filename, ""

    @staticmethod
    def validate_number_range(user_input: str, min_val: Union[int, float], max_val: Union[int, float], 
                              input_type: Type = int) -> Tuple[bool, Optional[Union[int, float]], str]:
        """
        Validate numeric input within a specified range.
        
        Args:
            user_input (str): Raw user input
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            input_type: Type to convert to (int or float)
            
        Returns:
            tuple: (is_valid: bool, processed_value: int|float, error_message: str)
        """
        if not user_input:
            return False, None, "Input must be a string"
        
        cleaned_input = user_input.strip()
        
        try:
            value = input_type(cleaned_input)
            if min_val <= value <= max_val:
                return True, value, ""
            else:
                return False, None, f"Please enter a {input_type.__name__} between {min_val} and {max_val}"
        except ValueError:
            return False, None, f"Please enter a valid {input_type.__name__}"


class DataValidator:
    """Handles validation of data structures and game state."""
    
    @staticmethod
    def validate_question_data(question_data: Union[List, Tuple]) -> Tuple[bool, str]:
        """
        Validate question data structure.
        
        Args:
            question_data: Question data to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if not isinstance(question_data, (list, tuple)):
            return False, "Question data must be a list or tuple"
        
        if len(question_data) < 5:
            return False, "Question data must have at least 5 elements"
        
        question_text, options, correct_idx, category, explanation = question_data[:5]
        
        # Validate question text
        if not isinstance(question_text, str) or not question_text.strip():
            return False, "Question text must be a non-empty string"
        
        # Validate options
        if not isinstance(options, list) or len(options) < 2:
            return False, "Options must be a list with at least 2 items"
        
        if not all(isinstance(opt, str) and opt.strip() for opt in options):
            return False, "All options must be non-empty strings"
        
        # Validate correct answer index
        if not isinstance(correct_idx, int) or not (0 <= correct_idx < len(options)):
            return False, f"Correct answer index must be an integer between 0 and {len(options)-1}"
        
        # Validate category
        if not isinstance(category, str) or not category.strip():
            return False, "Category must be a non-empty string"
        
        # Validate explanation (can be empty)
        if explanation is not None and not isinstance(explanation, str):
            return False, "Explanation must be a string or None"
        
        return True, ""

    @staticmethod
    def validate_history_data(history_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate history data structure.
        
        Args:
            history_data: History data to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if not isinstance(history_data, dict):
            return False, "History data must be a dictionary"
        
        required_keys = ["sessions", "questions", "categories", "total_correct", "total_attempts"]
        for key in required_keys:
            if key not in history_data:
                return False, f"Missing required key: {key}"
        
        # Validate data types
        if not isinstance(history_data["sessions"], list):
            return False, "Sessions must be a list"
        
        if not isinstance(history_data["questions"], dict):
            return False, "Questions must be a dictionary"
        
        if not isinstance(history_data["categories"], dict):
            return False, "Categories must be a dictionary"
        
        if not isinstance(history_data["total_correct"], int) or history_data["total_correct"] < 0:
            return False, "Total correct must be a non-negative integer"
        
        if not isinstance(history_data["total_attempts"], int) or history_data["total_attempts"] < 0:
            return False, "Total attempts must be a non-negative integer"
        
        return True, ""

    @staticmethod
    def validate_achievements_data(achievements_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate achievements data structure.
        
        Args:
            achievements_data: Achievements data to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if not isinstance(achievements_data, dict):
            return False, "Achievements data must be a dictionary"
        
        required_keys = ["badges", "points_earned", "questions_answered"]
        for key in required_keys:
            if key not in achievements_data:
                return False, f"Missing required key: {key}"
        
        # Validate data types
        if not isinstance(achievements_data["badges"], list):
            return False, "Badges must be a list"
        
        if not isinstance(achievements_data["points_earned"], int) or achievements_data["points_earned"] < 0:
            return False, "Points earned must be a non-negative integer"
        
        if not isinstance(achievements_data["questions_answered"], int) or achievements_data["questions_answered"] < 0:
            return False, "Questions answered must be a non-negative integer"
        
        return True, ""

    @staticmethod
    def validate_quiz_mode(mode: str) -> Tuple[bool, str]:
        """
        Validate quiz mode.
        
        Args:
            mode (str): Quiz mode to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        from utils.config import QUIZ_MODE_STANDARD, QUIZ_MODE_VERIFY
        
        valid_modes = [
            QUIZ_MODE_STANDARD, 
            QUIZ_MODE_VERIFY, 
            "quick_fire", 
            "mini_quiz", 
            "daily_challenge", 
            "pop_quiz"
        ]
        
        if mode in valid_modes:
            return True, ""
        else:
            return False, f"Invalid quiz mode. Must be one of: {valid_modes}"

    @staticmethod
    def sanitize_input(user_input: str, max_length: int = 1000) -> str:
        """
        Sanitize user input to prevent issues.
        
        Args:
            user_input (str): Raw user input
            max_length (int): Maximum allowed length
            
        Returns:
            str: Sanitized input
        """
        if not isinstance(user_input, str):
            return ""
        
        # Truncate if too long
        sanitized = user_input[:max_length]
        
        # Remove control characters except common whitespace
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\t\n\r')
        
        return sanitized

    @staticmethod
    def validate_file_path(file_path: str, must_exist: bool = False, must_be_writable: bool = False) -> Tuple[bool, str]:
        """
        Validate file path.
        
        Args:
            file_path (str): File path to validate
            must_exist (bool): Whether file must already exist
            must_be_writable (bool): Whether location must be writable
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if not isinstance(file_path, str) or not file_path.strip():
            return False, "File path cannot be empty"
        
        if must_exist and not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}"
        
        if must_be_writable:
            directory = os.path.dirname(file_path) or '.'
            if not os.access(directory, os.W_OK):
                return False, f"Directory is not writable: {directory}"
        
        return True, ""