#!/usr/bin/env python3
"""
Linux Plus Study System - Unified Application Entry Point

A comprehensive platform combining web-based quiz interfaces, CLI practice environments,
and VM management capabilities for CompTIA Linux+ exam preparation.
Provides unified access to interactive learning tools, virtual machine lifecycle management,
and hands-on practice challenges with robust error handling and flexible deployment options.
"""

import sys
import logging
import argparse
import traceback
from pathlib import Path
from typing import Optional, Dict, List
import signal
from models.game_state import GameState
# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("Linux Plus Study System requires Python 3.8+. Please upgrade your Python installation.")
    sys.exit(1)

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class LinuxPlusStudySystem:
    """
    Unified Linux Plus Study System application coordinator.
    
    Manages application lifecycle, mode selection, and provides centralized
    error handling and logging infrastructure for web interface, CLI playground,
    and VM management functionality.
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize unified application with comprehensive setup and validation.
        
        Args:
            debug: Enable debug-level logging and detailed error reporting
        """
        self.debug = debug
        self._setup_logging()
        self._setup_signal_handlers()
        self.logger = logging.getLogger(__name__)
        
    def _setup_logging(self) -> None:
        """Configure comprehensive logging infrastructure for application-wide use."""
        log_level = logging.DEBUG if self.debug else logging.INFO
        log_format = '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
        
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(logs_dir / 'linux_plus_study.log'),
                logging.FileHandler(logs_dir / 'linux_plus_study_errors.log', mode='a')
            ]
        )
        
        # Configure third-party library logging levels
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        logging.getLogger("libvirt").setLevel(logging.WARNING)
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        logging.getLogger("flask").setLevel(logging.WARNING)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Linux Plus Study System logging initialized")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            print("\nShutting down gracefully...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _validate_web_dependencies(self) -> bool:
        """Validate web application dependencies."""
        try:
            import flask
            return True
        except ImportError:
            self.logger.error("Flask not available for web mode")
            return False
    
    def _validate_vm_dependencies(self) -> bool:
        """Validate VM management dependencies."""
        try:
            import libvirt
            return True
        except ImportError:
            self.logger.error("Libvirt not available for VM mode")
            return False
    
    def run_web_application(self, host: str = "127.0.0.1", port: int = 5000) -> None:
        """
        Launch the web-based quiz and learning interface.
        
        Args:
            host: Host address to bind the web server
            port: Port number for the web server
        """
        try:
            self.logger.info("Starting web application mode")
            
            if not self._validate_web_dependencies():
                print("Error: Flask dependencies not available. Install with: pip install flask")
                return
            
            # Import web application components
            from views.web_view import create_app
            from controllers.quiz_controller import QuizController
            from controllers.stats_controller import StatsController
            
            # Initialize controllers
            game_state = GameState()
            quiz_controller = QuizController()
            stats_controller = StatsController()
            
            # Create Flask application
            app = create_app(
                quiz_controller=quiz_controller,
                game_state=game_state,
                stats_controller=stats_controller
            )
            
            self.logger.info(f"Web interface loaded successfully - Starting server on {host}:{port}")
            print(f"🌐 Linux Plus Study System Web Interface")
            print(f"📍 Server starting on: http://{host}:{port}")
            print(f"🎯 Features: Quiz System, CLI Playground, Statistics, Achievements")
            print(f"📊 Access your dashboard at: http://{host}:{port}")
            print("Press Ctrl+C to stop the server")
            
            # Run Flask development server
            app.run(host=host, port=port, debug=self.debug)
            
        except ImportError as import_err:
            error_msg = f"Failed to import web application modules: {import_err}"
            self.logger.error(error_msg, exc_info=True)
            print(f"Error: {error_msg}")
            print("Please ensure all web application files are properly installed.")
            
        except Exception as e:
            self.logger.error(f"Web application error: {e}", exc_info=True)
            print(f"Web application failed to start: {e}")
    
    def run_vm_management(self) -> None:
        """
        Launch the VM management CLI interface (LPEM functionality).
        """
        try:
            self.logger.info("Starting VM management mode")
            
            if not self._validate_vm_dependencies():
                print("Error: Libvirt dependencies not available. Install with: pip install libvirt-python")
                return
            
            # Import VM management components
            from vm_integration.controllers.vm_controller import app as vm_cli_app
            
            self.logger.info("VM management interface loaded successfully")
            print("🖥️  Linux Plus Practice Environment Manager (LPEM)")
            print("🔧 VM Management & Practice Challenges")
            print("📚 Interactive Linux+ Exam Preparation")
            
            # Run VM CLI application
            vm_cli_app()
            
        except ImportError as import_err:
            error_msg = f"Failed to import VM management modules: {import_err}"
            self.logger.error(error_msg, exc_info=True)
            print(f"Error: {error_msg}")
            print("Please ensure VM integration components are properly configured.")
            
        except Exception as e:
            self.logger.error(f"VM management error: {e}", exc_info=True)
            print(f"VM management failed to start: {e}")
    
    def run_cli_playground(self) -> None:
        """
        Launch standalone CLI playground for command practice.
        """
        try:
            self.logger.info("Starting CLI playground mode")
            
            # Import CLI playground components
            from utils.cli_playground import CLIPlayground
            
            playground = CLIPlayground()
            
            self.logger.info("CLI playground loaded successfully")
            print("💻 Linux Plus CLI Playground")
            print("📖 Interactive Command Line Practice")
            print("🎓 Safe Environment for Learning Linux Commands")
            print("Type 'help' for available commands, 'exit' to quit")
            
            # Run interactive CLI session
            playground.start_interactive_session()
            
        except ImportError as import_err:
            error_msg = f"Failed to import CLI playground modules: {import_err}"
            self.logger.error(error_msg, exc_info=True)
            print(f"Error: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"CLI playground error: {e}", exc_info=True)
            print(f"CLI playground failed to start: {e}")
    
    def display_main_menu(self) -> None:
        """Display interactive main menu for mode selection."""
        while True:
            print("\n" + "="*60)
            print("🐧 LINUX PLUS STUDY SYSTEM - UNIFIED PLATFORM")
            print("="*60)
            print("Select your learning mode:")
            print()
            print("1. 🌐 Web Interface    - Full quiz system with web UI")
            print("2. 🖥️  VM Management   - Virtual machine practice environments")
            print("3. 💻 CLI Playground   - Interactive command line practice")
            print("4. ❓ Help            - System information and usage guide")
            print("5. 🚪 Exit            - Quit application")
            print()
            
            try:
                choice = input("Enter your choice (1-5): ").strip()
                
                if choice == '1':
                    print("\nStarting web interface...")
                    self.run_web_application()
                    
                elif choice == '2':
                    print("\nStarting VM management...")
                    self.run_vm_management()
                    
                elif choice == '3':
                    print("\nStarting CLI playground...")
                    self.run_cli_playground()
                    
                elif choice == '4':
                    self.display_help()
                    
                elif choice == '5':
                    print("Thank you for using Linux Plus Study System!")
                    break
                    
                else:
                    print("Invalid choice. Please enter 1-5.")
                    
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                print("\n\nGoodbye!")
                break
    
    def display_help(self) -> None:
        """Display comprehensive help and system information."""
        print("\n" + "="*60)
        print("📚 LINUX PLUS STUDY SYSTEM - HELP & INFORMATION")
        print("="*60)
        print()
        print("🎯 PURPOSE:")
        print("   Comprehensive platform for CompTIA Linux+ exam preparation")
        print("   combining web-based learning with hands-on practice.")
        print()
        print("🌟 FEATURES:")
        print("   • Interactive quiz system with progress tracking")
        print("   • CLI command playground for safe practice")
        print("   • VM management for real Linux environments")
        print("   • Achievement system and detailed statistics")
        print("   • Progressive difficulty and adaptive learning")
        print()
        print("🚀 MODES:")
        print("   Web Interface  - Access via browser for full learning platform")
        print("   VM Management  - Create and manage practice VMs")
        print("   CLI Playground - Practice Linux commands safely")
        print()
        print("📝 COMMAND LINE OPTIONS:")
        print("   --web          Start in web mode directly")
        print("   --vm           Start in VM management mode")
        print("   --cli          Start in CLI playground mode")
        print("   --host HOST    Set web server host (default: 127.0.0.1)")
        print("   --port PORT    Set web server port (default: 5000)")
        print("   --debug        Enable debug mode")
        print("   --help         Show this help message")
        print()
        print("💡 EXAMPLES:")
        print("   python main.py --web --port 8080")
        print("   python main.py --vm --debug")
        print("   python main.py --cli")
        print()
        input("Press Enter to continue...")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create comprehensive command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Linux Plus Study System - Unified Learning Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                     # Interactive menu
  python main.py --web               # Start web interface
  python main.py --vm                # Start VM management
  python main.py --cli               # Start CLI playground
  python main.py --web --port 8080   # Web interface on port 8080
        """
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--web', action='store_true',
                           help='Start web interface mode')
    mode_group.add_argument('--vm', action='store_true',
                           help='Start VM management mode')
    mode_group.add_argument('--cli', action='store_true',
                           help='Start CLI playground mode')
    
    # Web server configuration
    parser.add_argument('--host', default='127.0.0.1',
                       help='Host address for web server (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port number for web server (default: 5000)')
    
    # General options
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode with detailed logging')
    
    return parser


def main():
    """
    Primary execution entry point with comprehensive error management.
    
    Initializes the unified application coordinator and handles top-level
    application lifecycle with robust error handling and user feedback.
    """
    try:
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # Initialize the unified application
        app = LinuxPlusStudySystem(debug=args.debug)
        
        # Determine run mode based on arguments
        if args.web:
            app.run_web_application(host=args.host, port=args.port)
            
        elif args.vm:
            app.run_vm_management()
            
        elif args.cli:
            app.run_cli_playground()
            
        else:
            # No specific mode selected - show interactive menu
            app.display_main_menu()
            
    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user. Goodbye!")
        sys.exit(0)
        
    except Exception as critical_error:
        # Handle any errors that occur before proper logging is set up
        print(f"Critical startup error: {critical_error}")
        if '--debug' in sys.argv or '-d' in sys.argv:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()