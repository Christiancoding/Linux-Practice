#!/usr/bin/env python3
"""
Linux+ Practice Environment Manager (LPEM) - Main Entry Point

A comprehensive command-line interface for managing libvirt virtual machines
and executing practice challenges for CompTIA Linux+ exam preparation.
Provides VM lifecycle management, snapshot operations, and interactive
challenge workflows with robust error handling and user-friendly reporting.
"""

import sys
import logging
import traceback
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("Linux+ Practice Environment Manager requires Python 3.8+. Please upgrade your Python installation.")
    sys.exit(1)

# Validate critical dependencies early

try:
    import libvirt  # type: ignore
except ImportError:
    print("Error: Missing required library 'libvirt-python'.")
    print("Please install it (e.g., 'pip install libvirt-python' or via system package manager) and try again.")
    sys.exit(1)

class LPEMApplication:
    """
    Linux+ Practice Environment Manager application coordinator.
    
    Manages application lifecycle, configuration validation, and provides
    centralized error handling and logging infrastructure for the entire
    VM management and challenge execution system.
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize LPEM application with comprehensive setup and validation.
        
        Args:
            debug: Enable debug-level logging and detailed error reporting
        """
        self.debug = debug
        self._setup_logging()
        self._validate_environment()
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
                logging.FileHandler(logs_dir / 'lpem.log'),
                logging.FileHandler(logs_dir / 'lpem_errors.log', mode='a')
            ]
        )
        
        # Configure third-party library logging levels
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        logging.getLogger("libvirt").setLevel(logging.WARNING)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("LPEM Application logging initialized")
    
    def _validate_environment(self) -> None:
        """
        Perform comprehensive environment validation and dependency checking.
        
        Validates system requirements, library versions, and runtime environment
        to ensure optimal application performance and user experience.
        """
        try:
            # Validate libvirt accessibility
            test_conn = libvirt.openReadOnly('qemu:///system') 
            if test_conn:
                test_conn.close()
            
            # Validate SSH key directory accessibility
            ssh_dir = Path.home() / '.ssh'
            if not ssh_dir.exists():
                print(f"Warning: SSH directory '{ssh_dir}' not found. You may need to set up SSH keys.")
            
            # Validate working directory permissions
            current_dir = Path.cwd()
            if not current_dir.is_dir() or not (current_dir / 'controllers').exists():
                print("Warning: Application may not be running from the correct directory.")
                print("Expected to find 'controllers' subdirectory in current working directory.")
        
        except Exception as e:
            if self.debug:
                print(f"Environment validation encountered issues: {e}")
            # Don't fail hard on validation issues - just warn and continue
    
    def run_application(self) -> None:
        """
        Execute the main LPEM application with comprehensive error handling.
        
        Loads the VM controller CLI interface and handles application lifecycle
        with robust error reporting and graceful failure handling.
        """
        try:
            self.logger.info("Starting Linux+ Practice Environment Manager")
            
            # Import and run the main CLI application
            from controllers.vm_controller import app
            
            self.logger.info("CLI interface loaded successfully")
            app()
            
        except ImportError as import_err:
            error_msg = f"Failed to import required modules: {import_err}"
            self.logger.error(error_msg, exc_info=True)
            print(f"Error: {error_msg}")
            print("Please ensure all application files are in the correct locations.")
            sys.exit(1)
            
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
            print("\nApplication interrupted by user. Goodbye!")
            sys.exit(0)
            
        except Exception as unexpected_error:
            error_msg = f"Unexpected application error: {unexpected_error}"
            self.logger.error(error_msg, exc_info=True)
            
            print(f"Error: {error_msg}")
            if self.debug:
                print("\nDetailed error information:")
                traceback.print_exc()
            else:
                print("Run with --debug for detailed error information.")
            
            sys.exit(1)
        
        finally:
            self.logger.info("LPEM Application shutdown complete")


def main():
    """
    Primary execution entry point with comprehensive error management.
    
    Initializes the LPEM application coordinator and handles top-level
    application lifecycle with robust error handling and user feedback.
    """
    # Parse basic debug flag from command line arguments
    debug_mode = '--debug' in sys.argv or '-d' in sys.argv
    
    try:
        # Initialize and run the application
        lpem_app = LPEMApplication(debug=debug_mode)
        lpem_app.run_application()
        
    except Exception as critical_error:
        # Handle any errors that occur before proper logging is set up
        print(f"Critical startup error: {critical_error}")
        if debug_mode:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()