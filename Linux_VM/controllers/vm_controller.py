#!/usr/bin/env python3
"""
VM Controller Module

Comprehensive CLI interface for Linux+ Practice Environment Manager (LPEM).
Manages libvirt VMs and executes practice challenges for CompTIA Linux+ exam preparation.
"""

import sys
import logging
import traceback
from pathlib import Path
from typing import Dict, Optional, Any

# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("This application requires Python 3.8+. Please upgrade your Python installation.")
    sys.exit(1)

# Third-party imports with error handling
try:
    import typer
    from typing_extensions import Annotated
except ImportError:
    print("Error: Missing required library 'typer'.")
    print("Please install it: pip install typer[all]")
    sys.exit(1)


# Local imports
from utils.console_helper import console, RICH_AVAILABLE

from rich.console import Console
console: Console

if RICH_AVAILABLE:
    pass
from utils.config import config
from utils.exceptions import (
    PracticeToolError,
    SnapshotOperationError,
    ChallengeLoadError,
    ChallengeValidationError
)
from utils.vm_manager import (
    connect_libvirt,
    close_libvirt,
    find_vm,
    list_vms,
    start_vm,
    wait_for_vm_ready,
    get_vm_ip
)
from utils.ssh_manager import (
    run_ssh_command
)
from utils.snapshot_manager import (
    create_external_snapshot,
    revert_to_snapshot,
    delete_snapshot,
    list_snapshots
)
from utils.challenge_manager import (
    load_challenges_from_dir,
    display_challenge_details,
    execute_setup_steps,
    manage_hints,
    create_challenge_template
)
from utils.validators import (
    execute_validation_step,
    validate_challenge_file
)
def validate_ssh_key(key_path: Path):
    # Basic fallback: just check if the file exists and is readable
    if not key_path.exists() or not key_path.is_file():
        raise PracticeToolError(f"SSH key file '{key_path}' does not exist or is not a file.")
    if not key_path.stat().st_mode & 0o400:
        raise PracticeToolError(f"SSH key file '{key_path}' is not readable.")
    return key_path

# Set up module logger
logger = logging.getLogger(__name__)

if RICH_AVAILABLE:
    from rich.panel import Panel
    from rich.table import Table  # Ensure Table is imported unconditionally


class VMController:
    """
    Advanced VM management controller with comprehensive CLI interface
    for Linux+ practice environment operations.
    """
    
    def __init__(self):
        """Initialize the VM controller."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._setup_logging()
        self._validate_environment()
    
    def _setup_logging(self) -> None:
        """Configure comprehensive logging infrastructure."""
        try:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler('lpem.log', mode='a')
                ]
            )
        except PermissionError:
            # Fallback to console-only logging if file access fails
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                handlers=[logging.StreamHandler()]
            )
    
    def _validate_environment(self) -> None:
        """Validate environment setup and dependencies."""
        try:
            # Check default SSH key validity (non-fatal warning)
            try:
                validate_ssh_key(config.ssh.DEFAULT_SSH_KEY_PATH)
            except PracticeToolError as key_err:
                console.print(f"[yellow]Warning:[/yellow] Default SSH key issue: {key_err}", style="yellow")
                console.print("[yellow]         Specify a valid key using --key if needed.[/]", style="yellow")
            except Exception as key_check_err:
                console.print(f"[yellow]Warning:[/yellow] Could not check default SSH key: {key_check_err}", style="yellow")
            
            # Check if default challenges directory exists
            if not config.challenge.DEFAULT_CHALLENGES_DIR.exists():
                console.print(f"[yellow]Warning:[/yellow] Default challenges directory '{config.challenge.DEFAULT_CHALLENGES_DIR}' not found.", style="yellow")
                console.print("[yellow]         Create it or specify a directory using --challenges-dir.[/]", style="yellow")
                
        except Exception as e:
            self.logger.error(f"Environment validation error: {e}", exc_info=True)


# Global controller instance
vm_controller = VMController()

# --- Typer Application Setup ---
app = typer.Typer(
    help="Linux+ Practice Environment Manager (LPEM)\n\n"
         "Manages libvirt VMs and runs practice challenges for the CompTIA Linux+ exam (XK0-005).\n"
         "Uses external snapshots for safe, revertible practice environments.",
    rich_markup_mode="rich" if RICH_AVAILABLE else "markdown"
)

# Challenge management sub-application
challenge_app = typer.Typer(
    name="challenge", 
    help="Manage challenge definitions (create templates, validate).",
    rich_markup_mode="rich" if RICH_AVAILABLE else "markdown"
)
app.add_typer(challenge_app)

# VM management sub-application  
vm_app = typer.Typer(
    name="vm",
    help="Virtual machine management operations.",
    rich_markup_mode="rich" if RICH_AVAILABLE else "markdown"
)
app.add_typer(vm_app)


# --- Main VM Commands ---

@app.command()
def list_available_vms(
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = config.vm.LIBVIRT_URI
):
    """Lists virtual machines known to libvirt."""
    conn = None
    try:
        conn = connect_libvirt(libvirt_uri)
        list_vms(conn)
    except PracticeToolError as e:
        console.print(f"[bold red]:x: Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if conn is not None:
            close_libvirt(conn)


@app.command(name="list-challenges")
def list_available_challenges(
    challenges_dir: Annotated[Path, typer.Option("--dir", "-d",
        help="Directory containing challenge YAML files.",
        exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True
    )] = config.challenge.DEFAULT_CHALLENGES_DIR
):
    """Lists valid practice challenges found in the specified directory."""
    try:
        challenges = load_challenges_from_dir(challenges_dir)
    except ChallengeLoadError as e:
        console.print(f"[bold red]:x: Error loading challenges:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)

    if not challenges:
        no_challenges_msg = "[i]No valid challenges loaded.[/]"
        if RICH_AVAILABLE:
            from rich.panel import Panel
            console.print(Panel(no_challenges_msg, title="Available Challenges", border_style="dim"))
        else:
            console.print(no_challenges_msg)
        return

    if RICH_AVAILABLE:
        from rich.table import Table
        table = Table(
            title=f"[bold blue]Available Challenges[/] ([dim]from {challenges_dir}[/])", 
            show_header=True, 
            header_style="bold magenta"
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("Category", style="yellow")
        table.add_column("Difficulty", style="green")
        table.add_column("Score", justify="right", style="blue")

        # Sort by category, then name for consistent listing
        sorted_challenges = sorted(
            challenges.values(), 
            key=lambda c: (c.get('category', 'zzz').lower(), c.get('name', 'zzz').lower())
        )

        for chal in sorted_challenges:
            table.add_row(
                chal['id'],
                chal.get('name', '[dim]N/A[/]'),
                chal.get('category', '[dim]N/A[/]'),
                chal.get('difficulty', '[dim]N/A[/]'),
                str(chal.get('score', 0)),
            )

        console.print(table)
    else:
        console.print("\nAvailable Challenges:")
        console.print("-" * 80)
        for challenge_id, challenge in sorted(challenges.items()):
            console.print(f"{challenge_id:25} | {challenge.get('name', 'N/A'):30} | {challenge.get('difficulty', 'N/A'):10}")
        console.print("-" * 80)

    console.print("\nRun '[bold]lpem run-challenge <ID>[/]' to start a challenge.")
    console.print("Use '[bold]lpem challenge --help[/]' for creation/validation commands.")


@app.command(name="run-challenge")
def run_challenge(
    challenge_id: Annotated[str, typer.Argument(help="ID of the challenge to run.")],
    vm_name: Annotated[str, typer.Option("--vm", help="Name of the libvirt VM to use.")] = config.vm.DEFAULT_VM_NAME,
    ssh_user: Annotated[str, typer.Option("--user", help="SSH username for VM access.")] = config.ssh.DEFAULT_SSH_USER,
    ssh_key: Annotated[Path, typer.Option("--key", help="Path to SSH private key.", exists=True, file_okay=True, readable=True)] = config.ssh.DEFAULT_SSH_KEY_PATH,
    challenges_dir: Annotated[Path, typer.Option("--challenges-dir", "-d", 
        help="Directory containing challenge YAML files.",
        exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True
    )] = config.challenge.DEFAULT_CHALLENGES_DIR,
    snapshot_name: Annotated[str, typer.Option("--snapshot", help="Name for the practice snapshot.")] = "practice-session",
    auto_confirm: Annotated[bool, typer.Option("--yes", "-y", help="Skip interactive confirmations.")] = False,
    keep_snapshot: Annotated[bool, typer.Option("--keep-snapshot", help="Do not delete snapshot after running.")] = False,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Print detailed command output.")] = False,
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = config.vm.LIBVIRT_URI
):
    """Runs a challenge: snapshot VM, start, setup, prompt/simulate user, validate, cleanup."""
    
    console.rule(f"[bold green]Starting Challenge: [cyan]{challenge_id}[/cyan][/]", style="green")
    
    # Initialize workflow variables
    conn: Optional[Any] = None
    domain: Optional[Any] = None
    vm_ip: Optional[str] = None
    snapshot_created = False
    challenge: Optional[Dict[str, Any]] = None
    challenge_passed = False
    current_score = 0
    hints_used_count = 0
    total_hint_cost = 0

    # Resolve and validate SSH key path
    try:
        ssh_key_path = validate_ssh_key(ssh_key)
    except PracticeToolError as key_err:
        console.print(f"[bold red]:x: SSH Key Error:[/bold red] {key_err}", style="red")
        raise typer.Exit(code=1)

    try:
        # --- 0. Load Challenges & Select Target Challenge ---
        challenges = load_challenges_from_dir(challenges_dir)
        if not challenges:
            raise PracticeToolError("No valid challenges were loaded.")

        challenge = challenges.get(challenge_id)
        if not challenge:
            ids_text = "\n".join([f"- {cid}" for cid in sorted(challenges.keys())]) or "[i]None[/]"
            panel_content = (f"[bold red]Error:[/bold red] Challenge ID '[yellow]{challenge_id}[/]' not found "
                           f"among valid challenges in '{challenges_dir}'.\n\n[bold]Available valid challenges:[/]\n{ids_text}")
            if RICH_AVAILABLE:
                from rich.panel import Panel
                console.print(Panel(panel_content, title="[bold red]Challenge Not Found[/]", border_style="red"))
            else:
                console.print(panel_content)
            raise typer.Exit(code=1)

        challenge = dict(challenge)  # Ensure type is Dict[str, Any]
        current_score: int = challenge['score']

        # --- 1. Connect to Libvirt & Find VM ---
        conn = connect_libvirt(libvirt_uri)
        domain = find_vm(conn, vm_name)

        # --- 2. Snapshot Management: Ensure Clean Slate ---
        console.print(f"\n:mag_right: Checking for existing snapshot '[cyan]{snapshot_name}[/cyan]'...")
        try:
            domain.snapshotLookupByName(snapshot_name, 0)
            console.print(f"  :warning: Found existing snapshot '[cyan]{snapshot_name}[/cyan]'.")
            
            if not auto_confirm:
                if RICH_AVAILABLE:
                    from rich.prompt import Confirm
                    delete_existing = Confirm.ask("Delete existing snapshot and create fresh one?", default=True)
                else:
                    delete_existing_input = input("Delete existing snapshot and create fresh one? [Y/n]: ")
                    delete_existing = delete_existing_input.strip().lower() in ("", "y", "yes")
            else:
                delete_existing = True
                console.print("[dim]Auto-confirming snapshot deletion.[/]")
            
            if delete_existing:
                delete_snapshot(domain, snapshot_name)
                console.print(f"[green]:heavy_check_mark: Deleted existing snapshot.[/]")
            else:
                console.print("[yellow]Aborted by user.[/]")
                raise typer.Exit()
                
        except Exception:
            # No existing snapshot found, proceed normally
            pass

        # --- 3. Create Fresh Snapshot ---
        try:
            snapshot_created = create_external_snapshot(domain, snapshot_name)
        except SnapshotOperationError as snap_err:
            console.print(f"[bold red]:x: Snapshot creation failed:[/bold red] {snap_err}", style="red")
            raise typer.Exit(code=1)

        if not snapshot_created:
            raise PracticeToolError("Snapshot creation failed for unknown reasons.")

        # --- 4. VM Startup and Network Detection ---
        if not domain.isActive():
            console.print(f":rocket: Starting VM '[cyan]{vm_name}[/cyan]'...")
            start_vm(domain)
        else:
            console.print(f"[dim]VM '[cyan]{vm_name}[/cyan]' is already running.[/]")

        console.print(":globe_with_meridians: Detecting VM IP address...")
        vm_ip = get_vm_ip(conn, domain)
        if not vm_ip:
            raise PracticeToolError("Could not determine VM IP address.")

        console.print(f"[green]:heavy_check_mark: VM accessible at [cyan]{vm_ip}[/cyan][/]")

        # Wait for SSH readiness
        console.print(":hourglass: Waiting for SSH service...")
        wait_for_vm_ready(str(vm_ip), ssh_user, ssh_key_path)
        
        # Verify SSH key permissions
        if ssh_key_path.stat().st_mode & config.ssh.KEY_PERMISSIONS_MASK != 0o400:
            raise PracticeToolError(f"SSH key '{ssh_key_path}' permissions are too open. Set to 0400.")

        # Test SSH connection
        console.print(":unlock: Testing SSH connection...")
        run_ssh_command(vm_ip, ssh_user, ssh_key_path, "echo 'SSH connection successful!'", timeout=config.ssh.CONNECT_TIMEOUT_SECONDS)
        console.print("[green]:heavy_check_mark: SSH connection established.[/]")

        # --- 4. Display Challenge Information ---
        display_challenge_details(challenge, challenge_id)

        # --- 5. Run Setup Steps ---
        execute_setup_steps(challenge, challenge_id, vm_ip, ssh_user, ssh_key_path, verbose)

        # --- 6. User Interaction Phase ---
        if not auto_confirm:
            console.rule("[bold]Your Turn![/]", style="green")
            action_panel_content = ("The VM is ready! Connect via SSH and complete the challenge objective.\n\n"
                                   f"**SSH Command:** `ssh -i {ssh_key_path} {ssh_user}@{vm_ip}`\n\n"
                                   "Perform the actions described in the challenge objective above.")
            
            if RICH_AVAILABLE:
                from rich.markdown import Markdown
                from rich.panel import Panel
                console.print(Panel(Markdown(action_panel_content), 
                                  title="Perform the actions on the VM.", 
                                  border_style="green", expand=False))
            else:
                console.print(f"\n--- Your Turn ---\n{action_panel_content}\n------")

            # Hint System
            current_score, hints_used_count, total_hint_cost = manage_hints(challenge, current_score)

            # Wait for user confirmation to proceed
            if RICH_AVAILABLE:
                from rich.prompt import Prompt
                Prompt.ask("\n:arrow_forward: Press Enter when ready to validate your work")
            else:
                input("\n-> Press Enter when ready to validate your work")

        # --- 7. Validation ---
        console.rule("[bold]Challenge Validation[/]", style="blue")
        validation_steps = challenge.get("validation") or []
        # Explicitly type as list of dicts for static analysis
        validation_steps: list[dict[str, Any]] = validation_steps
        all_validations_passed = True

        for i, step in enumerate(validation_steps):
            step: Dict[str, Any]  # type annotation for static analysis
            try:
                # Security reminder for verbose mode
                if verbose and step.get("type") == "run_command" and "command" in step:
                    console.print(f"[dim]Executing validation command: '{step['command']}'[/]")

                execute_validation_step(i + 1, step, vm_ip, ssh_user, ssh_key_path, verbose)

            except ChallengeValidationError:
                # execute_validation_step already printed the failure panel
                all_validations_passed = False
                console.print("[yellow]Stopping validation due to step failure.[/]", style="yellow")
                break
            except PracticeToolError as tool_err:
                console.print(f"[bold red]:x: Tool Error during validation step {i+1}:[/bold red] {tool_err}", style="red")
                all_validations_passed = False
                break

        # --- 8. Results ---
        challenge_passed = all_validations_passed
        final_score = current_score if challenge_passed else 0
        
        from ..utils.challenge_manager import ChallengeManager
        manager = ChallengeManager()
        manager.display_challenge_results(challenge, challenge_id, challenge_passed, 
                                        final_score, hints_used_count, total_hint_cost)

    except KeyboardInterrupt:
        console.print("\n[yellow]:warning: Operation interrupted by user.[/]", style="yellow")
        raise typer.Exit(code=1)
    except PracticeToolError as e:
        console.print(f"[bold red]:x: Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]:x: Unexpected error:[/bold red] {e}", style="red")
        if verbose and RICH_AVAILABLE:
            console.print_exception(show_locals=False)
        elif verbose:
            traceback.print_exc()
        raise typer.Exit(code=1)
    finally:
        # --- 9. Cleanup ---
        if snapshot_created and not keep_snapshot:
            try:
                console.print(f"\n:wastebasket: Cleaning up snapshot '[cyan]{snapshot_name}[/cyan]'...")
                if domain:
                    delete_snapshot(domain, snapshot_name)
                    console.print("[green]:heavy_check_mark: Snapshot cleanup completed.[/]")
            except Exception as cleanup_err:
                console.print(f"[yellow]:warning: Snapshot cleanup failed: {cleanup_err}[/]", style="yellow")
        
        # Close libvirt connection
        if conn is not None:
            close_libvirt(conn)
        
        if challenge_passed:
            console.print(f"\n[bold green]:trophy: Congratulations! Challenge '[cyan]{challenge_id}[/cyan]' completed successfully![/]")
        
        console.rule(f"[bold green]Challenge Workflow Finished: [cyan]{challenge_id}[/cyan][/]", style="green")


# --- Challenge Management Commands ---

@challenge_app.command("create-template")
def create_challenge_template_cmd(
    output_file: Annotated[Path, typer.Option("--output", "-o", 
        help="Path to save the template YAML file.", 
        dir_okay=False, writable=True
    )] = Path("challenge_template.yaml")
):
    """Creates a template YAML file for defining a new challenge."""
    try:
        if output_file.exists():
            if RICH_AVAILABLE:
                from rich.prompt import Confirm
                overwrite = Confirm.ask(f"File '[cyan]{output_file.resolve()}[/cyan]' already exists. Overwrite?", default=False)
            else:
                overwrite_input = input(f"File '{output_file.resolve()}' already exists. Overwrite? [y/N]: ")
                overwrite = overwrite_input.strip().lower() in ("y", "yes")
            if not overwrite:
                console.print("[yellow]Aborted.[/]")
                raise typer.Exit()

        create_challenge_template(output_file)
        
        # Display template content using Rich Syntax if available
        if RICH_AVAILABLE:
            try:
                from rich.syntax import Syntax  # Ensure Syntax is imported here
                from rich.panel import Panel    # Ensure Panel is imported here
                template_content = output_file.read_text(encoding='utf-8')
                syntax = Syntax(template_content, "yaml", theme="default", line_numbers=True, word_wrap=False)
                console.print(Panel(syntax, title="Template Content", border_style="green", expand=False))
            except Exception as read_err:
                console.print(f"[yellow]Could not display template content: {read_err}[/]", style="yellow")

        console.print("\n:pencil: Edit this file to define your challenge.")
        if RICH_AVAILABLE:
            from rich.panel import Panel
            console.print(Panel("[bold red]SECURITY WARNING:[/bold red] Be extremely careful with 'run_command' steps in setup/validation.", border_style="red"))
        else:
            console.print("[bold red]SECURITY WARNING:[/bold red] Be extremely careful with 'run_command' steps in setup/validation.")

    except IOError as e:
        console.print(f"[bold red]:x: Error writing template file '{output_file}': {e}[/]", style="red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]:x: An unexpected error occurred: {e}[/]", style="red")
        raise typer.Exit(code=1)


@challenge_app.command("validate")
def validate_challenge_yaml(
    file_path: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True,
        help="Path to the challenge YAML file to validate."
    )]
):
    """Validates the structure and basic syntax of a challenge YAML file."""
    try:
        validate_challenge_file(file_path)
    except typer.Exit:
        # Re-raise typer exits (they already have proper exit codes)
        raise
    except Exception as e:
        console.print(f"[bold red]:x: Validation failed with unexpected error: {e}[/]", style="red")
        if RICH_AVAILABLE:
            console.print_exception(show_locals=False)
        else:
            traceback.print_exc()
        raise typer.Exit(code=1)


# --- VM Management Commands ---

@vm_app.command("start")
def start_vm_command(
    vm_name: Annotated[str, typer.Argument(help="Name of the VM to start.")],
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = config.vm.LIBVIRT_URI
):
    """Start a virtual machine."""
    conn = None
    try:
        conn = connect_libvirt(libvirt_uri)
        domain = find_vm(conn, vm_name)
        
        if domain.isActive():
            console.print(f"[yellow]:warning: VM '[cyan]{vm_name}[/cyan]' is already running.[/]", style="yellow")
        else:
            start_vm(domain)
            console.print(f"[green]:rocket: Successfully started VM '[cyan]{vm_name}[/cyan]'.[/]")
            
    except PracticeToolError as e:
        console.print(f"[bold red]:x: Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if conn is not None:
            close_libvirt(conn)


@vm_app.command("stop")
def stop_vm_command(
    vm_name: Annotated[str, typer.Argument(help="Name of the VM to stop.")],
    force: Annotated[bool, typer.Option("--force", help="Force shutdown without graceful shutdown.")] = False,
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = config.vm.LIBVIRT_URI
):
    """Stop a virtual machine."""
    conn = None
    try:
        conn = connect_libvirt(libvirt_uri)
        domain = find_vm(conn, vm_name)
        
        if not domain.isActive():
            console.print(f"[yellow]:warning: VM '[cyan]{vm_name}[/cyan]' is not running.[/]", style="yellow")
        else:
            if force:
                domain.destroy()  # Force shutdown
                console.print(f"[green]:stop_sign: Force stopped VM '[cyan]{vm_name}[/cyan]'.[/]")
            else:
                domain.shutdown()  # Graceful shutdown
                console.print(f"[green]:stop_sign: Initiated graceful shutdown of VM '[cyan]{vm_name}[/cyan]'.[/]")
                
    except Exception as e:
        console.print(f"[bold red]:x: Error stopping VM:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if conn is not None:
            close_libvirt(conn)

@vm_app.command("cleanup-snapshots")
def cleanup_snapshots_command(
    vm_name: Annotated[str, typer.Argument(help="Name of the VM to cleanup snapshots for.")],
    keep_count: Annotated[int, typer.Option("--keep", help="Number of recent snapshots to keep.")] = 3,
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = config.vm.LIBVIRT_URI
):
    """Clean up old snapshot files for a virtual machine."""
    conn = None
    try:
        conn = connect_libvirt(libvirt_uri)
        domain = find_vm(conn, vm_name)
        
        from utils.snapshot_manager import SnapshotManager
        manager = SnapshotManager()
        manager._cleanup_old_snapshots(domain, keep_count)
        
        console.print(f"[green]:heavy_check_mark: Cleaned up old snapshots for VM '[cyan]{vm_name}[/cyan]' (kept {keep_count} recent).[/]")
        
    except PracticeToolError as e:
        console.print(f"[bold red]:x: Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if conn is not None:
            close_libvirt(conn)
@vm_app.command("status")
def vm_status_command(
    vm_name: Annotated[str, typer.Argument(help="Name of the VM to check.")],
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = config.vm.LIBVIRT_URI
):
    """Show virtual machine status and information."""
    conn = None
    try:
        conn = connect_libvirt(libvirt_uri)
        domain = find_vm(conn, vm_name)
        
        # Get basic VM information
        is_active: bool = bool(domain.isActive())
        state_str = "Running" if is_active else "Stopped"
        
        if RICH_AVAILABLE:
            info_table = Table.grid(padding=(0, 2))
            info_table.add_column(style="bold")
            info_table.add_column()
            
            info_table.add_row("VM Name:", f"[cyan]{vm_name}[/]")
            info_table.add_row("Status:", f"[green]{state_str}[/]" if is_active else f"[red]{state_str}[/]")
            
            if is_active:
                # Try to get IP address
                try:
                    vm_ip = get_vm_ip(conn, domain)
                    if vm_ip:
                        info_table.add_row("IP Address:", f"[blue]{vm_ip}[/]")
                except Exception:
                    info_table.add_row("IP Address:", "[dim]Unable to detect[/]")
            
            console.print(Panel(info_table, title=f"VM Status: {vm_name}", border_style="blue"))
        else:
            console.print(f"VM Name: {vm_name}")
            console.print(f"Status: {state_str}")
            
    except PracticeToolError as e:
        console.print(f"[bold red]:x: Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if conn is not None:
            close_libvirt(conn)


@vm_app.command("snapshots")
def list_vm_snapshots(
    vm_name: Annotated[str, typer.Argument(help="Name of the VM to list snapshots for.")],
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = config.vm.LIBVIRT_URI
):
    """List all snapshots for a virtual machine."""
    conn = None
    try:
        conn = connect_libvirt(libvirt_uri)
        domain = find_vm(conn, vm_name)
        list_snapshots(domain)
        
    except PracticeToolError as e:
        console.print(f"[bold red]:x: Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if conn is not None:
            close_libvirt(conn)


@vm_app.command("revert")
def revert_vm_snapshot(
    vm_name: Annotated[str, typer.Argument(help="Name of the VM to revert.")],
    snapshot_name: Annotated[str, typer.Argument(help="Name of the snapshot to revert to.")],
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = config.vm.LIBVIRT_URI
):
    """Revert a virtual machine to a specific snapshot."""
    conn = None
    try:
        conn = connect_libvirt(libvirt_uri)
        domain = find_vm(conn, vm_name)
        
        success = revert_to_snapshot(domain, snapshot_name)
        if success:
            console.print(f"[green]:heavy_check_mark: Successfully reverted VM '[cyan]{vm_name}[/cyan]' to snapshot '[cyan]{snapshot_name}[/cyan]'.[/]")
        
    except PracticeToolError as e:
        console.print(f"[bold red]:x: Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if conn is not None:
            close_libvirt(conn)


# --- Utility Commands ---

@app.command()
def setup_user(
    vm_name: Annotated[str, typer.Option("--vm", help="Name of the libvirt VM to use.")] = config.vm.DEFAULT_VM_NAME,
    new_user: Annotated[str, typer.Option("--new-user", help="Username to set up on the VM.")] = config.ssh.DEFAULT_SSH_USER,
    admin_user: Annotated[str, typer.Option("--admin-user", help="An existing sudoer user on the VM.")] = "ubuntu",
    admin_key: Annotated[Path, typer.Option("--admin-key", help="Path to SSH private key for admin user.")] = config.ssh.DEFAULT_SSH_KEY_PATH,
    public_key_path: Annotated[Path, typer.Option("--pub-key", help="Path to PUBLIC SSH key to install.", 
        exists=True, file_okay=True, readable=True)] = Path("~/.ssh/id_ed25519.pub").expanduser(),
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = config.vm.LIBVIRT_URI
):
    """Set up a new user account on the VM with SSH access."""
    conn = None
    try:
        # Validate admin SSH key
        admin_key_path = validate_ssh_key(admin_key)
        
        # Read public key content
        try:
            public_key_content = public_key_path.read_text().strip()
        except Exception as e:
            console.print(f"[bold red]:x: Error reading public key file:[/bold red] {e}", style="red")
            raise typer.Exit(code=1)
        
        console.rule(f"[bold]Setting up user '[cyan]{new_user}[/cyan]' on VM '[cyan]{vm_name}[/cyan]'[/]", style="blue")
        
        # Connect to VM
        conn = connect_libvirt(libvirt_uri)
        domain = find_vm(conn, vm_name)
        
        if not domain.isActive():
            console.print(f":rocket: Starting VM '[cyan]{vm_name}[/cyan]'...")
            start_vm(domain)
        
        vm_ip = get_vm_ip(conn, domain)
        if not vm_ip:
            raise PracticeToolError("Could not determine VM IP address.")
        
        console.print(f"[green]:heavy_check_mark: VM accessible at [cyan]{vm_ip}[/cyan][/]")
        
        # User setup commands
        setup_commands = [
            f"sudo useradd -m -s /bin/bash {new_user}",
            f"sudo mkdir -p /home/{new_user}/.ssh",
            f"echo '{public_key_content}' | sudo tee /home/{new_user}/.ssh/authorized_keys",
            f"sudo chmod 700 /home/{new_user}/.ssh",
            f"sudo chmod 600 /home/{new_user}/.ssh/authorized_keys", 
            f"sudo chown -R {new_user}:{new_user} /home/{new_user}/.ssh",
            f"sudo usermod -aG sudo {new_user}"
        ]
        
        for i, command in enumerate(setup_commands, 1):
            console.print(f"[dim]Step {i}/{len(setup_commands)}: {command}[/]")
            result = run_ssh_command(vm_ip, admin_user, admin_key_path, command)
            
            if not result.get('success', False):
                error_details = result.get('stderr', 'Unknown error')
                console.print(f"[bold red]:x: Setup failed at step {i}:[/bold red] {error_details}", style="red")
                raise typer.Exit(code=1)
        
        console.print(f"\n[green]:heavy_check_mark: User '[cyan]{new_user}[/cyan]' successfully set up on VM![/]")
        console.print(f"[blue]Test connection:[/] ssh -i {admin_key_path} {new_user}@{vm_ip}")
        
    except PracticeToolError as e:
        console.print(f"[bold red]:x: Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if conn is not None:
            close_libvirt(conn)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    app()


# Export the main application for use in main.py
__all__ = ['app', 'vm_controller']