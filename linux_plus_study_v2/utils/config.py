#!/usr/bin/env python3
"""
Configuration constants for the Linux+ Study Game.
"""

import sys
import os
from pathlib import Path

# --- File Constants ---
HISTORY_FILE = "linux_plus_history.json"
ACHIEVEMENTS_FILE = "linux_plus_achievements.json"

# --- Quiz Mode Constants ---
QUIZ_MODE_STANDARD = "standard"
QUIZ_MODE_VERIFY = "verify"

# --- Gamification Constants ---
POINTS_PER_CORRECT = 10
POINTS_PER_INCORRECT = -2
STREAK_BONUS_THRESHOLD = 3
STREAK_BONUS_MULTIPLIER = 1.5

# --- Quick Fire Mode Constants ---
QUICK_FIRE_QUESTIONS = 5
QUICK_FIRE_TIME_LIMIT = 180  # 3 minutes in seconds

# --- Mini Quiz Constants ---
MINI_QUIZ_QUESTIONS = 3
MINI_QUIZ_TIME_LIMIT = 30  # 30 seconds
# Project structure paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
UTILS_DIR = PROJECT_ROOT / "utils"

# Data file paths
QUESTIONS_FILE = DATA_DIR / "questions.json"
ACHIEVEMENTS_FILE = PROJECT_ROOT / "linux_plus_achievements.json"
HISTORY_FILE = PROJECT_ROOT / "linux_plus_history.json"
WEB_SETTINGS_FILE = PROJECT_ROOT / "web_settings.json"

# Application modes (GUI mode removed)
SUPPORTED_MODES = ["cli", "web"]
DEFAULT_MODE = "cli"


# --- Colorama Setup (CLI Colors) ---
try:
    import colorama
    colorama.init(autoreset=True)
    
    # Define a richer color palette using colorama styles
    C = {
        "reset": colorama.Style.RESET_ALL,
        "bold": colorama.Style.BRIGHT,
        "dim": colorama.Style.DIM,
        # Foreground Colors
        "fg_black": colorama.Fore.BLACK,
        "fg_red": colorama.Fore.RED,
        "fg_green": colorama.Fore.GREEN,
        "fg_yellow": colorama.Fore.YELLOW,
        "fg_blue": colorama.Fore.BLUE,
        "fg_magenta": colorama.Fore.MAGENTA,
        "fg_cyan": colorama.Fore.CYAN,
        "fg_white": colorama.Fore.WHITE,
        "fg_lightblack_ex": colorama.Fore.LIGHTBLACK_EX,
        # Bright Foreground Colors
        "fg_bright_red": colorama.Fore.LIGHTRED_EX,
        "fg_bright_green": colorama.Fore.LIGHTGREEN_EX,
        "fg_bright_yellow": colorama.Fore.LIGHTYELLOW_EX,
        "fg_bright_blue": colorama.Fore.LIGHTBLUE_EX,
        "fg_bright_magenta": colorama.Fore.LIGHTMAGENTA_EX,
        "fg_bright_cyan": colorama.Fore.LIGHTCYAN_EX,
        "fg_bright_white": colorama.Fore.LIGHTWHITE_EX,
        # Background Colors
        "bg_red": colorama.Back.RED,
        "bg_green": colorama.Back.GREEN,
        "bg_yellow": colorama.Back.YELLOW,
        "bg_blue": colorama.Back.BLUE,
        "bg_magenta": colorama.Back.MAGENTA,
        "bg_cyan": colorama.Back.CYAN,
        "bg_white": colorama.Back.WHITE,
    }
    
    # Define semantic colors using the palette
    COLOR_QUESTION = C["fg_bright_cyan"] + C["bold"]
    COLOR_OPTIONS = C["fg_white"]
    COLOR_OPTION_NUM = C["fg_yellow"] + C["bold"]
    COLOR_CATEGORY = C["fg_bright_yellow"] + C["bold"]
    COLOR_CORRECT = C["fg_bright_green"] + C["bold"]
    COLOR_INCORRECT = C["fg_bright_red"] + C["bold"]
    COLOR_EXPLANATION = C["fg_lightblack_ex"]
    COLOR_PROMPT = C["fg_bright_magenta"] + C["bold"]
    COLOR_HEADER = C["fg_bright_blue"] + C["bold"]
    COLOR_SUBHEADER = C["fg_blue"] + C["bold"]
    COLOR_STATS_LABEL = C["fg_white"]
    COLOR_STATS_VALUE = C["fg_bright_yellow"]
    COLOR_STATS_ACC_GOOD = C["fg_bright_green"]
    COLOR_STATS_ACC_AVG = C["fg_yellow"]
    COLOR_STATS_ACC_BAD = C["fg_bright_red"]
    COLOR_BORDER = C["fg_blue"]
    COLOR_INPUT = C["fg_bright_white"]
    COLOR_ERROR = C["fg_white"] + C["bg_red"] + C["bold"]
    COLOR_WARNING = C["fg_bright_yellow"] + C["bold"]
    COLOR_INFO = C["fg_bright_cyan"]
    COLOR_WELCOME_BORDER = C["fg_bright_yellow"] + C["bold"]
    COLOR_WELCOME_TEXT = C["fg_white"]
    COLOR_WELCOME_TITLE = C["fg_bright_yellow"] + C["bold"]
    COLOR_RESET = C["reset"]
    
except ImportError:
    print("Warning: Colorama not found. Colored output will be disabled in CLI.")
    # Define empty strings if colorama is not available
    C = {k: "" for k in ["reset", "bold", "dim", "fg_black", "fg_red", "fg_green", 
         "fg_yellow", "fg_blue", "fg_magenta", "fg_cyan", "fg_white", "fg_lightblack_ex", 
         "fg_bright_red", "fg_bright_green", "fg_bright_yellow", "fg_bright_blue", 
         "fg_bright_magenta", "fg_bright_cyan", "fg_bright_white", "bg_red", "bg_green", 
         "bg_yellow", "bg_blue", "bg_magenta", "bg_cyan", "bg_white"]}
    
    COLOR_QUESTION, COLOR_OPTIONS, COLOR_OPTION_NUM, COLOR_CATEGORY = "", "", "", ""
    COLOR_CORRECT, COLOR_INCORRECT, COLOR_EXPLANATION, COLOR_PROMPT = "", "", "", ""
    COLOR_HEADER, COLOR_SUBHEADER, COLOR_STATS_LABEL, COLOR_STATS_VALUE = "", "", "", ""
    COLOR_STATS_ACC_GOOD, COLOR_STATS_ACC_AVG, COLOR_STATS_ACC_BAD = "", "", ""
    COLOR_BORDER, COLOR_INPUT, COLOR_ERROR, COLOR_WARNING, COLOR_INFO = "", "", "", "", ""
    COLOR_WELCOME_BORDER, COLOR_WELCOME_TEXT, COLOR_WELCOME_TITLE = "", "", ""
    COLOR_RESET = ""

# --- Sample Questions Data ---
SAMPLE_QUESTIONS = [
    (
        "Which command installs the GRUB2 bootloader to a specified device?",
        ["grub2-mkconfig", "grub2-install", "update-grub", "dracut"],
        1, "Commands (System Management)",
        "`grub2-install` installs the GRUB2 bootloader files to the appropriate location and typically installs the boot code to the MBR or EFI partition. Example: `grub2-install /dev/sda` (for BIOS systems) or `grub2-install --target=x86_64-efi --efi-directory=/boot/efi` (for UEFI systems)."
    )
]
# CLI Configuration Settings
CLI_SETTINGS = {
    "welcome_message": "Welcome to Linux Plus Study Tool",
    "prompt_symbol": ">>> ",
    "clear_screen": True,
    "show_progress_bar": True,
    "colored_output": True,
    "max_menu_options": 10,
    "input_timeout": 300,  # 5 minutes
}

# Web Configuration Settings
WEB_SETTINGS = {
    "default_host": "127.0.0.1",
    "default_port": 5000,
    "debug_mode": False,
    "threaded": True,
    "template_auto_reload": True,
    "session_timeout": 3600,  # 1 hour
    "max_content_length": 16 * 1024 * 1024,  # 16MB
}

# Quiz Configuration
QUIZ_SETTINGS = {
    "default_question_count": 10,
    "max_question_count": 50,
    "min_question_count": 1,
    "shuffle_questions": True,
    "shuffle_options": True,
    "show_immediate_feedback": True,
    "allow_review": True,
}

# Achievement System Configuration
ACHIEVEMENT_SETTINGS = {
    "points_per_correct": 10,
    "bonus_streak_multiplier": 1.5,
    "streak_threshold": 5,
    "daily_challenge_bonus": 50,
    "perfect_quiz_bonus": 25,
}

# Scoring and Statistics
SCORING_SETTINGS = {
    "passing_percentage": 70,
    "excellent_percentage": 90,
    "streak_bonus_threshold": 10,
    "leaderboard_max_entries": 100,
}

# Question Categories (Linux Plus specific)
QUESTION_CATEGORIES = [
    "Hardware and System Configuration",
    "Systems Operation and Maintenance", 
    "Security",
    "Linux Troubleshooting and Diagnostics",
    "Automation and Scripting",
]

# Difficulty Levels
DIFFICULTY_LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"]

# File validation settings
FILE_VALIDATION = {
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "allowed_extensions": [".json", ".txt", ".csv"],
    "encoding": "utf-8",
}

# Logging Configuration
LOGGING_SETTINGS = {
    "log_level": "INFO",
    "log_file": PROJECT_ROOT / "app.log",
    "max_log_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

# Error Messages
ERROR_MESSAGES = {
    "file_not_found": "Required file not found: {filename}",
    "invalid_mode": "Invalid mode. Supported modes: {modes}",
    "no_questions": "No questions available for the selected category",
    "invalid_answer": "Invalid answer format. Please try again.",
    "network_error": "Network connection error. Please check your connection.",
    "permission_error": "Permission denied. Check file permissions.",
}

# Success Messages  
SUCCESS_MESSAGES = {
    "quiz_completed": "Quiz completed successfully!",
    "achievement_unlocked": "Achievement unlocked: {achievement}",
    "stats_cleared": "Statistics cleared successfully",
    "file_saved": "File saved successfully: {filename}",
}

# Development and Debug Settings
DEBUG_SETTINGS = {
    "verbose_logging": False,
    "show_sql_queries": False,
    "profile_performance": False,
    "mock_data": False,
}

# API Configuration (for potential future web API)
API_SETTINGS = {
    "version": "v1",
    "rate_limit": 100,  # requests per minute
    "cors_enabled": False,
    "authentication_required": False,
}

# User Interface Constants
UI_CONSTANTS = {
    "page_title": "Linux Plus Study Tool",
    "app_version": "2.0.0",
    "copyright": "© 2024 Linux Plus Study Tool",
    "support_email": "support@linuxplus.example.com",
}

# Performance Settings
PERFORMANCE_SETTINGS = {
    "cache_questions": True,
    "cache_timeout": 3600,  # 1 hour
    "lazy_loading": True,
    "pagination_size": 20,
}

def get_config_value(section, key, default=None):
    """
    Retrieve a configuration value from the specified section.
    
    Args:
        section (str): Configuration section name
        key (str): Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    config_sections = {
        "cli": CLI_SETTINGS,
        "web": WEB_SETTINGS,
        "quiz": QUIZ_SETTINGS,
        "achievements": ACHIEVEMENT_SETTINGS,
        "scoring": SCORING_SETTINGS,
        "logging": LOGGING_SETTINGS,
        "debug": DEBUG_SETTINGS,
        "api": API_SETTINGS,
        "ui": UI_CONSTANTS,
        "performance": PERFORMANCE_SETTINGS,
    }
    
    section_config = config_sections.get(section, {})
    return section_config.get(key, default)

def validate_mode(mode):
    """
    Validate if the provided mode is supported.
    
    Args:
        mode (str): Application mode to validate
        
    Returns:
        bool: True if mode is supported, False otherwise
    """
    return mode in SUPPORTED_MODES

def get_file_path(file_type):
    """
    Get the full file path for a specific file type.
    
    Args:
        file_type (str): Type of file (questions, achievements, history, etc.)
        
    Returns:
        Path: Full path to the specified file
    """
    file_paths = {
        "questions": QUESTIONS_FILE,
        "achievements": ACHIEVEMENTS_FILE,
        "history": HISTORY_FILE,
        "web_settings": WEB_SETTINGS_FILE,
    }
    
    return file_paths.get(file_type)

def ensure_directories():
    """
    Ensure all required directories exist.
    Create them if they don't exist.
    """
    directories = [
        DATA_DIR,
        TEMPLATES_DIR,
        STATIC_DIR,
        STATIC_DIR / "css",
        STATIC_DIR / "js",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Environment-specific overrides
if os.getenv("FLASK_ENV") == "development":
    WEB_SETTINGS["debug_mode"] = True
    DEBUG_SETTINGS["verbose_logging"] = True

if os.getenv("PRODUCTION") == "true":
    WEB_SETTINGS["debug_mode"] = False
    DEBUG_SETTINGS["verbose_logging"] = False
    LOGGING_SETTINGS["log_level"] = "WARNING"
# Database Connection Pooling Settings
DATABASE_POOL_SETTINGS = {
    "pool_size": 10,           # Number of connections to maintain in pool
    "max_overflow": 20,        # Additional connections beyond pool_size
    "pool_pre_ping": True,     # Validate connections before use
    "pool_recycle": 3600,      # Recycle connections after 1 hour
    "pool_timeout": 30,        # Timeout waiting for connection from pool
    "echo": False,             # Log all SQL statements (set to True for debugging)
}

# Database Configuration
DATABASE_SETTINGS = {
    "sqlite": {
        "url": "sqlite:///data/linux_plus_study.db",
        "pool_enabled": False,  # SQLite doesn't benefit from pooling
    },
    "postgresql": {
        "url": "postgresql://username:password@localhost:5432/linux_plus_study",
        "pool_enabled": True,
    },
    "mysql": {
        "url": "mysql+pymysql://username:password@localhost:3306/linux_plus_study",
        "pool_enabled": True,
    }
}
def get_database_config(db_type="sqlite"):
    """
    Get database configuration with connection pooling settings.
    
    Args:
        db_type (str): Database type (sqlite, postgresql, mysql)
        
    Returns:
        dict: Combined database and pool configuration
    """
    db_config = DATABASE_SETTINGS.get(db_type, DATABASE_SETTINGS["sqlite"])
    
    if db_config.get("pool_enabled", False):
        return {**db_config, **DATABASE_POOL_SETTINGS}
    else:
        return db_config