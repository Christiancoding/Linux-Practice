#!/usr/bin/env python3
"""
Linux+ Study Game - Main Entry Point

A comprehensive study tool for CompTIA Linux+ certification preparation
featuring both CLI and web interfaces with gamification elements.
"""

import sys
import traceback
import signal
import sys
# Ensure the script is run with Python 3
if sys.version_info < (3, 0):
    print("This script requires Python 3. Please run with python3.")
    sys.exit(1)
import os

# Import configuration and utilities
from utils.config import *
from models.game_state import GameState
from views.cli_view import LinuxPlusStudyCLI
import views.cli_view as cli_view
from views.web_view import LinuxPlusStudyWeb

def detect_interface_preference():
    """
    Detect if we should force CLI mode based on environment or arguments.
    
    Returns:
        str: 'cli', or 'ask' for user choice
    """
    # Check for command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == 'cli':
            return 'cli'
    
    # Detect non-interactive environment
    if not sys.stdin.isatty():
        return 'cli'
    
    # Interactive environment - ask user
    return 'ask'

def get_user_interface_choice_with_web():
    """
    Prompt user to choose between CLI orweb interfaces.
    
    Returns:
        str: 'cli', or 'web'
    """
    while True:
        try:
            prompt_text = f"{COLOR_PROMPT}Choose interface ({COLOR_OPTIONS}CLI{COLOR_PROMPT} or {COLOR_OPTIONS}web{COLOR_PROMPT}): {COLOR_INPUT}"
            print(prompt_text, end='')
            sys.stdout.flush()
            
            choice = input().lower().strip()
            print(COLOR_RESET, end='')
            
            if choice in ['cli', 'web']:
                return choice
            else:
                print(f"{COLOR_INFO} Invalid choice. Please type 'cli', or 'web'. {COLOR_RESET}")
                
        except EOFError:
            print(f"\n{COLOR_ERROR} Input interrupted. Defaulting to CLI. {COLOR_RESET}")
            return 'cli'
        except KeyboardInterrupt:
            print(f"\n{COLOR_WARNING} Operation cancelled by user. Exiting. {COLOR_RESET}")
            sys.exit(0)

def get_user_interface_choice():
    """
    Prompt user to choose between CLI and web interfaces.
    
    Returns:
        str: 'cli' or 'web'
    """
    while True:
        try:
            prompt_text = f"{COLOR_PROMPT}Choose interface ({COLOR_OPTIONS}CLI{COLOR_PROMPT} or {COLOR_OPTIONS}web{COLOR_PROMPT}): {COLOR_INPUT}"
            print(prompt_text, end='')
            sys.stdout.flush()
            
            choice = input().lower().strip()
            print(COLOR_RESET, end='')
            
            if choice in ['cli', 'web']:
                return choice
            else:
                print(f"{COLOR_INFO} Invalid choice. Please type 'cli' or 'web'. {COLOR_RESET}")
                
        except EOFError:
            print(f"\n{COLOR_ERROR} Input interrupted. Defaulting to CLI. {COLOR_RESET}")
            return 'cli'
        except KeyboardInterrupt:
            print(f"\n{COLOR_WARNING} Operation cancelled by user. Exiting. {COLOR_RESET}")
            sys.exit(0)


def launch_cli_interface(game_state):
    """
    Launch the CLI interface.
    
    Args:
        game_state: GameState instance
    """
    try:
        cli_view = LinuxPlusStudyCLI(game_state)
        cli_view.display_welcome_message()
        cli_view.main_menu()
    except KeyboardInterrupt:
        print(f"\n{COLOR_WARNING} Keyboard interrupt detected. Saving progress and exiting. {COLOR_RESET}")
        game_state.save_history()
        game_state.save_achievements()
        sys.exit(0)
    except Exception as e:
        print(f"\n{COLOR_ERROR} An unexpected error occurred in CLI mode: {e} {COLOR_RESET}")
        print(f"{COLOR_INFO} Attempting to save progress before exiting... {COLOR_RESET}")
        game_state.save_history()
        game_state.save_achievements()
        traceback.print_exc()
        sys.exit(1)
def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🙏 Thanks for using Linux+ Study App!")
    print("📚 Keep practicing and good luck with your certification!")
    print("👋 Goodbye!\n")
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def launch_web_interface(game_state):
    """
    Launch the web interface.
    
    Args:
        game_state: GameState instance
    """
    try:
        # Register signal handler for graceful exit
        signal.signal(signal.SIGINT, signal_handler)
        web_view = LinuxPlusStudyWeb(game_state)
        print("🚀 Starting Linux+ Study App...")
        print("📖 Web interface loading...")
        print("💡 Press Ctrl+C to exit gracefully")
        web_view.start()
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        print(f"\n❌ Error starting web interface: {e}")
        print("🔧 Please check your installation and try again.")
        sys.exit(1)
        
    except ImportError as e:
        print(f"Error: Failed to initialize web interface.")
        print(f"Missing required packages. Install with: pip install flask pywebview")
        print(f"Error details: {e}")
        
        # Attempt to save before exiting
        game_state.save_history()
        game_state.save_achievements()
        sys.exit(1)
        
    except Exception as e:
        print(f"\nAn unexpected error occurred launching the web interface: {e}")
        print("Error details:")
        traceback.print_exc()
        print("Attempting to save progress...")
        game_state.save_history()
        game_state.save_achievements()
        sys.exit(1)
def main():
    """Main entry point for the Linux+ Study Game."""
    
    # Initialize colorama if available
    try:
        if 'colorama' in sys.modules:
            import colorama
            colorama.init(autoreset=True)
    except Exception as e:
        print(f"Warning: Failed to initialize colorama: {e}")
    
    # Initialize game state
    try:
        game_state = GameState()
    except Exception as e:
        print(f"Fatal error: Failed to initialize game state: {e}")
        traceback.print_exc()
        sys.exit(1)
    print(f"{COLOR_INFO}Welcome to the Linux+ Study Game!{COLOR_RESET}")
    # Determine interface preference
    interface_preference = detect_interface_preference()
    
    if interface_preference == 'ask':
        interface_choice = get_user_interface_choice_with_web()  # Use new function
    else:
        interface_choice = interface_preference
    
    # Launch appropriate interface
    print(f"{COLOR_INFO}Starting Linux+ Study Game in {interface_choice.upper()} mode...{COLOR_RESET}")
    
    if interface_choice == 'web':
        launch_web_interface(game_state)
    else:
        launch_cli_interface(game_state)


if __name__ == "__main__":
    main()