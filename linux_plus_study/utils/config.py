#!/usr/bin/env python3
"""
Configuration constants for the Linux+ Study Game.
"""

import sys
import tkinter.font as tkFont

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

# --- GUI Color Scheme ---
GUI_COLORS = {
    "bg": "#2B2B2B",          # Dark background
    "fg": "#D3D3D3",          # Light grey text
    "bg_widget": "#3C3F41",   # Slightly lighter background for widgets
    "fg_header": "#A9B7C6",   # Lighter text for headers
    "accent": "#FFC66D",      # Amber/Yellow accent
    "accent_dark": "#E8A44C",
    "button": "#4E5254",      # Darker button background
    "button_fg": "#D4D4D4",   # Light button text
    "button_hover": "#5F6365",
    "button_disabled_bg": "#3C3F41",
    "correct": "#6A8759",     # Muted green
    "incorrect": "#AC4142",   # Muted red
    "explanation_bg": "#313335",
    "border": "#555555",
    "disabled_fg": "#888888",
    "status_fg": "#BBBBBB",
    "category_fg": "#808080",
    "dim": "#888888",
    "welcome_title": "#FFC66D",
    "welcome_text": "#D3D3D3",
    "streak": "#6897BB",
}

# --- GUI Font Configuration ---
def get_gui_fonts():
    """Returns a dictionary of fonts for GUI components."""
    try:
        return {
            "base": tkFont.Font(family="Segoe UI", size=10),
            "bold": tkFont.Font(family="Segoe UI", size=10, weight="bold"),
            "header": tkFont.Font(family="Segoe UI", size=16, weight="bold"),
            "subheader": tkFont.Font(family="Segoe UI", size=12, weight="bold"),
            "italic": tkFont.Font(family="Segoe UI", size=9, slant="italic"),
            "question": tkFont.Font(family="Segoe UI", size=12),
            "option": tkFont.Font(family="Segoe UI", size=11),
            "feedback": tkFont.Font(family="Segoe UI", size=11, weight="bold"),
            "explanation": tkFont.Font(family="Consolas", size=10),
            "stats": tkFont.Font(family="Consolas", size=10),
            "button": tkFont.Font(family="Segoe UI", size=10, weight="bold"),
            "welcome_title": tkFont.Font(family="Segoe UI", size=14, weight="bold"),
            "welcome_text": tkFont.Font(family="Segoe UI", size=11),
        }
    except Exception as e:
        print(f"Warning: Could not create custom fonts: {e}")
        return {}

# --- Sample Questions Data ---
SAMPLE_QUESTIONS = [
    (
        "Which command installs the GRUB2 bootloader to a specified device?",
        ["grub2-mkconfig", "grub2-install", "update-grub", "dracut"],
        1, "Commands (System Management)",
        "`grub2-install` installs the GRUB2 bootloader files to the appropriate location and typically installs the boot code to the MBR or EFI partition. Example: `grub2-install /dev/sda` (for BIOS systems) or `grub2-install --target=x86_64-efi --efi-directory=/boot/efi` (for UEFI systems)."
    )
]