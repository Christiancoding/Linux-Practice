#!/usr/bin/env python3
"""
Configuration constants for the Linux+ Study Game.
"""
from typing import Optional, List, Dict, Any, Union
import sys
import os
from pathlib import Path

# Ensure minimum Python version compatibility
if sys.version_info < (3, 8):
    print("Linux+ Practice Environment Manager requires Python 3.8+")
    sys.exit(1)

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

# Application modes
SUPPORTED_MODES = ["cli", "web"]
DEFAULT_MODE = "cli"

# --- Quiz Mode Constants ---
QUIZ_MODE_STANDARD = "standard"
QUIZ_MODE_VERIFY = "verify"

# --- Quick Fire Mode Constants ---
QUICK_FIRE_QUESTIONS = 5
QUICK_FIRE_TIME_LIMIT = 180  # 3 minutes in seconds

# --- Mini Quiz Constants ---
MINI_QUIZ_QUESTIONS = 3
MINI_QUIZ_TIME_LIMIT = 30  # 30 seconds

# --- Colorama Setup (CLI Colors) ---
COLOR_QUESTION = ""
COLOR_OPTIONS = ""
COLOR_OPTION_NUM = ""
COLOR_CATEGORY = ""
COLOR_CORRECT = ""
COLOR_INCORRECT = ""
COLOR_EXPLANATION = ""
COLOR_PROMPT = ""
COLOR_HEADER = ""
COLOR_SUBHEADER = ""
COLOR_STATS_LABEL = ""
COLOR_STATS_VALUE = ""
COLOR_STATS_ACC_GOOD = ""
COLOR_STATS_ACC_AVG = ""
COLOR_STATS_ACC_BAD = ""
COLOR_BORDER = ""
COLOR_INPUT = ""
COLOR_ERROR = ""
COLOR_WARNING = ""
COLOR_INFO = ""
COLOR_WELCOME_BORDER = ""
COLOR_WELCOME_TEXT = ""
COLOR_WELCOME_TITLE = ""
COLOR_RESET = ""

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
    # Assign semantic colors using the palette
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

# CLI Configuration Settings
CLI_SETTINGS: Dict[str, Any] = {
    "welcome_message": "Welcome to Linux Plus Study Tool",
    "prompt_symbol": ">>> ",
    "clear_screen": True,
    "show_progress_bar": True,
    "colored_output": True,
    "max_menu_options": 10,
    "input_timeout": 300,  # 5 minutes
}

# Web Configuration Settings
WEB_SETTINGS: Dict[str, Any] = {
    "default_host": "127.0.0.1",
    "default_port": 5000,
    "debug_mode": False,
    "threaded": True,
    "template_auto_reload": True,
    "session_timeout": 3600,  # 1 hour
    "max_content_length": 16 * 1024 * 1024,  # 16MB
}

# Quiz Configuration
QUIZ_SETTINGS: Dict[str, Any] = {
    "default_question_count": 10,
    "max_question_count": 50,
    "min_question_count": 1,
    "shuffle_questions": True,
    "shuffle_options": True,
    "show_immediate_feedback": True,
    "allow_review": True,
}

# Achievement System Configuration (consolidated)
ACHIEVEMENT_SETTINGS: Dict[str, Any] = {
    "points_per_correct": 10,
    "points_per_incorrect": -2,
    "bonus_streak_multiplier": 1.5,
    "streak_threshold": 5,
    "streak_bonus_threshold": 3,
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
    "Commands (System Management)",
]

# Difficulty Levels
DIFFICULTY_LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"]

# File validation settings
FILE_VALIDATION: Dict[str, Any] = {
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "allowed_extensions": [".json", ".txt", ".csv"],
    "encoding": "utf-8",
}

# Logging Configuration
LOGGING_SETTINGS: Dict[str, Any] = {
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
API_SETTINGS: Dict[str, Any] = {
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
PERFORMANCE_SETTINGS: Dict[str, Any] = {
    "cache_questions": True,
    "cache_timeout": 3600,  # 1 hour
    "lazy_loading": True,
    "pagination_size": 20,
}

# Database Connection Pooling Settings
DATABASE_POOL_SETTINGS: Dict[str, Any] = {
    "pool_size": 10,           # Number of connections to maintain in pool
    "max_overflow": 20,        # Additional connections beyond pool_size
    "pool_pre_ping": True,     # Validate connections before use
    "pool_recycle": 3600,      # Recycle connections after 1 hour
    "pool_timeout": 30,        # Timeout waiting for connection from pool
    "echo": False,             # Log all SQL statements (set to True for debugging)
}

# Database Configuration
DATABASE_SETTINGS: Dict[str, Any] = {
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

# --- Sample Questions Data ---
SAMPLE_QUESTIONS = [
    (
        "Which command installs the GRUB2 bootloader to a specified device?",
        ["grub2-mkconfig", "grub2-install", "update-grub", "dracut"],
        1, "Commands (System Management)",
        "`grub2-install` installs the GRUB2 bootloader files to the appropriate location and typically installs the boot code to the MBR or EFI partition. Example: `grub2-install /dev/sda` (for BIOS systems) or `grub2-install --target=x86_64-efi --efi-directory=/boot/efi` (for UEFI systems)."
    )
]

# Environment-specific overrides
if os.getenv("FLASK_ENV") == "development":
    WEB_SETTINGS["debug_mode"] = True
    DEBUG_SETTINGS["verbose_logging"] = True

if os.getenv("PRODUCTION") == "true":
    WEB_SETTINGS["debug_mode"] = False
    DEBUG_SETTINGS["verbose_logging"] = False
    LOGGING_SETTINGS["log_level"] = "WARNING"

# Import libvirt for error code constants (with graceful fallback)
try:
    import libvirt  # type: ignore
except ImportError:
    print("Error: Missing required library 'libvirt-python'.\n"
          "Please install it (e.g., 'pip install libvirt-python' or via system package manager) and try again.", 
          file=sys.stderr)
    sys.exit(1)

# Configuration Classes for VM Management
class VMConfiguration:
    """Virtual Machine management configuration settings."""
    
    # Default VM Settings
    DEFAULT_VM_NAME: str = "ubuntu24.04-2"
    DEFAULT_SNAPSHOT_NAME: str = "practice_external_snapshot"
    
    # VM Operation Timeouts (in seconds)
    READINESS_TIMEOUT_SECONDS: int = 120
    READINESS_POLL_INTERVAL_SECONDS: int = 5
    SHUTDOWN_TIMEOUT_SECONDS: int = 120
    # Libvirt Connection Configuration
    LIBVIRT_URI: str = 'qemu:///system'

class SSHConfiguration:
    """SSH connection and authentication configuration settings."""
    
    # Default SSH Connection Parameters
    DEFAULT_SSH_USER: str = "roo"  # Update this for your environment
    DEFAULT_SSH_KEY_PATH: Path = Path("~/.ssh/id_ed25519").expanduser()
    
    # SSH Operation Timeouts (in seconds)
    CONNECT_TIMEOUT_SECONDS: int = 10
    COMMAND_TIMEOUT_SECONDS: int = 30
    
    # SSH Security Settings
    KEY_PERMISSIONS_MASK: int = 0o077  # Only owner should have access
    
    @classmethod
    def validate_ssh_key_path(cls, key_path: Path) -> bool:
        """
        Validate SSH key file permissions and existence.
        
        Args:
            key_path: Path to SSH private key file
            
        Returns:
            bool: True if key is valid and secure, False otherwise
        """
        if not key_path.exists():
            return False
        
        # Check file permissions for security
        key_perms = key_path.stat().st_mode & 0o777
        if key_perms & cls.KEY_PERMISSIONS_MASK:
            return False
        
        return True

class ChallengeConfiguration:
    """Challenge system configuration and default settings."""
    
    # Default Challenge Settings
    DEFAULT_CHALLENGES_DIR: Path = Path(__file__).parent.parent / "challenges"
    DEFAULT_CHALLENGE_SCORE: int = 100
    
    # Challenge Validation Settings
    REQUIRED_CHALLENGE_KEYS = ['id', 'name', 'description', 'validation']
    ALLOWED_CHALLENGE_KEYS = [
        'id', 'name', 'description', 'category', 'difficulty', 'score',
        'concepts', 'setup', 'user_action_simulation', 'validation', 'hints', 'flag'
    ]
    
    # Challenge File Processing
    CHALLENGE_FILE_EXTENSIONS = ['.yaml', '.yml']
    
    @classmethod
    def get_challenge_files(cls, directory: Path) -> List[Path]:
        """
        Get all valid challenge files from a directory.
        
        Args:
            directory: Directory to scan for challenge files
            
        Returns:
            list: List of Path objects for valid challenge files
        """
        if not directory.exists() or not directory.is_dir():
            return []
        
        challenge_files: List[Path] = []
        for ext in cls.CHALLENGE_FILE_EXTENSIONS:
            challenge_files.extend(directory.glob(f"*{ext}"))
        
        return sorted(challenge_files)

class SystemConfiguration:
    """System-wide configuration and service management settings."""
    
    # Systemctl Status Exit Codes
    EXIT_CODE_ACTIVE: int = 0
    EXIT_CODE_INACTIVE: int = 3
    EXIT_CODE_FAILED_BASE: int = 1  # Any non-zero, non-inactive usually means failure
    EXIT_CODE_ENABLED: int = 0
    EXIT_CODE_DISABLED: int = 1
    
    # Network and Service Validation
    DEFAULT_PING_COUNT: int = 3
    DEFAULT_PORT_TIMEOUT: int = 5
    
    # File System Settings
    DEFAULT_FILE_MODE: str = "0644"
    DEFAULT_DIR_MODE: str = "0755"

class LibvirtErrorCodes:
    """Libvirt error code constants with safe fallback handling."""
    
    # Use getattr for safe access to libvirt error codes
    VIR_ERR_NO_DOMAIN = getattr(libvirt, 'VIR_ERR_NO_DOMAIN', -1)
    VIR_ERR_NO_DOMAIN_SNAPSHOT = getattr(libvirt, 'VIR_ERR_NO_DOMAIN_SNAPSHOT', -1)
    VIR_ERR_OPERATION_INVALID = getattr(libvirt, 'VIR_ERR_OPERATION_INVALID', -1)
    VIR_ERR_AGENT_UNRESPONSIVE = getattr(libvirt, 'VIR_ERR_AGENT_UNRESPONSIVE', -1)
    VIR_ERR_OPERATION_TIMEOUT = getattr(libvirt, 'VIR_ERR_OPERATION_TIMEOUT', -1)
    VIR_ERR_ARGUMENT_UNSUPPORTED = getattr(libvirt, 'VIR_ERR_ARGUMENT_UNSUPPORTED', -1)
    VIR_ERR_CONFIG_EXIST = getattr(libvirt, 'VIR_ERR_CONFIG_EXIST', -1)
    VIR_ERR_INVALID_DOMAIN = getattr(libvirt, 'VIR_ERR_INVALID_DOMAIN', -1)

class ApplicationConfiguration:
    """Main application configuration combining all subsystem settings."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize application configuration with optional config file override.
        
        Args:
            config_file: Optional path to configuration file for overrides
        """
        self.vm = VMConfiguration()
        self.ssh = SSHConfiguration()
        self.challenge = ChallengeConfiguration()
        self.system = SystemConfiguration()
        self.libvirt_errors = LibvirtErrorCodes()
        
        if config_file:
            self._load_config_file(config_file)
    
    def _load_config_file(self, config_file: Path) -> None:
        """
        Load configuration overrides from file.
        
        Args:
            config_file: Path to configuration file
            
        Note:
            This method can be extended to support YAML/JSON config files
            for environment-specific overrides.
        """
        # Future implementation for config file loading
        # Could support YAML/JSON configuration files for different environments
        pass
    
    def validate_configuration(self) -> bool:
        """
        Validate current configuration settings.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Validate SSH key if specified
        if hasattr(self.ssh, 'DEFAULT_SSH_KEY_PATH'):
            if not self.ssh.validate_ssh_key_path(self.ssh.DEFAULT_SSH_KEY_PATH):
                return False
        
        # Validate challenges directory
        if not self.challenge.DEFAULT_CHALLENGES_DIR.parent.exists():
            return False
        
        return True

# Utility Functions
def get_config_value(section: str, key: str, default: Any = None) -> Any:
    """
    Retrieve a configuration value from the specified section.
    
    Args:
        section (str): Configuration section name
        key (str): Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    config_sections: Dict[str, Dict[str, Any]] = {
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

def validate_mode(mode: str) -> bool:
    """
    Validate if the provided mode is supported.
    
    Args:
        mode (str): Application mode to validate
        
    Returns:
        bool: True if mode is supported, False otherwise
    """
    return mode in SUPPORTED_MODES

def get_file_path(file_type: str) -> Optional[Path]:
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

def ensure_directories() -> None:
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

def get_database_config(db_type: str = "sqlite") -> Dict[str, Any]:
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

# Backward compatibility - maintain the original Config class interface
class Config(VMConfiguration, SSHConfiguration, ChallengeConfiguration, SystemConfiguration):
    """
    Legacy configuration class for backward compatibility.
    
    This class combines all configuration sections into a single namespace
    to maintain compatibility with existing code that expects the original
    Config class from ww.py.
    """
    pass

# Global configuration instance for easy importing
config = ApplicationConfiguration()
