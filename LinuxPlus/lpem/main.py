#!/usr/bin/env python3
"""
Main entry point for the Linux+ Practice Environment Manager (LPEM) tool.

Manages libvirt VMs and runs practice challenges for the CompTIA Linux+ exam (XK0-005).
Uses external snapshots for safe, revertible practice environments.
"""

import sys
import traceback
from pathlib import Path
import typer # Import typer

from .config import Config
# Use console features for the menu if rich is available
from .console import console, RICH_AVAILABLE, Prompt, Confirm 
# Import the command functions directly or the app object
from .cli import app, list_available_vms, list_available_challenges, setup_vm_user, run_challenge_workflow, challenge_app 

def check_dependencies():
    """Check if required dependencies are installed."""
    missing_deps = []
    
    # Check libvirt
    try:
        import libvirt
    except ImportError:
        missing_deps.append("libvirt-python")
    
    # Check paramiko
    try:
        import paramiko
    except ImportError:
        missing_deps.append("paramiko")
    
    # Check yaml
    try:
        import yaml
    except ImportError:
        missing_deps.append("PyYAML")
    
    # Check typer
    try:
        import typer
        from typing_extensions import Annotated
    except ImportError:
        missing_deps.append("typer[all]")
    
    if missing_deps:
        error_msg = "Error: Missing required libraries:\n"
        for dep in missing_deps:
            error_msg += f"  - {dep}\n"
        error_msg += "\nPlease install them (e.g., 'pip install LIBRARY') and try again."
        print(error_msg, file=sys.stderr)
        sys.exit(1)

def check_default_ssh_key():
    """Check if the default SSH key exists and has appropriate permissions."""
    try:
        from .network import _validate_ssh_key
        _validate_ssh_key(Config.DEFAULT_SSH_KEY_PATH)
    except Exception as e:
        # Non-fatal warning if default key is bad, user might specify --key
        console.print(f"[yellow]Warning:[/yellow] Default SSH key issue: {e}", style="yellow")
        console.print("[yellow]         Specify a valid key using --key if needed.[/]", style="yellow")

def check_challenges_dir():
    """Check if the default challenges directory exists."""
    if not Config.DEFAULT_CHALLENGES_DIR.exists():
        console.print(f"[yellow]Warning:[/yellow] Default challenges directory '{Config.DEFAULT_CHALLENGES_DIR}' not found.", style="yellow")
        console.print("[yellow]         Create it or specify a directory using --challenges-dir.[/]", style="yellow")

def display_main_menu():
    """Displays the main menu and handles user selection."""
    console.rule("[bold blue]LPEM Main Menu[/]", style="blue")
    console.print("1. List Available VMs")
    console.print("2. List Available Challenges")
    console.print("3. Run a Challenge")
    console.print("4. Setup VM User")
    console.print("5. Manage Challenges (Sub-menu)")
    console.print("0. Exit")
    console.print("")

    while True:
        try:
            # Use rich Prompt if available for better experience
            if RICH_AVAILABLE:
                choice = Prompt.ask("Enter your choice", choices=["1", "2", "3", "4", "5", "0"], default="0")
            else:
                choice = input("Enter your choice (0-5): ")
                if choice not in ["0", "1", "2", "3", "4", "5"]:
                    raise ValueError("Invalid choice")

            if choice == '1':
                # Call the function registered with Typer
                # Note: You might need to adjust how default arguments are handled
                # if they are usually provided by Typer decorators.
                # A simpler way might be to use subprocess to call 'lpem list-available-vms'
                console.print("\nRunning: List Available VMs...")
                app.registered_commands[0].callback() # Assumes list_available_vms is the first registered command
                # Or more robustly: find the command by name if possible
                # Or call the imported function directly if defaults are handled elsewhere
                # list_available_vms() # May need default args passed explicitly
                break
            elif choice == '2':
                console.print("\nRunning: List Available Challenges...")
                app.registered_commands[1].callback() # Assumes list_available_challenges is second
                # list_available_challenges()
                break
            elif choice == '3':
                 console.print("\nRunning: Run a Challenge...")
                 # This command requires arguments. You'll need to prompt for them.
                 challenge_id = Prompt.ask("Enter the Challenge ID to run")
                 vm_name = Prompt.ask("Enter the VM name", default=Config.DEFAULT_VM_NAME)
                 # You'd need to potentially prompt for other options like --user, --key etc.
                 # For simplicity, this example just shows calling with required arg
                 # Calling the function directly might be easier here:
                 try:
                     run_challenge_workflow(challenge_id=challenge_id, vm_name=vm_name) # Add other args/options as needed
                 except typer.Exit: # Catch typer exits from the command
                     pass 
                 break
                 # Note: Directly calling the Typer app function for complex commands like run-challenge
                 # can be tricky due to argument parsing. Using subprocess might be an alternative:
                 # import subprocess
                 # subprocess.run([sys.executable, "-m", "lpem", "run-challenge", challenge_id, "--vm", vm_name])

            elif choice == '4':
                 console.print("\nRunning: Setup VM User...")
                 # Similar to run-challenge, this requires arguments/options
                 vm_name = Prompt.ask("Enter the VM name", default=Config.DEFAULT_VM_NAME)
                 new_user = Prompt.ask("Enter the username to setup", default=Config.DEFAULT_SSH_USER)
                 # Prompt for other options as needed...
                 try:
                    setup_vm_user(vm_name=vm_name, new_user=new_user) # Add other args/options
                 except typer.Exit:
                     pass
                 break
            elif choice == '5':
                 console.print("\nRunning: Manage Challenges...")
                 # You could display a sub-menu for challenge commands (template, validate)
                 # Or simply run the challenge app with --help
                 import subprocess
                 subprocess.run([sys.executable, "-m", "lpem", "challenge", "--help"])
                 break
            elif choice == '0':
                console.print("Exiting.")
                sys.exit(0)
            else:
                console.print("[red]Invalid choice, please try again.[/]", style="red")

        except ValueError:
             console.print("[red]Invalid input. Please enter a number between 0 and 5.[/]", style="red")
        except Exception as e:
             console.print(f"[bold red]An error occurred running the command:[/]", style="red")
             console.print_exception(show_locals=False)
             # Decide if you want to break or loop again after an error
             break # Exit menu on command error for now


def main():
    """Main entry point for the LPEM CLI tool."""
    # Check dependencies first
    check_dependencies()
    
    # Check other defaults
    check_default_ssh_key()
    check_challenges_dir()

    # Check if arguments were passed (besides script name)
    if len(sys.argv) > 1:
        # If commands/arguments are passed, let Typer handle them as before
        app()
    else:
        # No commands passed, display the main menu
        display_main_menu()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        if RICH_AVAILABLE:
            console.print_exception(show_locals=True)
        else:
            traceback.print_exc()
        sys.exit(1)
