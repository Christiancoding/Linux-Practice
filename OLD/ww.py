#!/usr/bin/env python3

# --- Part 1: Standard Library Imports ---
import json
import os
import re
import shlex
import socket
import stat  # For checking file permissions
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# --- Part 2: Third-Party Library Imports & Checks ---
try:
    import libvirt
except ImportError:
    print("Error: Missing required library 'libvirt-python'.\n"
          "Please install it (e.g., 'pip install libvirt-python' or via system package manager) and try again.", file=sys.stderr)
    sys.exit(1)

try:
    import paramiko
except ImportError:
    print("Error: Missing required library 'paramiko'.\n"
          "Please install it (e.g., 'pip install paramiko') and try again.", file=sys.stderr)
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("Error: Missing required library 'PyYAML'.\n"
          "Please install it (e.g., 'pip install pyyaml') and try again.", file=sys.stderr)
    sys.exit(1)

try:
    import typer
    from typing_extensions import Annotated
except ImportError:
    print("Error: Missing required library 'typer'.\n"
          "Please install it (e.g., 'pip install typer[all]') and try again.", file=sys.stderr)
    sys.exit(1)

# --- Part 3: Rich Library Integration (Optional UI Enhancements) ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Provide dummy classes/functions if rich is not available
    class Console:
        def print(self, *args, **kwargs): typer.echo(*args)
        def rule(self, title="", style=""): typer.echo(f"--- {title} ---")
        def print_exception(self, *args, **kwargs): traceback.print_exc()
    class Panel:
        def __init__(self, content, title="", border_style="dim", expand=True, **kwargs):
            self.content = content
            self.title = title
        def __rich_console__(self, console, options):
             yield f"--- {self.title} ---"
             yield str(self.content)
             yield f"--- End {self.title} ---"
    class Table:
        def __init__(self, title="", **kwargs): self.title=title; self._rows = []; self._columns = []
        def add_column(self, header, **kwargs): self._columns.append(header)
        def add_row(self, *items): self._rows.append(items)
        def __rich_console__(self, console, options):
             if self.title: yield f"--- {self.title} ---"
             if self._columns: yield " | ".join(self._columns)
             yield "-" * (sum(len(str(c)) for c in self._columns) + (len(self._columns) * 3 - 1)) # Separator
             for row in self._rows: yield " | ".join(map(str, row))
             if self.title: yield f"--- End {self.title} ---"
    class Syntax:
         def __init__(self, code, lexer, theme="default", line_numbers=False, word_wrap=False): self.code = code
         def __rich_console__(self, console, options): yield self.code
    class Markdown:
         def __init__(self, markup): self.markup = markup
         def __rich_console__(self, console, options): yield self.markup
    class Text:
         def __init__(self, text, style=""): self.text = text; self.style = style
         def __rich_console__(self, console, options): yield self.text
         @staticmethod
         def assemble(*args): return "".join(str(item[0]) if isinstance(item, tuple) else str(item) for item in args)
    class Confirm:
        @staticmethod
        def ask(prompt, default=False):
            response = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
            if not response: return default
            return response == 'y'
    class Prompt:
        @staticmethod
        def ask(prompt, default=""):
            return input(f"{prompt}: ")
    class Progress: # Dummy Progress
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def add_task(self, description, total=None): return 0 # Return dummy task ID
        def update(self, task_id, **kwargs): pass
        @property
        def finished(self): return True # Always finished for dummy

# --- Part 4: Console Initialization & Custom Exceptions ---
# --- Initialize Rich Console ---
# Set highlight=False to avoid potential conflicts with typer coloring/markup
# Use stderr=True if you want logs/errors to go to stderr separately
console = Console(highlight=False, stderr=False)

# --- Custom Exceptions ---
class PracticeToolError(Exception):
    """Base exception for CLI operational errors."""
    pass

class LibvirtConnectionError(PracticeToolError):
    """Error connecting to libvirt."""
    pass

class VMNotFoundError(PracticeToolError):
    """VM definition not found in libvirt."""
    pass

class SnapshotOperationError(PracticeToolError):
    """Error during snapshot creation, revert, or deletion."""
    pass

class AgentCommandError(PracticeToolError):
    """Error communicating with the QEMU Guest Agent."""
    pass

class NetworkError(PracticeToolError):
    """Network-related errors (IP retrieval, SSH connection)."""
    pass

class SSHCommandError(PracticeToolError):
    """Error executing a command via SSH."""
    pass

class ChallengeLoadError(PracticeToolError):
    """Error loading or validating challenge definitions."""
    pass

class ChallengeValidationError(Exception):
    """Validation failed, containing specific reasons."""
    def __init__(self, reasons: list):
        self.reasons = reasons
        super().__init__(f"Validation failed: {'; '.join(reasons)}")

# --- Part 5: Constants and Configuration ---
# Group related constants for better organization
class Config:
    # VM Defaults
    DEFAULT_VM_NAME: str = "ubuntu24.04-2"
    DEFAULT_SNAPSHOT_NAME: str = "practice_external_snapshot"
    VM_READINESS_TIMEOUT_SECONDS: int = 120
    VM_READINESS_POLL_INTERVAL_SECONDS: int = 5
    VM_SHUTDOWN_TIMEOUT_SECONDS: int = 120

    # SSH Defaults
    DEFAULT_SSH_USER: str = "roo" # !! IMPORTANT: Update if needed !!
    DEFAULT_SSH_KEY_PATH: Path = Path("~/.ssh/id_ed25519").expanduser() # !! IMPORTANT: Update if needed !!
    SSH_CONNECT_TIMEOUT_SECONDS: int = 10
    SSH_COMMAND_TIMEOUT_SECONDS: int = 30
    SSH_KEY_PERMISSIONS_MASK: int = 0o077 # Permissions check: only owner should have access

    # Challenge Defaults
    DEFAULT_CHALLENGES_DIR: Path = Path("./challenges")
    DEFAULT_CHALLENGE_SCORE: int = 100

    # Libvirt Connection URI
    LIBVIRT_URI: str = 'qemu:///system'

    # Exit Codes for systemctl status checks
    EXIT_CODE_ACTIVE: int = 0
    EXIT_CODE_INACTIVE: int = 3
    EXIT_CODE_FAILED_BASE: int = 1 # Any non-zero, non-inactive usually means failure/not-found etc.
    EXIT_CODE_ENABLED: int = 0
    EXIT_CODE_DISABLED: int = 1

# Use getattr for safe access to libvirt error codes if they might be missing
VIR_ERR_NO_DOMAIN = getattr(libvirt, 'VIR_ERR_NO_DOMAIN', -1)
VIR_ERR_NO_DOMAIN_SNAPSHOT = getattr(libvirt, 'VIR_ERR_NO_DOMAIN_SNAPSHOT', -1)
VIR_ERR_OPERATION_INVALID = getattr(libvirt, 'VIR_ERR_OPERATION_INVALID', -1)
VIR_ERR_AGENT_UNRESPONSIVE = getattr(libvirt, 'VIR_ERR_AGENT_UNRESPONSIVE', -1)
VIR_ERR_OPERATION_TIMEOUT = getattr(libvirt, 'VIR_ERR_OPERATION_TIMEOUT', -1)
VIR_ERR_ARGUMENT_UNSUPPORTED = getattr(libvirt, 'VIR_ERR_ARGUMENT_UNSUPPORTED', -1)
VIR_ERR_CONFIG_EXIST = getattr(libvirt, 'VIR_ERR_CONFIG_EXIST', -1)
VIR_ERR_INVALID_DOMAIN = getattr(libvirt, 'VIR_ERR_INVALID_DOMAIN', -1)

# --- Part 6: Challenge Template Definition ---
# (Keep the existing CHALLENGE_TEMPLATE string here - it's large and static)
CHALLENGE_TEMPLATE = """
# --- Challenge Definition File ---
# See documentation or existing challenges for examples.
# SECURITY WARNING: 'run_command' executes commands via SSH on the target VM.
# Do not load challenges from untrusted sources without understanding the commands.

# Unique identifier for the challenge (e.g., configure-ssh-keys)
id: my-new-challenge

# Human-readable name for the challenge
name: "My New Challenge Title"

# Detailed description of the objective for the user (Markdown supported)
description: |
  Explain what the user needs to accomplish here.
  * Use lists.
  * Use `code`.
  * **Bold** and _italics_.

# Category for grouping challenges (e.g., Networking, Security, File Management)
category: "Uncategorized"

# Difficulty level (e.g., Easy, Medium, Hard, Expert)
difficulty: "Medium"

# Potential score for completing the challenge successfully (before hint costs)
score: 100

# List of relevant Linux concepts or commands involved
# concepts:
#   - ssh
#   - ssh-keygen
#   - systemctl

# Optional: Setup steps executed *before* the user interacts with the VM.
# Used to put the VM into the correct starting state for the challenge.
# WARNING: Commands run here execute on the VM via SSH. Use with extreme caution.
#          Prefer declarative steps (copy_file, ensure_service_status) if possible.
setup:
  - type: run_command
    # Example: Ensure a package needed for the challenge is installed
    # command: "sudo apt-get update && sudo apt-get install -y --no-install-recommends some-package"
    command: "echo 'Setup step 1: Placeholder command executed on VM'"
  # - type: copy_file # Needs implementation using Paramiko SFTP
  #   source: "files/needed_config.txt" # Path relative to challenge file
  #   destination: "/etc/needed_config.txt" # Absolute path on VM
  #   owner: "root" # Optional: user name or uid
  #   group: "root" # Optional: group name or gid
  #   mode: "0644" # Optional: octal mode string
  # - type: ensure_service_status
  #   service: "nginx"
  #   state: "stopped" # 'started', 'stopped', 'restarted'
  #   enabled: false # Optional: true, false

# Optional: A command that simulates the user performing the correct action.
# Useful for testing validation logic with the --simulate flag.
# WARNING: Command runs on the VM via SSH.
user_action_simulation: "echo 'User action simulation: Placeholder command executed on VM'"

# Required: Validation steps executed *after* the user performs the action.
# These determine if the challenge objective was met.
validation:
  - type: run_command # Check command output/exit status
    command: "hostname" # Example: check hostname
    success_criteria:
      exit_status: 0 # Default is 0 if success_criteria is omitted
      # stdout_contains: "practice-vm" # Check if stdout includes this string
      # stdout_equals: "expected_exact_output" # Check for exact stdout match
      # stdout_matches_regex: "^Welcome to .*$" # Check if stdout matches regex
      # stderr_empty: true # Check if stderr is empty
      # stderr_contains: "Warning:" # Check if stderr contains string
  - type: check_service_status
    service: "ssh"
    expected_status: "active" # active | inactive | failed
    # check_enabled: true # Optional: Check if service is enabled at boot
  - type: check_port_listening
    port: 22
    protocol: "tcp" # tcp | udp
    expected_state: true # true (listening) | false (not listening)
  - type: check_file_exists
    path: "/home/roo/.ssh/authorized_keys"
    expected_state: true # true (exists) | false (does not exist)
    file_type: "file" # any | file | directory
    # owner: "roo" # Optional: Check owner username or uid
    # group: "roo" # Optional: Check group name or gid
    # permissions: "0600" # Optional: Check exact octal permissions
  - type: check_file_contains
    path: "/etc/motd"
    text: "Welcome" # Mutually exclusive with matches_regex
    # matches_regex: "^Welcome to .*$" # Mutually exclusive with text
    expected_state: true # true (contains) | false (does not contain)

# Optional: Hints displayed to the user upon request.
hints:
  - text: "First hint: Point towards a general concept or tool."
    cost: 0 # Score cost for viewing this hint
  - text: "Second hint: Suggest a specific command or file to look at."
    cost: 10
  - text: "Third hint: Give more specific guidance or mention a common mistake."
    cost: 20

# Optional: A 'flag' string displayed upon successful completion.
# If omitted, a generic success message is shown.
# flag: "CTF{My_Challenge_Completed_Successfully}"
"""

# --- Part 7: Libvirt Helper Functions ---
def connect_libvirt() -> libvirt.virConnect:
    """Connects to libvirt specified by Config.LIBVIRT_URI."""
    try:
        conn = libvirt.open(Config.LIBVIRT_URI)
        if conn is None:
            raise LibvirtConnectionError(f'Failed to open connection to {Config.LIBVIRT_URI}')
        console.print(f"[bold green]:heavy_check_mark: Successfully connected to libvirt ({Config.LIBVIRT_URI})[/]")
        return conn
    except libvirt.libvirtError as e:
        raise LibvirtConnectionError(f'Error connecting to libvirt ({Config.LIBVIRT_URI}): {e}') from e

def find_vm(conn: libvirt.virConnect, vm_name: str) -> libvirt.virDomain:
    """Finds a VM domain by name."""
    if not conn:
        raise LibvirtConnectionError("Libvirt connection is not valid.")
    try:
        domain = conn.lookupByName(vm_name)
        state, _ = domain.state()
        state_str = "[green]Running[/]" if state == libvirt.VIR_DOMAIN_RUNNING else "[yellow]Inactive[/]"
        id_str = f"(ID: {domain.ID()})" if state == libvirt.VIR_DOMAIN_RUNNING else ""
        console.print(f":mag: Found VM: [bold cyan]{vm_name}[/] {id_str} - State: {state_str}")
        return domain
    except libvirt.libvirtError as e:
        if e.get_error_code() == VIR_ERR_NO_DOMAIN and VIR_ERR_NO_DOMAIN != -1:
             raise VMNotFoundError(f"VM '{vm_name}' not found. Please ensure it is defined in libvirt.") from e
        raise PracticeToolError(f"Error finding VM '{vm_name}': {e}") from e
    except Exception as e: # Catch unexpected errors
        raise PracticeToolError(f"An unexpected error occurred while finding VM '{vm_name}': {e}") from e

def close_libvirt(conn: Optional[libvirt.virConnect]):
    """Safely closes the libvirt connection."""
    if conn:
        try:
            conn.close()
            console.print("[dim]Libvirt connection closed.[/]")
        except libvirt.libvirtError as e:
            # Non-critical, just print a warning
            console.print(f"[yellow]:warning: Error closing libvirt connection:[/yellow] {e}", style="yellow")

# --- Part 8: Core VM Lifecycle Functions ---
def list_vms(conn: libvirt.virConnect):
    """Lists all defined VMs (active and inactive) using Rich Table."""
    if not conn:
        console.print("[bold red]:x: Error: Invalid libvirt connection passed to list_vms.[/]", style="red")
        return

    table = Table(title="[bold blue]Available Libvirt VMs[/]", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("State", justify="center")
    table.add_column("ID", justify="right")

    try:
        # Active VMs
        active_domains_ids = conn.listDomainsID()
        active_domains = [conn.lookupByID(dom_id) for dom_id in active_domains_ids] if active_domains_ids else []
        for domain in active_domains:
             table.add_row(domain.name(), "[green]Running[/]", str(domain.ID()))

        # Inactive VMs
        inactive_domains_names = conn.listDefinedDomains()
        if inactive_domains_names:
            for name in inactive_domains_names:
                # Avoid listing active VMs again if listDefinedDomains includes them
                if name not in [d.name() for d in active_domains]:
                    table.add_row(name, "[yellow]Shut off[/]", "[dim]N/A[/]")

        if not active_domains and not inactive_domains_names:
             console.print("  [i]No VMs found.[/]")
             return

        console.print(table)

    except libvirt.libvirtError as e:
        raise PracticeToolError(f"Error listing VMs from libvirt: {e}") from e

def start_vm(domain: libvirt.virDomain) -> bool:
    """Starts the specified VM domain."""
    if not domain:
        raise PracticeToolError("Invalid VM domain provided to start_vm.")
    try:
        if domain.isActive():
            console.print(f":information_source: VM '[bold cyan]{domain.name()}[/]' is already running.")
            return True
        else:
            console.print(f":rocket: Starting VM '[bold cyan]{domain.name()}[/]'...")
            if domain.create() < 0:
                 # create() returns -1 on failure and raises libvirtError sometimes
                 raise PracticeToolError(f"Libvirt failed to start VM '{domain.name()}' (check libvirt logs).")

            # Wait briefly for state change using Rich spinner
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                transient=True, # Clear spinner on exit
                console=console # Ensure it uses the same console
            ) as progress:
                progress.add_task(f"Waiting for '{domain.name()}' state...", total=None)
                time.sleep(4) # Give it a moment

            # Re-check state more definitively
            state, _ = domain.state()
            if state == libvirt.VIR_DOMAIN_RUNNING:
                console.print(f"[green]:heavy_check_mark: VM '[bold cyan]{domain.name()}[/]' appears to be running (ID: {domain.ID()}).[/]")
                return True
            else:
                 # This is unlikely if domain.create() succeeded, but good to check
                 console.print(f"[yellow]:warning: VM '[bold cyan]{domain.name()}[/] state is {state} shortly after start command. Proceeding, but check VM status.[/]", style="yellow")
                 return True # Still return True as the start command likely succeeded

    except libvirt.libvirtError as e:
        raise PracticeToolError(f"Error starting VM '{domain.name()}': {e}") from e
    except Exception as e:
        raise PracticeToolError(f"An unexpected error occurred while starting VM '{domain.name()}': {e}") from e


def shutdown_vm(domain: libvirt.virDomain) -> bool:
    """Shuts down the specified VM domain using ACPI, falling back to destroy."""
    if not domain:
        raise PracticeToolError("Invalid VM domain provided to shutdown_vm.")
    try:
        if not domain.isActive():
            console.print(f":information_source: VM '[bold cyan]{domain.name()}[/]' is already shut down.")
            return True
        else:
            console.print(f":stop_button: Attempting graceful shutdown for VM '[bold cyan]{domain.name()}[/]' (ACPI)...")
            shutdown_failed = False
            try:
                # shutdown() returns 0 on success, -1 on error
                if domain.shutdown() < 0:
                    shutdown_failed = True
                    console.print(f"  [yellow]:warning: ACPI shutdown command failed for VM '{domain.name()}'. Will try destroy later if needed.[/]", style="yellow")
                else:
                    console.print("  [dim]ACPI shutdown signal sent.[/]")
            except libvirt.libvirtError as e:
                 # Sometimes shutdown() raises error instead of returning -1
                 shutdown_failed = True
                 console.print(f"  [yellow]:warning: Error sending ACPI shutdown signal for VM '{domain.name()}': {e}. Will try destroy later if needed.[/]", style="yellow")

            # Wait for shutdown with Rich Progress bar only if ACPI signal was sent (or seemed to be)
            if not shutdown_failed:
                max_wait_sec = Config.VM_SHUTDOWN_TIMEOUT_SECONDS
                wait_interval = 3
                console.print(f"  [dim]Waiting up to {max_wait_sec}s for graceful shutdown...[/]")
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    transient=False, # Keep progress bar visible after completion
                    console=console
                ) as progress:
                    task = progress.add_task(f"Shutting down '{domain.name()}'...", total=max_wait_sec)
                    start_time = time.time()
                    while (time.time() - start_time) < max_wait_sec:
                        try:
                            if not domain.isActive():
                                progress.update(task, completed=max_wait_sec, description=f"VM '{domain.name()}' shut down.")
                                break # Exit loop early
                            current_state, _ = domain.state()
                            progress.update(task, advance=wait_interval, description=f"Shutting down '{domain.name()}'... State: {current_state}")
                            time.sleep(wait_interval)
                        except libvirt.libvirtError as e:
                            # Handle case where VM disappears during wait
                            if e.get_error_code() == VIR_ERR_NO_DOMAIN and VIR_ERR_NO_DOMAIN != -1:
                                progress.update(task, completed=max_wait_sec, description=f"VM '{domain.name()}' disappeared (assumed shut down)")
                                console.print("\n  [yellow]VM disappeared during shutdown wait.[/]", style="yellow")
                                return True # Treat as success
                            # If it's not a "no domain" error, re-raise to outer handler
                            raise
                    else: # Loop finished without breaking (timeout)
                        progress.update(task, description=f"VM '{domain.name()}' still active after timeout.")

            # Check final state and force destroy if needed
            if domain.isActive():
                console.print(f"[yellow]:warning: VM '[bold cyan]{domain.name()}[/]' did not shut down gracefully. Forcing power off (destroy)...[/]", style="yellow")
                if domain.destroy() < 0:
                    raise PracticeToolError(f"Failed to destroy (force power off) VM '{domain.name()}' after timeout/failure.")
                else:
                    console.print(f"  [green]:heavy_check_mark: VM '[bold cyan]{domain.name()}[/] destroyed (forced power off).[/]")
                    time.sleep(2) # Brief pause after destroy
                    return True # Destroy succeeded
            else:
                console.print(f"[green]:heavy_check_mark: VM '[bold cyan]{domain.name()}[/] shut down successfully.[/]")
                return True # Graceful shutdown succeeded

    except libvirt.libvirtError as e:
        err_code = e.get_error_code()
        # Handle cases where the VM is already gone or shutdown fails due to invalid state
        if err_code == VIR_ERR_NO_DOMAIN and VIR_ERR_NO_DOMAIN != -1:
             console.print(f"[yellow]:information_source: VM '{domain.name()}' disappeared or is already shut down.[/]", style="yellow")
             return True
        if err_code == VIR_ERR_OPERATION_INVALID and VIR_ERR_OPERATION_INVALID != -1:
            try:
                # Double-check if it's really inactive
                if not domain.isActive():
                    console.print(f"[yellow]:information_source: VM '{domain.name()}' is already shut down (operation invalid).[/]", style="yellow")
                    return True
            except libvirt.libvirtError: # If check fails, assume gone
                 console.print(f"[yellow]:information_source: VM '{domain.name()}' disappeared or is already shut down.[/]", style="yellow")
                 return True
        # If it wasn't an expected "already off" error, raise it
        raise PracticeToolError(f"Error during shutdown process for VM '{domain.name()}': {e}") from e
    except Exception as e:
        raise PracticeToolError(f"An unexpected error occurred while shutting down VM '{domain.name()}': {e}") from e

# --- Part 9: QEMU Guest Agent Functions ---
def qemu_agent_command(domain: libvirt.virDomain, command_json_str: str, timeout_sec: int = 10) -> Optional[Any]:
    """Sends a command to the QEMU guest agent and returns the parsed JSON response."""
    if not domain: return None # Should not happen if called correctly
    if not domain.isActive():
        # console.print("[yellow]QEMU Agent:[/yellow] VM is not running.", style="yellow") # Less verbose
        return None

    try:
        if not hasattr(domain, 'qemuAgentCommand'):
            # console.print("[yellow]QEMU Agent:[/yellow] qemuAgentCommand not supported by this libvirt version or setup.", style="yellow")
            return None # Treat as agent unavailable

        # console.print(f"[dim]QEMU Agent Command: {command_json_str}[/]") # Debug
        response_str = domain.qemuAgentCommand(command_json_str, timeout_sec, 0)
        # console.print(f"[dim]QEMU Agent Response: {response_str}[/]") # Debug

        if response_str is None:
            # Sometimes None indicates success for commands with no return value (like fsfreeze)
            # We will treat None as potential success but log if unexpected.
            # console.print("[dim]QEMU Agent: Received None response (might be OK).[/]")
            return {} # Return empty dict to signify command sent, no error, no data

        # Attempt to parse JSON response
        try:
            response_json = json.loads(response_str)
            if isinstance(response_json, dict) and response_json.get("error"):
                 error_details = response_json["error"].get("desc", "Unknown error")
                 error_class = response_json["error"].get("class", "GenericError")
                 console.print(f"[yellow]QEMU Agent:[/yellow] Guest agent reported error: {error_class} - {error_details}", style="yellow")
                 return None # Indicate agent-level error
            return response_json
        except json.JSONDecodeError:
            console.print(f"[yellow]QEMU Agent:[/yellow] Could not decode JSON response: {response_str}", style="yellow")
            return None # Indicate communication/format error

    except libvirt.libvirtError as e:
        err_code = e.get_error_code()
        # Be less verbose for common/expected failures during startup etc.
        if err_code in (VIR_ERR_AGENT_UNRESPONSIVE, VIR_ERR_OPERATION_TIMEOUT, VIR_ERR_OPERATION_INVALID, VIR_ERR_ARGUMENT_UNSUPPORTED):
            # console.print(f"[dim]QEMU Agent: Command failed (Code {err_code}, Reason: {e}). Expected during boot/setup sometimes.[/]")
            pass # Silently fail if common error code
        else:
            console.print(f"[yellow]QEMU Agent:[/yellow] Libvirt error running agent command (Code {err_code}): {e}", style="yellow")
        return None # Indicate libvirt-level error
    except Exception as e:
        console.print(f"[red]QEMU Agent:[/red] An unexpected error occurred running agent command: {e}", style="red")
        return None

def qemu_agent_fsfreeze(domain: libvirt.virDomain) -> bool:
    """Attempts to freeze VM filesystems using the QEMU guest agent."""
    console.print(":snowflake: Attempting filesystem freeze via QEMU agent...")
    response = qemu_agent_command(domain, '{"execute": "guest-fsfreeze-freeze"}')

    # Check response: None means communication error or agent error.
    # An empty dict {} means command sent, no error reported, no data returned (often success for fsfreeze).
    # A dict with {'return': X} is explicit success.
    if response is None:
        console.print("  [yellow]:warning: QEMU Agent: Filesystem freeze command failed or agent unresponsive/error.[/]", style="yellow")
        return False
    elif isinstance(response, dict): # Includes {} or {'return': ...}
        frozen_count = response.get('return', 0) # Default to 0 if 'return' key is missing (like in {})
        if frozen_count >= 0:
             console.print(f"  [green]:heavy_check_mark: QEMU Agent: Filesystems frozen successfully (Count: {frozen_count}).[/]")
             return True
        else:
             # Should not happen if response is a dict unless agent returns negative count?
             console.print(f"  [yellow]:warning: QEMU Agent: Filesystem freeze returned unexpected dict response: {response}[/]", style="yellow")
             return False
    else: # Unexpected response type
        console.print(f"  [yellow]:warning: QEMU Agent: Filesystem freeze returned unexpected response type: {type(response)} {response}[/]", style="yellow")
        return False

def qemu_agent_fsthaw(domain: libvirt.virDomain) -> bool:
    """Attempts to thaw VM filesystems using the QEMU guest agent."""
    console.print(":fire: Attempting filesystem thaw via QEMU agent...")
    response = qemu_agent_command(domain, '{"execute": "guest-fsfreeze-thaw"}')

    # Similar response interpretation as fsfreeze
    if response is None:
        console.print("  [yellow]:warning: QEMU Agent: Filesystem thaw command failed or agent unresponsive/error.[/]", style="yellow")
        return False
    elif isinstance(response, dict):
        thawed_count = response.get('return', 0)
        if thawed_count >= 0:
             console.print(f"  [green]:heavy_check_mark: QEMU Agent: Filesystems thawed successfully (Count: {thawed_count}).[/]")
             return True
        else:
             console.print(f"  [yellow]:warning: QEMU Agent: Filesystem thaw returned unexpected dict response: {response}[/]", style="yellow")
             return False
    else: # Unexpected response type
        console.print(f"  [yellow]:warning: QEMU Agent: Filesystem thaw returned unexpected response type: {type(response)} {response}[/]", style="yellow")
        return False

# --- Part 10: Snapshot Management Functions ---
def _generate_snapshot_xml(domain: libvirt.virDomain, snapshot_name: str, agent_frozen: bool) -> Tuple[str, List[str]]:
    """Generates the snapshot XML and returns XML string and list of snapshot disk file paths."""
    snapshot_disk_files = []
    try:
        raw_xml = domain.XMLDesc(0)
        tree = ET.fromstring(raw_xml)
        disks_xml = ""
        disk_count = 0
        # FIX: Removed 'console=console' from Table constructor
        disk_table = Table(title="Snapshot Disk Planning", show_header=True, header_style="magenta")
        disk_table.add_column("Target Dev")
        disk_table.add_column("Original Disk")
        disk_table.add_column("Snapshot Disk")

        for device in tree.findall('devices/disk'):
            disk_type = device.get('type')
            disk_device = device.get('device')
            # Only snapshot file-based disks used as 'disk' (not CDROM etc)
            if disk_type == 'file' and disk_device == 'disk':
                target_dev_node = device.find('target')
                if target_dev_node is None: continue # Skip disks without target
                target_dev = target_dev_node.get('dev')

                driver_node = device.find('driver')
                driver_type = driver_node.get('type') if driver_node is not None else 'qcow2' # Assume qcow2 if not specified

                source_file_node = device.find('source')
                if source_file_node is None or 'file' not in source_file_node.attrib:
                    console.print(f"[yellow]Warning:[/yellow] Disk '{target_dev}' has no source file defined, skipping snapshot for this disk.", style="yellow")
                    continue

                original_disk_path_str = source_file_node.get('file')
                original_disk_path = Path(original_disk_path_str).resolve() # Resolve to absolute path
                original_disk_dir = original_disk_path.parent

                if not original_disk_dir.is_dir():
                     # This is critical, libvirt might error out later
                     raise SnapshotOperationError(f"Directory '{original_disk_dir}' for base disk '{original_disk_path.name}' (target: {target_dev}) does not exist.")

                # Construct snapshot filename
                snapshot_disk_filename = f"{domain.name()}-{target_dev}-{snapshot_name}.qcow2"
                snapshot_disk_path = original_disk_dir / snapshot_disk_filename
                snapshot_disk_files.append(str(snapshot_disk_path)) # Store path as string for XML

                disk_table.add_row(target_dev, str(original_disk_path), str(snapshot_disk_path))
                disk_count += 1

                # Check if snapshot file already exists (libvirt might handle this, but good to check)
                if snapshot_disk_path.exists():
                    console.print(f"[yellow]Warning:[/yellow] Snapshot disk file '{snapshot_disk_path}' already exists. Libvirt will likely fail unless QUIESCE works perfectly or file is unlinked.", style="yellow")
                    # We will NOT attempt to remove it here, let libvirt manage it with ATOMIC flag.

                # Append XML for this disk
                disks_xml += f"""
                <disk name='{target_dev}' snapshot='external'>
                  <driver type='{driver_type}'/>
                  <source file='{str(snapshot_disk_path)}'/>
                </disk>
                """

        if disk_count > 0:
            console.print(disk_table) # Table is printed using the console here
        else:
             raise SnapshotOperationError("No suitable file-based disks found to snapshot.")

        if not disks_xml:
             # This should not happen if disk_count > 0, but defensive check
             raise SnapshotOperationError("Failed to generate disk XML for snapshot.")

        # Final snapshot XML structure
        snapshot_xml = f"""
        <domainsnapshot>
          <name>{snapshot_name}</name>
          <description>External snapshot for practice session (Agent Freeze: {agent_frozen})</description>
          <disks>
            {disks_xml}
          </disks>
        </domainsnapshot>
        """
        # console.print(Panel(Syntax(snapshot_xml, "xml", theme="default", line_numbers=True), title="Snapshot XML")) # Debug
        return snapshot_xml, snapshot_disk_files

    except ET.ParseError as e:
        raise SnapshotOperationError(f"Error parsing VM XML description: {e}") from e
    # Reraise SnapshotOperationError and PracticeToolError directly
    except (SnapshotOperationError, PracticeToolError) as e:
        raise e
    except Exception as e:
        # Catch any other unexpected errors during XML generation
        raise SnapshotOperationError(f"An unexpected error occurred generating snapshot XML: {e}") from e


def create_external_snapshot(domain: libvirt.virDomain, snapshot_name: str):
    """Creates an external snapshot, attempting agent-based freeze/thaw."""
    if not domain:
        raise PracticeToolError("Invalid VM domain provided to create_external_snapshot.")
    console.rule(f"[bold]Creating EXTERNAL Snapshot: [cyan]{snapshot_name}[/][/]", style="blue")

    was_frozen_by_agent = False
    snapshot_files_to_check: List[str] = []

    try:
        # 1. Filesystem Freeze (if VM is running)
        if domain.isActive():
            was_frozen_by_agent = qemu_agent_fsfreeze(domain)
            if was_frozen_by_agent:
                 time.sleep(2) # Give FS time to sync/settle after freeze signal
            else:
                 console.print("[yellow]:warning: Agent freeze failed or unavailable. Snapshot consistency depends on libvirt QUIESCE flag or app quiescing.[/]", style="yellow")
        else:
             console.print("[dim]VM not running, skipping agent filesystem freeze.[/]")

        # 2. Generate Snapshot XML
        snapshot_xml, snapshot_files_to_check = _generate_snapshot_xml(domain, snapshot_name, was_frozen_by_agent)

        # 3. Determine Snapshot Flags
        # Base flags: DISK_ONLY (no memory), ATOMIC (all disks or none)
        flags = libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY | libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_ATOMIC
        quiesce_flag_used = False

        # Add QUIESCE flag if agent freeze failed AND VM is running
        if domain.isActive() and not was_frozen_by_agent:
            if hasattr(libvirt, 'VIR_DOMAIN_SNAPSHOT_CREATE_QUIESCE'):
                flags |= libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_QUIESCE
                quiesce_flag_used = True
                console.print("  [dim](Using libvirt QUIESCE flag as agent freeze was skipped/failed)[/]")
            else:
                console.print("  [yellow](Libvirt QUIESCE flag not available, proceeding without it)[/]", style="yellow")

        # 4. Create Snapshot via Libvirt
        console.print(f"  Attempting snapshot creation (Flags: {flags})...")
        snapshot = domain.snapshotCreateXML(snapshot_xml, flags)
        # snapshotCreateXML raises libvirtError on failure

        if snapshot:
            console.print(f"[green]:camera_with_flash: Successfully created external snapshot metadata: '{snapshot.getName()}'[/]")
            # Optional: Check if snapshot disk files were actually created (useful for diagnosing storage issues)
            # for file_path in snapshot_files_to_check:
            #     if not Path(file_path).exists():
            #          console.print(f"[yellow]Warning:[/yellow] Snapshot disk file '{file_path}' was not found after successful metadata creation.", style="yellow")
            return True
        else:
            # Should not happen if snapshotCreateXML doesn't raise error, but defensive check
            raise SnapshotOperationError(f"Libvirt snapshotCreateXML returned None unexpectedly for '{snapshot_name}'.")


    except libvirt.libvirtError as e:
        err_code = e.get_error_code()
        if err_code == VIR_ERR_CONFIG_EXIST and VIR_ERR_CONFIG_EXIST != -1:
             # Make this a specific exception type
             raise SnapshotOperationError(f"Snapshot metadata '{snapshot_name}' already exists. Delete it first.") from e
        elif err_code == VIR_ERR_AGENT_UNRESPONSIVE and VIR_ERR_AGENT_UNRESPONSIVE != -1 and quiesce_flag_used:
             # Snapshot failed specifically because agent was required *even with* QUIESCE flag
             msg = f"Snapshot creation failed: Libvirt QUIESCE flag requires guest agent interaction, but agent was unresponsive ({e})"
             console.print(f"[bold red]Error:[/bold red] {msg}", style="red")
             raise SnapshotOperationError(msg) from e
        elif err_code == VIR_ERR_OPERATION_INVALID and VIR_ERR_OPERATION_INVALID != -1:
             # Often happens if trying to snapshot RAM with DISK_ONLY, or disk issues
             msg = f"Snapshot creation failed (Operation Invalid): Check snapshot flags and disk configuration. Libvirt error: {e}"
             console.print(f"[bold red]Error:[/bold red] {msg}", style="red")
             raise SnapshotOperationError(msg) from e
        else:
             # General libvirt error during creation
             raise SnapshotOperationError(f"Error creating external snapshot '{snapshot_name}': {e}") from e
    # Reraise SnapshotOperationError and PracticeToolError directly
    except (SnapshotOperationError, PracticeToolError) as e:
        raise e
    except Exception as e:
        # Catch any other unexpected errors
        raise SnapshotOperationError(f"An unexpected error occurred creating snapshot '{snapshot_name}': {e}") from e
    finally:
        # Thaw filesystem ONLY if freeze was successful
        if was_frozen_by_agent:
            if not qemu_agent_fsthaw(domain):
                 # Critical warning if thaw fails
                 console.print("[bold red]:rotating_light: CRITICAL:[/bold red] Filesystem thaw command failed after successful freeze. VM filesystems might be stuck frozen!", style="red")
                 console.print("  Manual intervention (e.g., 'fsfreeze -u /' inside VM or reboot) might be required.", style="red")
        console.rule(f"[bold]End Snapshot Creation[/]", style="blue")

def revert_to_snapshot(domain: libvirt.virDomain, snapshot_name: str):
    """Reverts the VM to a previously created snapshot."""
    if not domain:
        raise PracticeToolError("Invalid VM domain provided to revert_to_snapshot.")
    console.rule(f"[bold]Reverting to Snapshot: [cyan]{snapshot_name}[/][/]", style="blue")
    snapshot = None
    try:
        # 1. Lookup snapshot
        snapshot = domain.snapshotLookupByName(snapshot_name, 0) # Raises NO_DOMAIN_SNAPSHOT if not found

        # 2. Shutdown VM if running
        if domain.isActive():
             console.print(":warning: VM is running. Shutting down before reverting snapshot...")
             if not shutdown_vm(domain): # shutdown_vm handles errors internally
                  raise SnapshotOperationError("Failed to shut down VM before revert. Aborting.")
             time.sleep(3) # Allow state to settle
             if domain.isActive(): # Double check
                  raise SnapshotOperationError("VM failed to shut down completely before revert. Aborting.")
             console.print("  [dim]VM confirmed shut down.[/]")

        # 3. Attempt Revert
        # VIR_DOMAIN_SNAPSHOT_REVERT_FORCE might be needed for external snapshots if state is inconsistent
        flags = 0
        if hasattr(libvirt, 'VIR_DOMAIN_SNAPSHOT_REVERT_FORCE'):
            flags |= libvirt.VIR_DOMAIN_SNAPSHOT_REVERT_FORCE
            console.print("  [dim](Attempting revert with VIR_DOMAIN_SNAPSHOT_REVERT_FORCE flag)[/]")
        else:
            console.print("  [dim](VIR_DOMAIN_SNAPSHOT_REVERT_FORCE flag not available)[/]")

        console.print(f":rewind: Reverting using snapshot '{snapshot.getName()}' (Flags: {flags})...")
        # revertToSnapshot returns 0 on success, -1 on error
        if domain.revertToSnapshot(snapshot, flags) < 0:
            # Check libvirt logs for detailed reason
            raise SnapshotOperationError(f"Libvirt failed to revert VM '{domain.name()}' to snapshot '{snapshot_name}' (check libvirt logs).")

        console.print(f"[green]:heavy_check_mark: Successfully reverted VM '[bold cyan]{domain.name()}[/]' to snapshot '{snapshot_name}'.[/]")
        time.sleep(2) # Pause after revert

        # State after revert (usually off for external snapshot revert)
        if domain.isActive():
            console.print("[yellow]Warning:[/yellow] VM is running after disk-only revert, which might be unexpected.", style="yellow")
        else:
            console.print("[dim]VM is shut off after revert (expected).[/]")
        return True

    except libvirt.libvirtError as e:
        err_code = e.get_error_code()
        if err_code == VIR_ERR_NO_DOMAIN_SNAPSHOT and VIR_ERR_NO_DOMAIN_SNAPSHOT != -1:
             raise SnapshotOperationError(f"Snapshot '{snapshot_name}' not found. Cannot revert.") from e
        # Check for common specific error messages if needed
        elif "Invalid target domain state 'disk-snapshot'" in str(e):
             msg = f"Revert failed due to snapshot state issue (often from snapshotting a running VM without full quiesce): {e}"
             console.print(f"[yellow]Warning:[/yellow] {msg}", style="yellow")
             raise SnapshotOperationError(msg) from e
        else:
            # Generic libvirt error during revert
            snap_exists_after_fail = False
            if snapshot: # Check if snapshot still exists if lookup initially succeeded
                try: domain.snapshotLookupByName(snapshot_name, 0); snap_exists_after_fail = True
                except libvirt.libvirtError: pass
            raise SnapshotOperationError(f"Error reverting to snapshot '{snapshot_name}': {e}. Snapshot exists after fail: {snap_exists_after_fail}") from e
    # Reraise SnapshotOperationError and PracticeToolError directly
    except (SnapshotOperationError, PracticeToolError) as e:
        raise e
    except Exception as e:
        raise SnapshotOperationError(f"An unexpected error occurred while reverting to snapshot '{snapshot_name}': {e}") from e
    finally:
         console.rule(f"[bold]End Snapshot Revert[/]", style="blue")

def delete_external_snapshot(domain: libvirt.virDomain, snapshot_name: str):
    """Deletes an external snapshot, usually requiring the VM to be off."""
    if not domain:
        raise PracticeToolError("Invalid VM domain provided to delete_external_snapshot.")
    console.rule(f"[bold]Deleting Snapshot: [cyan]{snapshot_name}[/][/]", style="red")
    snapshot = None
    try:
        # 1. Lookup snapshot
        snapshot = domain.snapshotLookupByName(snapshot_name, 0) # Raises NO_DOMAIN_SNAPSHOT if not found

        # 2. Shutdown VM if running (Deletion often requires VM off, especially for block commit)
        if domain.isActive():
             console.print(":warning: VM is running. Shutting down before deleting snapshot...")
             if not shutdown_vm(domain):
                  raise SnapshotOperationError("Failed to shut down VM before deleting snapshot. Aborting.")
             time.sleep(3)
             if domain.isActive():
                  raise SnapshotOperationError("VM failed to shut down completely before delete. Aborting.")
             console.print("  [dim]VM confirmed shut down.[/]")

        # 3. Delete Snapshot
        # Flags=0: Default behavior, attempts metadata delete + block commit (merge).
        # VIR_DOMAIN_SNAPSHOT_DELETE_METADATA_ONLY: Safer for manual merge later.
        flags = 0
        console.print(f":wastebasket: Attempting to delete snapshot '{snapshot.getName()}' (Flags={flags}). This might involve merging data...")
        # snapshot.delete returns 0 on success, -1 on error
        if snapshot.delete(flags) < 0:
            raise SnapshotOperationError(f"Libvirt failed to delete snapshot '{snapshot_name}' (Flags={flags}). Check libvirt logs for details (e.g., block commit errors).")

        console.print(f"[green]:heavy_check_mark: Successfully initiated deletion of snapshot '{snapshot_name}'.[/]")
        console.print("[yellow]NOTE:[/yellow] Block commit (merging) might happen asynchronously. Verify disk chain if needed.")
        time.sleep(2)

        # 4. Verify Deletion (Check metadata)
        try:
             domain.snapshotLookupByName(snapshot_name, 0)
             # If lookup succeeds, metadata deletion hasn't completed or failed.
             console.print("[yellow]Warning:[/yellow] Snapshot metadata still exists shortly after deletion command. Deletion/merge might be ongoing or failed.", style="yellow")
        except libvirt.libvirtError as e_lookup:
             if e_lookup.get_error_code() == VIR_ERR_NO_DOMAIN_SNAPSHOT and VIR_ERR_NO_DOMAIN_SNAPSHOT != -1:
                  console.print("[dim]Snapshot metadata successfully deleted or deletion is in progress.[/]")
             else:
                  # Unexpected error during verification lookup
                  console.print(f"[yellow]Warning:[/yellow] Error checking snapshot status after delete command: {e_lookup}", style="yellow")
        return True

    except libvirt.libvirtError as e:
        err_code = e.get_error_code()
        if err_code == VIR_ERR_NO_DOMAIN_SNAPSHOT and VIR_ERR_NO_DOMAIN_SNAPSHOT != -1:
             console.print(f"[yellow]:information_source: Snapshot '{snapshot_name}' already deleted or never existed.[/]", style="yellow")
             return True # Not an error in this context
        # Other libvirt error during lookup or delete
        raise SnapshotOperationError(f"Error deleting snapshot '{snapshot_name}': {e}") from e
    # Reraise SnapshotOperationError and PracticeToolError directly
    except (SnapshotOperationError, PracticeToolError) as e:
        raise e
    except Exception as e:
        raise SnapshotOperationError(f"An unexpected error occurred while deleting snapshot '{snapshot_name}': {e}") from e
    finally:
        console.rule(f"[bold]End Snapshot Deletion[/]", style="red")


def list_snapshots(domain: libvirt.virDomain):
    """Lists all snapshots for the given VM domain using Rich Table."""
    if not domain:
        raise PracticeToolError("Invalid VM domain provided to list_snapshots.")

    # FIX: Removed 'console=console' from Table constructor
    table = Table(title=f"[bold blue]Snapshots for VM '[cyan]{domain.name()}[/]'[/]", show_header=True, header_style="bold magenta")
    table.add_column("Snapshot Name", style="cyan")
    table.add_column("Created", style="dim", justify="center")
    table.add_column("VM State", justify="center") # State *at time of snapshot*
    table.add_column("Type", justify="center")
    table.add_column("Description", justify="left")

    try:
        snapshot_names = domain.snapshotListNames(0)
        if not snapshot_names:
            console.print(Panel("[i]No snapshots found.[/]", title=f"Snapshots for {domain.name()}", border_style="dim", style="dim"))
            return

        for name in snapshot_names:
            details = "[dim]N/A[/]"
            creation_time_str = "[dim]N/A[/]"
            state_str = "[dim]N/A[/]"
            type_str = "[dim]Unknown[/]"
            try:
                snapshot = domain.snapshotLookupByName(name, 0) # Raises NO_DOMAIN_SNAPSHOT if gone
                xml_desc = snapshot.getXMLDesc(0)
                snap_tree = ET.fromstring(xml_desc)

                creation_time_node = snap_tree.find('creationTime')
                state_node = snap_tree.find('state')
                disks_node = snap_tree.find('disks')
                desc_node = snap_tree.find('description')
                memory_node = snap_tree.find('memory') # Check for memory snapshot

                is_external = disks_node is not None and any(
                    d.get('snapshot') == 'external' for d in disks_node.findall('disk')
                )
                has_memory = memory_node is not None and memory_node.get('snapshot', 'no') != 'no'

                if creation_time_node is not None and creation_time_node.text.isdigit():
                     try: creation_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(creation_time_node.text)))
                     except ValueError: pass # Handle potential large timestamps

                state_str = state_node.text if state_node is not None else '[dim]N/A[/]'
                type_str = f"{'External' if is_external else 'Internal'}{'+Mem' if has_memory else ''}"
                details = desc_node.text.strip() if desc_node is not None and desc_node.text else "[dim]No description[/]"

            except libvirt.libvirtError as e_lookup:
                if e_lookup.get_error_code() == VIR_ERR_NO_DOMAIN_SNAPSHOT and VIR_ERR_NO_DOMAIN_SNAPSHOT != -1:
                    details = "[yellow](Disappeared)[/]"
                else:
                    details = f"[red](Error looking up: {e_lookup})[/]"
            except ET.ParseError:
                 details = "[red](Error parsing XML)[/]"
            except Exception as detail_err:
                 details = f"[red](Unexpected error: {detail_err})[/]"
            finally:
                 table.add_row(name, creation_time_str, state_str, type_str, details)

        console.print(table)

    except libvirt.libvirtError as e:
        raise PracticeToolError(f"Error listing snapshots for VM '{domain.name()}': {e}") from e

# --- Part 11: Network and SSH Functions ---
def _get_vm_ip_address_agent(domain: libvirt.virDomain) -> Optional[str]:
    """Gets the VM IP address using the QEMU Guest Agent (internal helper)."""
    if not domain or not domain.isActive(): return None
    # Use interfaceAddresses if available (more direct than guest-network-get-interfaces)
    if hasattr(domain, 'interfaceAddresses') and hasattr(libvirt, 'VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT'):
        try:
            agent_flag = libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT
            interfaces = domain.interfaceAddresses(agent_flag, 0)
            if interfaces:
                for iface_name, iface_data in interfaces.items():
                    if iface_name == 'lo' or 'addrs' not in iface_data: continue
                    for addr_info in iface_data['addrs']:
                        if addr_info.get('type') == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                            ip_addr = addr_info.get('addr')
                            # Basic check to exclude link-local (169.254) and loopback (127.*)
                            if ip_addr and not ip_addr.startswith("169.254.") and not ip_addr.startswith("127."):
                                return ip_addr # Return first suitable IPv4 found
        except libvirt.libvirtError as e:
             err_code = e.get_error_code()
             if err_code not in [VIR_ERR_AGENT_UNRESPONSIVE, VIR_ERR_OPERATION_TIMEOUT, VIR_ERR_OPERATION_INVALID, VIR_ERR_ARGUMENT_UNSUPPORTED]:
                 console.print(f"  [yellow]Libvirt error querying agent interfaces: {e}[/]", style="yellow")
        except Exception as e:
             console.print(f"  [yellow]Unexpected error getting IP via agent (interfaceAddresses): {e}[/]", style="yellow")

    # Fallback: Try guest-network-get-interfaces command via agent
    response = qemu_agent_command(domain, '{"execute": "guest-network-get-interfaces"}')
    if isinstance(response, dict) and "return" in response and isinstance(response["return"], list):
        for iface in response["return"]:
            if iface.get("name") == "lo" or "ip-addresses" not in iface: continue
            for ip_info in iface["ip-addresses"]:
                if ip_info.get("ip-address-type") == "ipv4":
                    ip_addr = ip_info.get("ip-address")
                    if ip_addr and not ip_addr.startswith("169.254.") and not ip_addr.startswith("127."):
                        return ip_addr # Return first suitable IPv4 found
    return None


def _get_vm_ip_address_dhcp(conn: libvirt.virConnect, domain: libvirt.virDomain) -> Optional[str]:
    """Gets the VM IP address via Libvirt DHCP leases (internal helper)."""
    if not domain or not domain.isActive() or not conn: return None

    vm_mac: Optional[str] = None
    network_name: Optional[str] = None

    try:
        raw_xml = domain.XMLDesc(0)
        tree = ET.fromstring(raw_xml)

        # Find the MAC and network for the first 'network' type interface
        for iface in tree.findall('.//devices/interface[@type="network"]'):
            mac_node = iface.find('mac[@address]')
            source_node = iface.find('source[@network]')
            if mac_node is not None and source_node is not None:
                vm_mac = mac_node.get('address')
                network_name = source_node.get('network')
                if vm_mac and network_name: break # Use first one found

        if not vm_mac or not network_name: return None # No suitable interface found

        network = conn.networkLookupByName(network_name) # Raises error if not found
        if not network.isActive(): return None # Network not active

        # Get DHCP leases
        all_leases = []
        if hasattr(network, 'getAllDHCPLeases'): # Prefer newer method if available
            all_leases = network.getAllDHCPLeases(0)
        elif hasattr(network, 'DHCPLeases'): # Fallback
             # Older DHCPLeases might require MAC, try without first
             try: all_leases = network.DHCPLeases()
             except TypeError: # Might require MAC argument
                  try: all_leases = network.DHCPLeases(vm_mac, 0) # Pass MAC if needed
                  except libvirt.libvirtError: pass # Ignore if lease retrieval fails

        if not all_leases: return None

        # Find matching, active lease
        current_time = time.time()
        for lease in all_leases:
            if lease.get('mac', '').lower() == vm_mac.lower():
                ip_addr = lease.get('ipaddr')
                expiry_time = lease.get('expirytime')
                is_expired = expiry_time is not None and current_time > expiry_time
                if ip_addr and not is_expired:
                    return ip_addr # Found active lease
                elif ip_addr and is_expired:
                     console.print(f"  [dim]Found expired DHCP lease for {vm_mac}: IP={ip_addr}[/]", style="dim")

    except (libvirt.libvirtError, ET.ParseError, AttributeError, Exception) as e:
        # Log unexpected errors during DHCP check
        console.print(f"  [yellow]Error querying DHCP leases: {type(e).__name__} - {e}[/]", style="yellow")

    return None # No active lease found


def get_vm_ip(conn: libvirt.virConnect, domain: libvirt.virDomain) -> str:
    """Tries to get the VM IP, first using Agent, then DHCP leases."""
    console.print("\n:satellite: Obtaining VM IP Address...")
    ip: Optional[str] = None

    # Try Agent First (usually more reliable if available)
    with Progress(SpinnerColumn(spinner_name="point"), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
        task = progress.add_task("Querying QEMU Agent for IP...", total=None)
        ip = _get_vm_ip_address_agent(domain)
        progress.update(task, description=f"Agent query complete (IP {'found' if ip else 'not found'}).")

    if ip:
        console.print(f"  [green]:heavy_check_mark: Found IP via QEMU Agent:[/green] [bold magenta]{ip}[/]")
        return ip
    else:
        console.print("  [dim]Agent IP retrieval failed or unavailable. Trying DHCP leases...[/]")
        # Try DHCP Leases as Fallback
        with Progress(SpinnerColumn(spinner_name="point"), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            task = progress.add_task("Checking Libvirt DHCP leases...", total=None)
            ip = _get_vm_ip_address_dhcp(conn, domain)
            progress.update(task, description=f"DHCP query complete (IP {'found' if ip else 'not found'}).")

        if ip:
             console.print(f"  [green]:heavy_check_mark: Found IP via DHCP Lease:[/green] [bold magenta]{ip}[/]")
             return ip
        else:
             # Both methods failed
             raise NetworkError("Failed to obtain VM IP address using both QEMU Agent and DHCP leases. Check VM network config and guest services.")

def _validate_ssh_key(key_path: Path) -> Path:
    """Validates SSH private key existence and permissions."""
    resolved_path = key_path.expanduser().resolve()
    if not resolved_path.is_file():
        raise PracticeToolError(f"SSH key file not found: {resolved_path}")

    # Check permissions (basic check: should not be world/group readable/writable)
    try:
        key_stat = resolved_path.stat()
        permissions = stat.S_IMODE(key_stat.st_mode)
        if permissions & Config.SSH_KEY_PERMISSIONS_MASK: # Checks group/other permissions
             console.print(f"[yellow]Warning:[/yellow] SSH key file '{resolved_path}' has insecure permissions ({oct(permissions)}). Recommended: 600 or 400.", style="yellow")
             # Allow execution but warn the user. Could raise PracticeToolError here for stricter check.
             # raise PracticeToolError(f"SSH key file '{resolved_path}' has insecure permissions ({oct(permissions)}). Use chmod 600.")
    except OSError as e:
        console.print(f"[yellow]Warning:[/yellow] Could not check permissions for SSH key file '{resolved_path}': {e}", style="yellow")

    return resolved_path


def run_ssh_command(ip_address: str, user: str, key_filename: Path, command: str, command_timeout: int = Config.SSH_COMMAND_TIMEOUT_SECONDS, verbose: bool = False, stdin_data: Optional[str] = None) -> Dict[str, Any]:
    """Connects via SSH, executes a command, returns results including potential errors."""
    if not ip_address:
        raise SSHCommandError("No IP address provided for SSH command.")

    key_path = _validate_ssh_key(key_filename) # Validate existence and permissions

    ssh_client = None
    # Initialize result with None for status, distinguish from actual -1 later if needed
    result = {'stdout': '', 'stderr': '', 'exit_status': None, 'error': None}

    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Less secure, consider known_hosts

        ssh_client.connect(
            hostname=ip_address,
            username=user,
            key_filename=str(key_path), # Paramiko needs string path
            timeout=Config.SSH_CONNECT_TIMEOUT_SECONDS,
            look_for_keys=False, # Only use specified key
            auth_timeout=Config.SSH_CONNECT_TIMEOUT_SECONDS
        )

        # *** MODIFIED exec_command call ***
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=command_timeout, get_pty=False)

        # *** ADDED: Write stdin_data if provided ***
        if stdin_data is not None:
            try:
                stdin.channel.sendall(stdin_data.encode('utf-8', errors='replace'))
                stdin.channel.shutdown_write() # Signal EOF after writing
            except Exception as stdin_err:
                 # Handle potential errors during stdin write
                 if not result.get('error'): # Avoid overwriting previous errors
                      result['error'] = f"Error writing to command stdin: {stdin_err}"
                 # We might still try to read output/status below

        # Read output (handle potential timeouts during read)
        channel = stdout.channel
        start_read = time.time()
        stdout_bytes = b""
        stderr_bytes = b""
        timed_out_in_loop = False

        while not channel.exit_status_ready():
             # Check for read timeout
             if time.time() - start_read > command_timeout + 5: # Add buffer for safety
                 result['error'] = f"Command execution timed out after {command_timeout}s (waiting for exit status)."
                 # Use a distinct marker for timeout within the loop vs. connection timeout
                 result['exit_status'] = -999 # Special code for command exec timeout
                 timed_out_in_loop = True
                 console.print(f"[yellow]:warning: {result['error']}[/]", style="yellow")
                 break # Exit the read loop

             # Read available data without blocking indefinitely
             if channel.recv_ready():
                 stdout_bytes += channel.recv(4096)
             if channel.recv_stderr_ready():
                 stderr_bytes += channel.recv_stderr(4096)

             # Avoid busy-waiting if no data and not exited
             if not channel.recv_ready() and not channel.recv_stderr_ready():
                 time.sleep(0.05)

        # --- FIX: Retrieve exit status more reliably after the loop ---
        # If the command finished (loop exited because exit_status_ready became true)
        # AND we didn't hit the explicit timeout within the loop:
        if not timed_out_in_loop:
            # Try to get the actual exit status
            try:
                result['exit_status'] = channel.recv_exit_status()
                # Read any remaining data that might have arrived after status was ready
                stdout_bytes += stdout.read()
                stderr_bytes += stderr.read()
            except Exception as e:
                 # Handle potential errors during final read/status retrieval
                 if not result['error']: # Avoid overwriting timeout error
                      result['error'] = f"Error retrieving final status/output: {e}"
                 result['exit_status'] = result.get('exit_status', -1) # Keep previous status or set -1

        # Decode output safely
        result['stdout'] = stdout_bytes.decode('utf-8', errors='replace').strip()
        result['stderr'] = stderr_bytes.decode('utf-8', errors='replace').strip()

        # If status is still None after attempts, set to -1 to indicate an issue
        if result['exit_status'] is None:
            result['exit_status'] = -1
            if not result['error']: # Add an error if none exists yet
                 result['error'] = "Failed to retrieve command exit status."


        return result

    # --- Exception Handling (mostly unchanged, but context added) ---
    except paramiko.AuthenticationException as e:
        err_msg = f"SSH Authentication failed for user '{user}' with key '{key_path}'. Verify key is in authorized_keys on VM and permissions are correct."
        result['error'] = err_msg
        result['exit_status'] = -1 # Indicate auth failure
        raise SSHCommandError(err_msg) from e
    except (paramiko.SSHException, socket.timeout, ConnectionRefusedError, OSError) as e:
        err_type = type(e).__name__
        if isinstance(e, socket.timeout):
             err_msg = f"SSH connection to {ip_address} timed out after {Config.SSH_CONNECT_TIMEOUT_SECONDS}s."
        elif isinstance(e, ConnectionRefusedError):
             err_msg = f"SSH connection refused by {ip_address} (is SSH server running on the VM?)."
        elif isinstance(e, OSError) and "No route to host" in str(e):
             err_msg = f"Network error connecting to {ip_address}: No route to host."
        else: # General SSHException or other OSError
             err_msg = f"SSH connection or protocol error to {ip_address} ({err_type}): {e}"
        result['error'] = err_msg
        result['exit_status'] = -1 # Indicate connection failure explicitly
        raise SSHCommandError(err_msg) from e
    except Exception as e:
        # Catchall for unexpected errors during SSH execution
        err_msg = f"An unexpected error occurred during SSH command ('{command}'): {e}"
        result['error'] = err_msg
        result['exit_status'] = result.get('exit_status', -1) # Keep status if set, else -1
        raise SSHCommandError(err_msg) from e
    finally:
        if ssh_client:
            ssh_client.close()


def wait_for_vm_ready(ip_address: str, user: str, key_filename: Path, timeout: int = Config.VM_READINESS_TIMEOUT_SECONDS, poll_interval: int = Config.VM_READINESS_POLL_INTERVAL_SECONDS):
    """Waits for the VM to become accessible via SSH using Rich Progress."""
    if not ip_address:
        raise NetworkError("Wait for Ready: No IP address provided.")

    key_path = _validate_ssh_key(key_filename) # Validate key path

    console.print(f"\n:hourglass_flowing_sand: Waiting up to {timeout} seconds for VM SSH readiness at [magenta]{ip_address}[/]...")
    start_time = time.time()
    last_error = "Timeout"

    with Progress(
        SpinnerColumn(spinner_name="earth"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("Elapsed: {task.elapsed:.0f}s"),
        transient=False, # Keep visible after completion
        console=console
    ) as progress:
        task = progress.add_task(f"Connecting to {ip_address}...", total=timeout)

        while not progress.finished:
            elapsed = time.time() - start_time
            progress.update(task, completed=min(elapsed, timeout))

            if elapsed >= timeout:
                 progress.update(task, description=f"Timeout waiting for {ip_address}", completed=timeout)
                 break # Exit loop, timeout error will be raised below

            ssh_client = None
            try:
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # Use a short connection timeout for the check itself
                connect_timeout = max(1, poll_interval - 1)
                ssh_client.connect(
                    hostname=ip_address,
                    username=user,
                    key_filename=str(key_path),
                    timeout=connect_timeout,
                    look_for_keys=False,
                    auth_timeout=connect_timeout
                )
                # If connect succeeds, SSH is ready
                progress.update(task, description=f"VM SSH Ready at {ip_address}!", completed=timeout)
                console.print(f"[green]:heavy_check_mark: VM SSH is ready at [bold magenta]{ip_address}[/]![/]")
                return True

            except paramiko.AuthenticationException as e:
                last_error = f"Authentication failed: {e}"
                progress.update(task, description=f"Auth failed for {user}@{ip_address}", completed=timeout)
                console.print(f"\n[yellow]:warning: VM SSH responded but authentication failed for user '{user}' with key '{key_path}'.[/]", style="yellow")
                console.print("[yellow]Check SSH key setup in the VM. Proceeding, but commands may fail.[/]", style="yellow")
                return True # Return True as SSH *server* is reachable, but warn user

            except (paramiko.SSHException, socket.timeout, ConnectionRefusedError, OSError) as e:
                # Common, expected errors during boot or network setup
                last_error = f"{type(e).__name__}"
                progress.update(task, description=f"Waiting for {ip_address} ({last_error})... Retrying")
                # Sleep is handled by the loop structure and timeout check below

            except Exception as e:
                # Unexpected error during the check
                last_error = f"Unexpected error: {e}"
                progress.update(task, description=f"Waiting for {ip_address}... (Unexpected Error)")
                console.print(f"\n[red]:x: Unexpected error while waiting for SSH: {e}[/]", style="red")
                console.print_exception(show_locals=False)
                # Continue waiting, but log the error

            finally:
                if ssh_client: ssh_client.close()
                # Controlled sleep before next attempt
                remaining_time = timeout - (time.time() - start_time)
                actual_sleep = min(poll_interval, max(0, remaining_time - 0.1)) # Ensure sleep is positive and respects remaining time
                if actual_sleep > 0:
                    time.sleep(actual_sleep)


    # Loop finished due to timeout
    raise NetworkError(f"VM did not become SSH-ready at {ip_address} within {timeout} seconds. Last status: {last_error}")

# --- Part 12: Challenge Loading & Validation Functions ---
def validate_challenge_structure(challenge_data: dict, filename: str = "challenge") -> List[str]:
    """Performs structural validation of loaded challenge data against expected schema."""
    errors = []
    # --- Top Level Keys ---
    required_keys = ['id', 'name', 'description', 'validation']
    allowed_keys = ['id', 'name', 'description', 'category', 'difficulty', 'score',
                    'concepts', 'setup', 'user_action_simulation', 'validation', 'hints', 'flag']
    for key in challenge_data:
        if key not in allowed_keys: errors.append(f"'{filename}': Unknown top-level key: '{key}'")
    for key in required_keys:
        if key not in challenge_data: errors.append(f"'{filename}': Missing required top-level key: '{key}'")

    # --- Basic Type Checks ---
    if 'id' in challenge_data and not isinstance(challenge_data['id'], str): errors.append(f"'{filename}': 'id' must be a string.")
    if 'name' in challenge_data and not isinstance(challenge_data['name'], str): errors.append(f"'{filename}': 'name' must be a string.")
    if 'description' in challenge_data and not isinstance(challenge_data['description'], str): errors.append(f"'{filename}': 'description' must be a string.")
    if 'category' in challenge_data and not isinstance(challenge_data['category'], str): errors.append(f"'{filename}': 'category' must be a string.")
    if 'difficulty' in challenge_data and not isinstance(challenge_data['difficulty'], str): errors.append(f"'{filename}': 'difficulty' must be a string.")
    if 'user_action_simulation' in challenge_data and not isinstance(challenge_data['user_action_simulation'], str): errors.append(f"'{filename}': 'user_action_simulation' must be a string.")
    if 'flag' in challenge_data and not isinstance(challenge_data['flag'], str): errors.append(f"'{filename}': 'flag' must be a string.")
    if 'concepts' in challenge_data and not isinstance(challenge_data['concepts'], list): errors.append(f"'{filename}': 'concepts' must be a list of strings.")
    elif 'concepts' in challenge_data:
        if not all(isinstance(c, str) for c in challenge_data['concepts']): errors.append(f"'{filename}': All items in 'concepts' must be strings.")

    # --- Score Validation ---
    if 'score' in challenge_data:
        try: int(challenge_data['score'])
        except (ValueError, TypeError): errors.append(f"'{filename}': 'score' ('{challenge_data['score']}') must be an integer.")

    # --- ID Format Validation ---
    challenge_id = challenge_data.get('id')
    if challenge_id and isinstance(challenge_id, str) and not re.match(r'^[a-zA-Z0-9._-]+$', challenge_id):
        errors.append(f"'{filename}': 'id' field '{challenge_id}' contains invalid characters. Use only letters, numbers, hyphens, underscores, periods.")

    # --- Validation Steps ---
    if 'validation' not in challenge_data: pass # Error already added
    elif not isinstance(challenge_data['validation'], list): errors.append(f"'{filename}': 'validation' field must be a list.")
    elif not challenge_data['validation']: errors.append(f"'{filename}': 'validation' list cannot be empty.")
    else:
        for i, step in enumerate(challenge_data['validation']):
            step_label = f"'{filename}' Validation step {i+1}"
            if not isinstance(step, dict): errors.append(f"{step_label}: Must be a dictionary.")
            elif 'type' not in step: errors.append(f"{step_label}: Missing 'type'.")
            else: # Type-specific checks
                step_type = step.get('type')
                if step_type == 'run_command':
                     if 'command' not in step: errors.append(f"{step_label}: Missing 'command'.")
                     if 'success_criteria' in step and not isinstance(step['success_criteria'], dict): errors.append(f"{step_label}: 'success_criteria' must be a dictionary.")
                elif step_type == 'check_service_status':
                     if 'service' not in step: errors.append(f"{step_label}: Missing 'service'.")
                     if 'expected_status' not in step: errors.append(f"{step_label}: Missing 'expected_status'.")
                     elif step['expected_status'] not in ["active", "inactive", "failed"]: errors.append(f"{step_label}: Invalid 'expected_status': {step['expected_status']}. Must be 'active', 'inactive', or 'failed'.")
                     if 'check_enabled' in step and not isinstance(step['check_enabled'], bool): errors.append(f"{step_label}: 'check_enabled' must be true or false.")
                elif step_type == 'check_port_listening':
                     if 'port' not in step: errors.append(f"{step_label}: Missing 'port'.")
                     try: int(step.get('port', 'x'))
                     except (ValueError, TypeError): errors.append(f"{step_label}: 'port' must be an integer.")
                     if 'protocol' in step and step['protocol'] not in ["tcp", "udp"]: errors.append(f"{step_label}: Invalid 'protocol': {step['protocol']}. Must be 'tcp' or 'udp'.")
                     if 'expected_state' not in step: errors.append(f"{step_label}: Missing 'expected_state'.")
                     elif not isinstance(step['expected_state'], bool): errors.append(f"{step_label}: 'expected_state' must be true or false.")
                elif step_type == 'check_file_exists':
                     if 'path' not in step: errors.append(f"{step_label}: Missing 'path'.")
                     if 'expected_state' not in step: errors.append(f"{step_label}: Missing 'expected_state'.")
                     elif not isinstance(step['expected_state'], bool): errors.append(f"{step_label}: 'expected_state' must be true or false.")
                     if 'file_type' in step and step['file_type'] not in ["any", "file", "directory"]: errors.append(f"{step_label}: Invalid 'file_type': {step['file_type']}. Must be 'any', 'file', or 'directory'.")
                     # Add optional checks for owner/group/permissions if implemented later
                elif step_type == 'check_file_contains':
                     if 'path' not in step: errors.append(f"{step_label}: Missing 'path'.")
                     if 'text' not in step and 'matches_regex' not in step: errors.append(f"{step_label}: Missing 'text' or 'matches_regex'.")
                     if 'text' in step and 'matches_regex' in step: errors.append(f"{step_label}: Cannot have both 'text' and 'matches_regex'.")
                     if 'expected_state' not in step: errors.append(f"{step_label}: Missing 'expected_state'.")
                     elif not isinstance(step['expected_state'], bool): errors.append(f"{step_label}: 'expected_state' must be true or false.")
                     if 'matches_regex' in step:
                         try: re.compile(step['matches_regex'])
                         except re.error as regex_err: errors.append(f"{step_label}: Invalid regex '{step['matches_regex']}': {regex_err}")
                else: errors.append(f"{step_label}: Unsupported validation type: '{step_type}'")

    # --- Setup Steps ---
    if 'setup' in challenge_data:
        if not isinstance(challenge_data['setup'], list): errors.append(f"'{filename}': 'setup' field must be a list if present.")
        else:
             for i, step in enumerate(challenge_data['setup']):
                 step_label = f"'{filename}' Setup step {i+1}"
                 if not isinstance(step, dict): errors.append(f"{step_label}: Must be a dictionary.")
                 elif 'type' not in step: errors.append(f"{step_label}: Missing 'type'.")
                 else: # Type-specific checks for setup
                     step_type = step.get('type')
                     if step_type == 'run_command':
                          if 'command' not in step: errors.append(f"{step_label}: Missing 'command'.")
                     # Add checks for 'copy_file', 'ensure_service_status' etc. if implemented
                     # elif step_type == 'copy_file': ...
                     else: errors.append(f"{step_label}: Unsupported setup type: '{step_type}'")

    # --- Hints ---
    if 'hints' in challenge_data:
         if not isinstance(challenge_data['hints'], list): errors.append(f"'{filename}': 'hints' field must be a list if present.")
         else:
             for i, hint in enumerate(challenge_data['hints']):
                 hint_label = f"'{filename}' Hint {i+1}"
                 if not isinstance(hint, dict): errors.append(f"{hint_label}: Must be a dictionary.")
                 elif 'text' not in hint: errors.append(f"{hint_label}: Missing 'text'.")
                 elif 'cost' in hint:
                     try: int(hint['cost'])
                     except (ValueError, TypeError): errors.append(f"{hint_label}: 'cost' ('{hint['cost']}') must be an integer.")

    return errors

def load_challenges_from_dir(challenges_dir: Path) -> Dict[str, Dict]:
    """Loads challenge definitions from YAML files in a directory, performing validation."""
    challenges: Dict[str, Dict] = {}
    if not challenges_dir.is_dir():
        raise ChallengeLoadError(f"Challenges directory not found: '{challenges_dir}'")

    console.print(f"\n:books: Loading challenges from: [blue underline]{challenges_dir.resolve()}[/]")
    yaml_files = sorted(list(challenges_dir.glob('*.yaml')) + list(challenges_dir.glob('*.yml')))

    if not yaml_files:
        console.print(f"  [yellow]:warning: No challenge YAML files (*.yaml, *.yml) found in '{challenges_dir}'.[/]", style="yellow")
        return challenges

    loaded_count = 0
    skipped_count = 0
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                challenge_data = yaml.safe_load(f)

            if not isinstance(challenge_data, dict):
                 console.print(f"  :warning: Skipping '[cyan]{yaml_file.name}[/cyan]': Content is not a valid YAML dictionary (root object).", style="yellow")
                 skipped_count += 1
                 continue

            # Validate structure before processing
            validation_errors = validate_challenge_structure(challenge_data, yaml_file.name)
            if validation_errors:
                # Use Panel for better formatting if Rich is available
                error_panel_content = "\n".join([f"- {e}" for e in validation_errors])
                if RICH_AVAILABLE:
                    console.print(Panel(error_panel_content, title=f"[bold red]Validation Errors in '{yaml_file.name}'[/]", border_style="red", expand=False))
                else:
                    console.print(f"--- Validation Errors in '{yaml_file.name}' ---")
                    console.print(error_panel_content)
                    console.print(f"--- End Errors ---")
                skipped_count += 1
                continue # Skip loading invalid challenges

            challenge_id = challenge_data['id'] # Already validated existence and type

            # Apply defaults and type conversions *after* validation
            challenge_data['score'] = int(challenge_data.get('score', Config.DEFAULT_CHALLENGE_SCORE))
            # Ensure 'hints' exists and cost is int
            processed_hints = []
            for hint in challenge_data.get('hints', []):
                if isinstance(hint, dict) and 'text' in hint:
                    hint['cost'] = int(hint.get('cost', 0))
                    processed_hints.append(hint)
            challenge_data['hints'] = processed_hints
            # Ensure 'setup' is a list
            challenge_data['setup'] = challenge_data.get('setup', [])
            # Ensure 'concepts' is a list
            challenge_data['concepts'] = challenge_data.get('concepts', [])

            if challenge_id in challenges:
                 console.print(f"  :warning: Duplicate challenge ID '[bold yellow]{challenge_id}[/]' found in '[cyan]{yaml_file.name}[/cyan]'. Overwriting previous definition.", style="yellow")

            challenges[challenge_id] = challenge_data
            loaded_count += 1

        except yaml.YAMLError as e:
            console.print(f"  [red]:x: Error parsing YAML file '[cyan]{yaml_file.name}[/cyan]': {e}[/]", style="red")
            skipped_count += 1
        except FileNotFoundError:
             console.print(f"  [red]:x: File '{yaml_file.name}' suddenly not found during loading.[/]", style="red")
             skipped_count += 1
        except Exception as e:
            console.print(f"  [red]:x: An unexpected error occurred loading '{yaml_file.name}': {e}[/]", style="red")
            if RICH_AVAILABLE: console.print_exception(show_locals=False)
            else: traceback.print_exc()
            skipped_count += 1

    # --- Summary ---
    summary = f"Load complete: [green]{loaded_count} challenges loaded[/]"
    if skipped_count > 0:
         summary += f", [yellow]{skipped_count} skipped due to errors[/]."
    else:
         summary += "."
    console.print(summary)
    if skipped_count > 0:
         console.print("[yellow]Please review the errors in the skipped challenge files.[/]", style="yellow")

    return challenges

# --- Part 13: Challenge Validation Step Execution Logic ---
def format_ssh_output(result_dict: Dict[str, Any], command_str: str) -> Any:
    """Formats SSH command results using Rich Panel."""
    max_cmd_len = 60
    display_cmd = command_str if len(command_str) <= max_cmd_len else command_str[:max_cmd_len-3] + "..."
    title = f"[bold]SSH Result[/] [dim]({display_cmd})[/]"

    content = ""
    exit_status = result_dict.get('exit_status', -1)
    exec_error = result_dict.get('error') # Specific execution error (timeout, auth fail, etc.)

    # Determine style based on exit status AND execution error
    if exec_error:
        status_text = f"[red]Execution Error[/]"
        border_style = "red"
    elif exit_status == 0:
        status_text = f"[green]{exit_status}[/]"
        border_style = "green"
    else:
        status_text = f"[red]{exit_status}[/]"
        border_style = "red"

    content += f"[b]Exit Status:[/b] {status_text}\n"
    if exec_error:
         content += f"[b]Error:[/b] [red]{exec_error}[/]\n"


    stdout = result_dict.get('stdout', '')
    stderr = result_dict.get('stderr', '')

    # Truncate long output for display
    max_lines = 10
    max_line_len = 100 # Prevent super long lines messing up panel width
    def truncate_output(output: str) -> str:
        lines = output.splitlines()
        truncated_lines = []
        for line in lines[:max_lines]:
             truncated_lines.append(line[:max_line_len] + ('[dim]...[/]' if len(line) > max_line_len else ''))
        display = "\n".join(truncated_lines)
        if len(lines) > max_lines:
            display += f"\n[dim]... ({len(lines) - max_lines} more lines)[/]"
        return display

    if stdout:
        content += f"\n[b]STDOUT:[/]\n---\n{truncate_output(stdout)}\n---"
    else:
        content += "\n[b]STDOUT:[/b] [i dim](empty)[/]"

    if stderr:
        content += f"\n\n[b]STDERR:[/]\n---\n{truncate_output(stderr)}\n---"
    else:
         content += "\n\n[b]STDERR:[/b] [i dim](empty)[/]"

    # Use Panel if Rich available, otherwise basic string format
    if RICH_AVAILABLE:
        return Panel(Text(content, no_wrap=False), title=title, border_style=border_style, expand=False)
    else:
        return f"--- {title} ---\n{content}\n--- End {title} ---"


def _validate_run_command(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'run_command' step. Returns True on success, raises ChallengeValidationError on failure."""
    command = step_data.get("command")
    if not command: raise ChallengeValidationError(["Missing 'command' in run_command step."])

    criteria = step_data.get("success_criteria", {"exit_status": Config.EXIT_CODE_ACTIVE}) # Default criteria = exit 0

    # Run the command via SSH
    try:
        val_result = run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=False)
    except SSHCommandError as e:
        # If SSH itself fails (connection, auth), validation fails
        raise ChallengeValidationError([f"SSH execution failed: {e}"]) from e

    if verbose: console.print(format_ssh_output(val_result, command))

    # Check for SSH command execution errors (e.g., timeout *during* command run)
    if val_result.get('error'):
         raise ChallengeValidationError([f"Command execution error: {val_result['error']}"])

    # Validate based on success_criteria
    step_reasons = []
    actual_status = val_result.get('exit_status', -1)
    actual_stdout = val_result.get('stdout', '')
    actual_stderr = val_result.get('stderr', '')

    # 1. Exit Status Check
    expected_status = criteria.get("exit_status")
    if expected_status is not None and actual_status != expected_status:
        step_reasons.append(f"Expected exit status {expected_status}, but got {actual_status}.")

    # 2. STDOUT Checks
    stdout_equals = criteria.get("stdout_equals")
    if stdout_equals is not None and actual_stdout != stdout_equals:
        step_reasons.append(f"stdout did not exactly match expected value.") # Avoid printing potentially large value

    stdout_contains = criteria.get("stdout_contains")
    if stdout_contains is not None and stdout_contains not in actual_stdout:
         step_reasons.append(f"stdout did not contain expected text.") # Avoid printing

    stdout_regex = criteria.get("stdout_matches_regex")
    if stdout_regex is not None:
        try:
            if not re.search(stdout_regex, actual_stdout, re.MULTILINE):
                step_reasons.append(f"stdout did not match regex '{stdout_regex}'.")
        except re.error as regex_err:
            # This should be caught by challenge validation, but handle defensively
            raise ChallengeValidationError([f"Invalid regex in challenge definition '{stdout_regex}': {regex_err}"])

    # 3. STDERR Checks
    stderr_empty = criteria.get("stderr_empty", False)
    if stderr_empty and actual_stderr:
        step_reasons.append(f"Expected stderr to be empty, but it was not.")

    stderr_contains = criteria.get("stderr_contains")
    if stderr_contains is not None and stderr_contains not in actual_stderr:
        step_reasons.append(f"stderr did not contain expected text.") # Avoid printing

    if step_reasons: raise ChallengeValidationError(step_reasons)
    return True # All criteria met


def _validate_check_service_status(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'check_service_status' step."""
    service_name = step_data.get("service")
    expected_status = step_data.get("expected_status") # required, validated in schema
    check_enabled = step_data.get("check_enabled", False) # Optional bool

    if not service_name or not expected_status: # Should be caught by schema validation
        raise ChallengeValidationError(["Invalid check_service_status step: Missing 'service' or 'expected_status'."])

    step_reasons = []

    # Check Active State using systemctl is-active
    cmd_active = f"systemctl is-active --quiet {shlex.quote(service_name)}"
    try:
        result_active = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_active, verbose=False)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for active check: {e}"])

    if verbose: console.print(format_ssh_output(result_active, f"systemctl is-active {service_name}"))
    if result_active.get('error'): raise ChallengeValidationError([f"Active check command error: {result_active['error']}"])

    actual_status_code = result_active.get('exit_status', -1)
    actual_status_str = "unknown"
    if actual_status_code == Config.EXIT_CODE_ACTIVE: actual_status_str = "active"
    elif actual_status_code == Config.EXIT_CODE_INACTIVE: actual_status_str = "inactive"
    elif actual_status_code >= Config.EXIT_CODE_FAILED_BASE: actual_status_str = "failed" # Treat other non-zero as failed/not-found

    if actual_status_str != expected_status:
        step_reasons.append(f"Expected service status '{expected_status}', but was '{actual_status_str}'.")

    # Check Enabled State (only if active check passed OR if active check failed but we still need to check enabled)
    if check_enabled:
        cmd_enabled = f"systemctl is-enabled --quiet {shlex.quote(service_name)}"
        try:
            result_enabled = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_enabled, verbose=False)
        except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for enabled check: {e}"])

        if verbose: console.print(format_ssh_output(result_enabled, f"systemctl is-enabled {service_name}"))
        if result_enabled.get('error'): raise ChallengeValidationError([f"Enabled check command error: {result_enabled['error']}"])

        is_enabled_code = result_enabled.get('exit_status', -1)
        is_enabled = (is_enabled_code == Config.EXIT_CODE_ENABLED)

        if not is_enabled:
            step_reasons.append(f"Expected service to be enabled, but 'systemctl is-enabled' reported it is not (exit code {is_enabled_code}).")

    if step_reasons: raise ChallengeValidationError(step_reasons)
    return True


def _validate_check_port_listening(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'check_port_listening' step."""
    port = step_data.get("port") # required, validated int in schema
    protocol = step_data.get("protocol", "tcp").lower() # default tcp
    expected_state = step_data.get("expected_state") # required bool

    if port is None or expected_state is None: # Should be caught by schema
        raise ChallengeValidationError(["Invalid check_port_listening step: Missing 'port' or 'expected_state'."])

    # Use ss command: -n (numeric), -l (listening), -p (processes), -t (tcp) / -u (udp)
    proto_flag = "t" if protocol == "tcp" else "u"
    # Robust check using awk: checks LISTEN state AND correct port in local address field (handles IPv4/IPv6)
    awk_filter = f'$1 == "LISTEN" && ($4 ~ /[:.][*]?{port}$/ || $4 ~ /\\[[:*]\\]:{port}$/) {{ found=1; exit }} END {{ exit !found }}'
    # Need to escape awk script for shell inside SSH command
    cmd = f"ss -nl{proto_flag}p | awk '{awk_filter}'"

    try:
        result = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd, verbose=False)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for port check: {e}"])

    if verbose: console.print(format_ssh_output(result, f"ss -nl{proto_flag}p | awk '...'"))
    if result.get('error'): raise ChallengeValidationError([f"Port check command error: {result['error']}"])

    # awk exits 0 if found (found=1 -> exit 0), 1 if not found (exit !found -> exit 1)
    is_listening = (result.get('exit_status') == 0)

    if is_listening != expected_state:
        state_str = "listening" if is_listening else "not listening"
        expected_str = "be listening" if expected_state else "not be listening"
        raise ChallengeValidationError([f"Expected port {protocol}/{port} to {expected_str}, but it was {state_str}."])
    return True


def _validate_check_file_exists(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'check_file_exists' step."""
    file_path = step_data.get("path") # required string
    expected_state = step_data.get("expected_state") # required bool
    file_type = step_data.get("file_type", "any").lower() # default any

    if not file_path or expected_state is None: # Should be caught by schema
        raise ChallengeValidationError(["Invalid check_file_exists step: Missing 'path' or 'expected_state'."])

    test_flag_map = {"any": "-e", "file": "-f", "directory": "-d"}
    test_flag = test_flag_map[file_type]
    quoted_path = shlex.quote(file_path)
    cmd = f"test {test_flag} {quoted_path}"

    try:
        result = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd, verbose=False)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for file check: {e}"])

    if verbose: console.print(format_ssh_output(result, f"test {test_flag} ..."))
    if result.get('error'): raise ChallengeValidationError([f"File check command error: {result['error']}"])

    # test command exits 0 if condition is true, 1 otherwise
    exists_and_matches_type = (result.get('exit_status') == 0)

    if exists_and_matches_type != expected_state:
        type_desc = f"a {file_type}" if file_type != "any" else "present"
        state_str = f"exists and is {type_desc}" if exists_and_matches_type else f"does not exist or is not {type_desc}"
        expected_str = f"exist and be {type_desc}" if expected_state else f"not exist or not be {type_desc}"
        raise ChallengeValidationError([f"Path '{file_path}' {state_str}, but expected to {expected_str}."])

    # Optional: Add checks for owner/group/permissions here if specified in step_data
    # Need to use 'stat' command and parse output. E.g.:
    # owner = step_data.get("owner")
    # if owner and exists_and_matches_type: ... run stat command ... check owner ... add reason if mismatch

    return True

def _validate_check_file_contains(step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool) -> bool:
    """Validates a 'check_file_contains' step."""
    file_path = step_data.get("path") # required string
    expected_text = step_data.get("text")
    expected_regex = step_data.get("matches_regex")
    expected_state = step_data.get("expected_state") # required bool

    if not file_path or expected_state is None or (expected_text is None and expected_regex is None):
        raise ChallengeValidationError(["Invalid check_file_contains step: Missing 'path', 'expected_state', or ('text'/'matches_regex')."])

    quoted_path = shlex.quote(file_path)

    # First, check if file exists and is readable (important for expected_state=False)
    cmd_check = f"test -r {quoted_path}"
    try:
        result_check = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_check, verbose=False)
        if result_check.get('error'): raise ChallengeValidationError([f"Readability check command error: {result_check['error']}"])
        file_is_readable = (result_check.get('exit_status') == 0)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for readability check: {e}"])

    if not file_is_readable:
        if expected_state is True: # Expected content, but file not readable/found
            raise ChallengeValidationError([f"File '{file_path}' not found or is not readable."])
        else: # Expected NO content, and file not readable/found = Success
            return True # Correctly does not contain the text

    # File exists and is readable, now check content using grep
    grep_opts = "-q" # Quiet mode (exit status only)
    pattern = ""
    search_desc = ""
    if expected_text is not None:
        grep_opts += "F" # Fixed string
        pattern = expected_text
        search_desc = f"text '{expected_text[:30]}{'...' if len(expected_text)>30 else ''}'"
    elif expected_regex is not None:
        grep_opts += "E" # Extended regex
        pattern = expected_regex
        search_desc = f"regex '{expected_regex[:30]}{'...' if len(expected_regex)>30 else ''}'"

    # Use -- to handle patterns starting with '-'
    cmd_grep = f"grep {grep_opts} -- {shlex.quote(pattern)} {quoted_path}"

    try:
        result_grep = run_ssh_command(vm_ip, ssh_user, ssh_key, cmd_grep, verbose=False)
    except SSHCommandError as e: raise ChallengeValidationError([f"SSH execution failed for grep check: {e}"])

    if verbose: console.print(format_ssh_output(result_grep, f"grep {grep_opts} ..."))
    if result_grep.get('error'): raise ChallengeValidationError([f"Grep command execution error: {result_grep['error']}"])

    # grep exit status: 0=found, 1=not found, >1=error
    grep_exit_status = result_grep.get('exit_status', -1)
    found = (grep_exit_status == 0)
    grep_error = (grep_exit_status > 1)

    if grep_error:
        # This indicates an issue like file disappearing or permissions problem during grep
        raise ChallengeValidationError([f"Error running grep on '{file_path}' (exit status {grep_exit_status}). File might have changed, or permissions issue."])

    if found != expected_state:
        state_str = "found" if found else "not found"
        expected_str = "be found" if expected_state else "not be found"
        raise ChallengeValidationError([f"Expected {search_desc} to {expected_str} in '{file_path}', but it was {state_str}."])
    return True


def execute_validation_step(step_num: int, step_data: dict, vm_ip: str, ssh_user: str, ssh_key: Path, verbose: bool):
    """Executes a single validation step, raising ChallengeValidationError on failure."""
    step_type = step_data.get("type")
    step_title = f"Step {step_num}: [bold cyan]{step_type}[/]"

    validation_functions = {
        "run_command": _validate_run_command,
        "check_service_status": _validate_check_service_status,
        "check_port_listening": _validate_check_port_listening,
        "check_file_exists": _validate_check_file_exists,
        "check_file_contains": _validate_check_file_contains,
    }

    validator_func = validation_functions.get(step_type)
    if not validator_func:
        raise ChallengeValidationError([f"Unsupported validation step type: '{step_type}'"])

    try:
        # Call the appropriate validation function
        # It returns True on success or raises ChallengeValidationError on failure
        validator_func(step_data, vm_ip, ssh_user, ssh_key, verbose)

        # If no exception was raised, the step passed
        success_panel_content = "[green]:heavy_check_mark: Passed[/]"
        if RICH_AVAILABLE:
            console.print(Panel(success_panel_content, title=step_title, border_style="green", expand=False))
        else:
            console.print(f"--- {step_title}: Passed ---")

    except ChallengeValidationError as e:
        # Format and print the failure reason panel
        reason_text = "\n".join([f"- {r}" for r in e.reasons])
        failure_panel_content = f"[bold red]:x: Failed[/]\n{reason_text}"
        if RICH_AVAILABLE:
            console.print(Panel(failure_panel_content, title=step_title, border_style="red", expand=False))
        else:
            console.print(f"--- {step_title}: FAILED ---")
            console.print(reason_text)
            console.print(f"--- End Failure ---")
        raise e # Re-raise to signal failure to the main workflow
    except Exception as ex: # Catch unexpected errors during validation logic itself
         reason = f"Unexpected Error during validation logic: {ex}"
         failure_panel_content = f"[bold red]:x: Failed[/]\n{reason}"
         if RICH_AVAILABLE:
            console.print(Panel(failure_panel_content, title=step_title, border_style="red", expand=False))
            console.print_exception(show_locals=False)
         else:
             console.print(f"--- {step_title}: FAILED ---")
             console.print(reason)
             traceback.print_exc()
             console.print(f"--- End Failure ---")
         # Wrap unexpected error in ChallengeValidationError for consistent handling
         raise ChallengeValidationError([reason]) from ex


# --- Part 14: Typer CLI Application Setup ---
app = typer.Typer(
    help=Panel(
        "[bold cyan]Linux+ Practice Environment Manager (LPEM)[/]\n\n"
        "Manages libvirt VMs and runs practice challenges for the CompTIA Linux+ exam (XK0-005).\n"
        "Uses external snapshots for safe, revertible practice environments.",
        title="LPEM CLI", border_style="blue") if RICH_AVAILABLE else "Linux+ Practice Environment Manager (LPEM)",
    rich_markup_mode="rich" if RICH_AVAILABLE else "markdown"
)
challenge_app = typer.Typer(name="challenge", help="Manage challenge definitions (create templates, validate).", rich_markup_mode="rich" if RICH_AVAILABLE else "markdown")
app.add_typer(challenge_app)

# --- Part 15: Typer Commands (Main Application Logic) ---
@app.command()
def list_available_vms(
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = Config.LIBVIRT_URI
):
    """Lists virtual machines known to libvirt."""
    conn = None
    try:
        # Override default URI if provided
        Config.LIBVIRT_URI = libvirt_uri
        conn = connect_libvirt()
        list_vms(conn)
    except PracticeToolError as e:
        console.print(f"[bold red]:x: Error:[/bold red] {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        close_libvirt(conn)


@app.command(name="list-challenges")
def list_available_challenges(
    challenges_dir: Annotated[Path, typer.Option("--dir", "-d",
        help="Directory containing challenge YAML files.",
        exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True
    )] = Config.DEFAULT_CHALLENGES_DIR
):
    """Lists valid practice challenges found in the specified directory."""
    try:
        challenges = load_challenges_from_dir(challenges_dir) # Validation happens inside
    except ChallengeLoadError as e:
         console.print(f"[bold red]:x: Error loading challenges:[/bold red] {e}", style="red")
         raise typer.Exit(code=1)

    if not challenges:
        no_challenges_msg = "[i]No valid challenges loaded.[/]"
        if RICH_AVAILABLE: console.print(Panel(no_challenges_msg, title="Available Challenges", border_style="dim"))
        else: console.print(no_challenges_msg)
        return

    # FIX: Removed 'console=console' from Table constructor
    table = Table(title=f"[bold blue]Available Challenges[/] ([dim]from {challenges_dir}[/])", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Category", style="yellow")
    table.add_column("Difficulty", style="green")
    table.add_column("Score", justify="right", style="blue")

    # Sort by category, then name for consistent listing
    sorted_challenges = sorted(challenges.values(), key=lambda c: (c.get('category', 'zzz').lower(), c.get('name', 'zzz').lower()))

    for chal in sorted_challenges:
        table.add_row(
            chal['id'], # Required field
            chal.get('name', '[dim]N/A[/]'),
            chal.get('category', '[dim]N/A[/]'),
            chal.get('difficulty', '[dim]N/A[/]'),
            str(chal['score']), # Required, defaults to 100
        )

    console.print(table) # Table is printed using the console here
    console.print("\nRun '[bold]lpem run-challenge <ID>[/]' to start a challenge.")
    console.print("Use '[bold]lpem challenge --help[/]' for creation/validation commands.")


@app.command(name="setup-user")
def setup_vm_user(
    vm_name: Annotated[str, typer.Option("--vm", help="Name of the libvirt VM to use.")] = Config.DEFAULT_VM_NAME,
    new_user: Annotated[str, typer.Option("--new-user", help="Username to set up on the VM.")] = Config.DEFAULT_SSH_USER, # Use the default user 'roo'
    admin_user: Annotated[str, typer.Option("--admin-user", help="An existing sudoer user on the VM to run setup commands.")] = "ubuntu", # Assuming 'ubuntu' is the default sudo user
    admin_key: Annotated[Path, typer.Option("--admin-key", help="Path to the SSH private key for the admin user.")] = Config.DEFAULT_SSH_KEY_PATH, # Assuming admin uses the same key for now
    public_key_path: Annotated[Path, typer.Option("--pub-key", help="Path to the PUBLIC SSH key to install for the new user.", exists=True, file_okay=True, readable=True)] = Path("~/.ssh/id_ed25519.pub").expanduser(), # Default public key path
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = Config.LIBVIRT_URI,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Print detailed command output.")] = False,
):
    """Sets up a user on the VM with SSH key authentication."""
    console.rule(f"[bold blue]Setting up User: [cyan]{new_user}[/cyan] on VM: [cyan]{vm_name}[/cyan][/]", style="blue")
    conn: Optional[libvirt.virConnect] = None
    domain: Optional[libvirt.virDomain] = None
    vm_ip: Optional[str] = None

    # Validate the admin key path
    try:
        admin_key_path = _validate_ssh_key(admin_key)
    except PracticeToolError as key_err:
        console.print(f"[bold red]:x: Admin SSH Key Error:[/bold red] {key_err}", style="red")
        raise typer.Exit(code=1)

    # Read the public key content
    try:
        public_key_content = public_key_path.read_text(encoding='utf-8').strip()
        if not public_key_content.startswith(("ssh-", "ecdsa-")):
             raise ValueError("Content does not look like a valid public SSH key.")
    except (IOError, ValueError) as pub_key_err:
        console.print(f"[bold red]:x: Public Key Error:[/bold red] Failed to read or validate public key '{public_key_path}': {pub_key_err}", style="red")
        raise typer.Exit(code=1)

    try:
        # --- Connect, Find VM, Start, Get IP, Wait ---
        Config.LIBVIRT_URI = libvirt_uri
        conn = connect_libvirt()
        domain = find_vm(conn, vm_name)
        start_vm(domain) # Ensure VM is running
        vm_ip = get_vm_ip(conn, domain)
        # Wait using the ADMIN user credentials first
        console.print(f"[dim]Waiting for VM readiness using admin user '{admin_user}'...[/]")
        wait_for_vm_ready(vm_ip, admin_user, admin_key_path, timeout=Config.VM_READINESS_TIMEOUT_SECONDS)

        console.print(f"\n:gear: Starting user setup for '{new_user}' using admin '{admin_user}'...")

        # --- Define Setup Commands ---
        home_dir = f"/home/{new_user}"
        ssh_dir = f"{home_dir}/.ssh"
        auth_keys_file = f"{ssh_dir}/authorized_keys"
        # No need for quoted_key_content here as we pass via stdin

        # --- Execute Setup Commands (Revised Key Writing Logic) ---
        all_succeeded = True
        check_home_cmd = f"sudo ls -ld {shlex.quote(home_dir)}"
        console.print(f"\nExecuting: [dim]`{check_home_cmd}`[/]")
        try:
            result_check_home = run_ssh_command(vm_ip, admin_user, admin_key_path, check_home_cmd, verbose=False)
            if verbose or result_check_home.get('exit_status', -1) != 0: # Show output if verbose or if it failed
                 console.print(format_ssh_output(result_check_home, check_home_cmd))
            if result_check_home.get('exit_status', -1) != 0:
                 console.print(f"[yellow]Warning:[/yellow] Could not verify status of home directory '{home_dir}'. Proceeding with caution.", style="yellow")
        except SSHCommandError as e:
             console.print(f"[yellow]Warning:[/yellow] SSH error checking home directory: {e}. Proceeding with caution.", style="yellow")


        # Define setup commands *WITHOUT* the key writing step initially
        setup_commands_part1 = [
            f"sudo useradd -m -s /bin/bash -G sudo {shlex.quote(new_user)} || echo 'User potentially already exists'",
            f"sudo mkdir -p {shlex.quote(ssh_dir)}",
            f"sudo chmod 700 {shlex.quote(ssh_dir)}",
        ]
        setup_commands_part2 = [
            f"sudo chmod 600 {shlex.quote(auth_keys_file)}",
            f"sudo chown -R {shlex.quote(new_user)}:{shlex.quote(new_user)} {shlex.quote(home_dir)}"
        ]

        # --- Execute Part 1 ---
        current_step_index = 0
        for i, command in enumerate(setup_commands_part1):
             current_step_index = i + 1
             step_title = f"Setup Step {current_step_index}"
             console.print(f"\nExecuting: [dim]`{command}`[/]")
             try:
                 result = run_ssh_command(vm_ip, admin_user, admin_key_path, command, verbose=False)

                 exec_error = result.get('error')
                 exit_status = result.get('exit_status', -1)
                 stderr_output = result.get('stderr', '').strip()
                 stdout_output = result.get('stdout', '').strip()

                 # Show detailed output if verbose OR if there was an error/non-zero exit
                 show_details = verbose or exec_error or exit_status != 0
                 if show_details:
                     console.print(format_ssh_output(result, command))

                 if exec_error or exit_status != 0:
                     details = exec_error or f"Exited with status {exit_status}"
                     error_details = f"{details}"
                     if stderr_output: error_details += f"\nSTDERR: {stderr_output}"
                     if stdout_output: error_details += f"\nSTDOUT: {stdout_output}"
                     console.print(Panel(f"[bold red]:x: Failed:[/bold red]\n{error_details}", title=step_title, border_style="red"))
                     all_succeeded = False
                     break # Stop on first error
                 else:
                     # Show success panel *unless* we already showed details above
                     if not show_details:
                        success_content = "[green]:heavy_check_mark: Succeeded[/]"
                        if stdout_output: # Show stdout even on success if it exists
                            success_content += f"\nSTDOUT: {stdout_output}"
                        console.print(Panel(success_content, title=step_title, border_style="green"))

             except SSHCommandError as e:
                 console.print(Panel(f"[bold red]:x: Failed:[/bold red] SSH execution error: {e}", title=step_title, border_style="red"))
                 all_succeeded = False
                 break # Stop on SSH failure

        # --- Step 4: Write Key via Stdin (if Part 1 succeeded) ---
        if all_succeeded:
             current_step_index += 1
             step_title = f"Setup Step {current_step_index}: Write authorized_keys"
             console.print(f"\nExecuting: [dim]`sudo tee {auth_keys_file}` (with key piped via stdin)")
             try:
                # The command to run remotely
                write_cmd = f"sudo tee {shlex.quote(auth_keys_file)}"
                # Data to pipe into the command's stdin (ensure it's just the key)
                # Using public_key_content directly which should be the single line key
                key_data_to_pipe = public_key_content + "\n" # Add newline just in case tee expects it

                # Use the modified run_ssh_command with stdin_data
                result = run_ssh_command(
                    vm_ip,
                    admin_user,
                    admin_key_path,
                    write_cmd,
                    verbose=False,
                    stdin_data=key_data_to_pipe
                )

                # Check result similar to other steps
                exec_error = result.get('error')
                exit_status = result.get('exit_status', -1)
                stderr_output = result.get('stderr', '').strip()
                stdout_output = result.get('stdout', '').strip() # tee mirrors stdin to stdout

                show_details = verbose or exec_error or exit_status != 0
                if show_details:
                    # Indicate stdin usage in the command display for clarity
                    console.print(format_ssh_output(result, write_cmd + " <<< KEY_DATA"))

                if exec_error or exit_status != 0:
                    details = exec_error or f"Exited with status {exit_status}"
                    error_details = f"{details}"
                    if stderr_output: error_details += f"\nSTDERR: {stderr_output}"
                    # Check if stdout (mirrored key) is what we sent, might help debug tee issues
                    if stdout_output != key_data_to_pipe.strip():
                        error_details += f"\nSTDOUT_MISMATCH: Tee output did not match expected key."
                    elif stdout_output: # Only show stdout if it wasn't a mismatch and exists
                        error_details += f"\nSTDOUT: {stdout_output}"

                    console.print(Panel(f"[bold red]:x: Failed:[/bold red]\n{error_details}", title=step_title, border_style="red"))
                    all_succeeded = False
                else:
                    if not show_details: # Only print success panel if details weren't shown
                        success_content = "[green]:heavy_check_mark: Succeeded[/]"
                        console.print(Panel(success_content, title=step_title, border_style="green"))

             except SSHCommandError as e:
                 console.print(Panel(f"[bold red]:x: Failed:[/bold red] SSH execution error: {e}", title=step_title, border_style="red"))
                 all_succeeded = False


        # --- Execute Part 2 (if previous steps succeeded) ---
        if all_succeeded:
             for i, command in enumerate(setup_commands_part2):
                  current_step_index += 1
                  step_title = f"Setup Step {current_step_index}"
                  console.print(f"\nExecuting: [dim]`{command}`[/]")
                  try:
                      result = run_ssh_command(vm_ip, admin_user, admin_key_path, command, verbose=False)

                      exec_error = result.get('error')
                      exit_status = result.get('exit_status', -1)
                      stderr_output = result.get('stderr', '').strip()
                      stdout_output = result.get('stdout', '').strip()

                      show_details = verbose or exec_error or exit_status != 0
                      if show_details:
                          console.print(format_ssh_output(result, command))

                      if exec_error or exit_status != 0:
                          details = exec_error or f"Exited with status {exit_status}"
                          error_details = f"{details}"
                          if stderr_output: error_details += f"\nSTDERR: {stderr_output}"
                          if stdout_output: error_details += f"\nSTDOUT: {stdout_output}"
                          console.print(Panel(f"[bold red]:x: Failed:[/bold red]\n{error_details}", title=step_title, border_style="red"))
                          all_succeeded = False
                          break # Stop on first error
                      else:
                          if not show_details:
                             success_content = "[green]:heavy_check_mark: Succeeded[/]"
                             if stdout_output:
                                 success_content += f"\nSTDOUT: {stdout_output}"
                             console.print(Panel(success_content, title=step_title, border_style="green"))

                  except SSHCommandError as e:
                      console.print(Panel(f"[bold red]:x: Failed:[/bold red] SSH execution error: {e}", title=step_title, border_style="red"))
                      all_succeeded = False
                      break # Stop on SSH failure

        # --- Post-Setup File Checks (if setup seemed to succeed so far) ---
        if all_succeeded:
             console.print("\n:mag: Checking file permissions and ownership post-setup...")
             post_check_commands = [
                 f"sudo ls -ld {shlex.quote(ssh_dir)}",
                 f"sudo ls -l {shlex.quote(auth_keys_file)}",
                 # Add command to check file content
                 f"sudo cat {shlex.quote(auth_keys_file)}"
             ]
             for check_cmd in post_check_commands:
                 console.print(f"\nExecuting: [dim]`{check_cmd}`[/]")
                 try:
                    result_check = run_ssh_command(vm_ip, admin_user, admin_key_path, check_cmd, verbose=False)
                    # Always show the output of these checks for debugging
                    console.print(format_ssh_output(result_check, check_cmd))
                    if result_check.get('error') or result_check.get('exit_status', -1) != 0:
                         console.print(f"[yellow]Warning:[/yellow] Post-setup check command failed.", style="yellow")
                         # Optional: Could set all_succeeded = False here if checks are critical
                 except SSHCommandError as e:
                      console.print(f"[yellow]Warning:[/yellow] SSH error during post-setup check: {e}", style="yellow")


        # --- Final Verification (Try connecting as the new user) ---
        if all_succeeded:
            console.print("\n:lock_with_ink_pen: Verifying SSH access for new user...")
            try:
                verify_cmd = "echo 'SSH connection successful!'"
                # IMPORTANT: Use the correct key for the new user 'roo'
                # Assuming the key corresponding to public_key_path is Config.DEFAULT_SSH_KEY_PATH
                # This assumption might need refinement if users can specify different keys easily
                new_user_private_key_path = Config.DEFAULT_SSH_KEY_PATH # Or derive from public_key_path if possible/needed
                if not new_user_private_key_path.is_file(): # Check if it's a file
                     raise PracticeToolError(f"Cannot verify '{new_user}' login: Private key '{new_user_private_key_path}' not found or is not a file.")

                result = run_ssh_command(vm_ip, new_user, new_user_private_key_path, verify_cmd, verbose=False)

                if verbose or result.get('error') or result.get('exit_status', -1) != 0:
                     console.print(format_ssh_output(result, verify_cmd))

                if result.get('error') or result.get('exit_status', -1) != 0:
                     err = result.get('error') or f"Exit status {result.get('exit_status', -1)}"
                     console.print(f"[bold red]:x: Verification Failed:[/bold red] Could not SSH as '{new_user}'. Error: {err}", style="red")
                     all_succeeded = False
                else:
                     console.print("[green]:heavy_check_mark: Verification Successful:[/green] Able to SSH as the new user.")
            except SSHCommandError as e:
                 console.print(f"[bold red]:x: Verification Failed:[/bold red] SSH error trying to connect as '{new_user}': {e}", style="red")
                 all_succeeded = False
            except PracticeToolError as key_err: # Catch missing private key error
                 console.print(f"[bold red]:x: Verification Failed:[/bold red] {key_err}", style="red")
                 all_succeeded = False

        # --- Results ---
        console.rule("[bold]User Setup Results[/]", style="blue")
        if all_succeeded:
            console.print(f"[bold green]:heavy_check_mark: User '{new_user}' setup completed successfully on VM '{vm_name}'.[/]")
        else:
            console.print(f"[bold red]:x: User '{new_user}' setup failed. Please review the errors above.[/]", style="red")
            raise typer.Exit(code=1)


    except (PracticeToolError, NetworkError, SSHCommandError) as e:
        console.print(f"\n[bold red]:rotating_light: Error during user setup:[/bold red]\n{e}", style="red")
        raise typer.Exit(code=1)
    except typer.Exit:
        raise # Propagate typer exits cleanly
    except Exception as e:
        console.print(f"\n[bold red]:rotating_light: An unexpected critical error occurred:[/]", style="red")
        if RICH_AVAILABLE: console.print_exception(show_locals=True)
        else: traceback.print_exc()
        raise typer.Exit(code=2)
    finally:
        console.print("\n[dim]Attempting graceful VM shutdown...[/]")
        if domain and domain.isActive():
            try:
                # Check if domain object is still valid before calling shutdown
                if is_domain_valid(domain): # Assumes is_domain_valid helper exists or add it
                    shutdown_vm(domain)
                else:
                    console.print("[yellow]Warning:[/yellow] Domain object became invalid before cleanup shutdown.", style="yellow")
            except PracticeToolError as shutdown_err:
                 console.print(f"[yellow]Warning:[/yellow] Failed to shutdown VM during cleanup: {shutdown_err}", style="yellow")
            except Exception as shutdown_unexpected_err:
                 console.print(f"[yellow]Warning:[/yellow] Unexpected error during cleanup shutdown: {shutdown_unexpected_err}", style="yellow")
        elif domain and not domain.isActive():
             console.print("[dim]VM already shut down.[/]")

        close_libvirt(conn)
        console.rule("[bold]User Setup Workflow Finished[/]", style="blue")

# Helper function needed in finally block (add this somewhere in your script if not present)
def is_domain_valid(dom: Optional[libvirt.virDomain]) -> bool:
    if not dom: return False
    try: dom.info(); return True # Simple check
    except libvirt.libvirtError as le:
         # Define VIR_ERR_INVALID_DOMAIN if not already defined globally
         VIR_ERR_INVALID_DOMAIN = getattr(libvirt, 'VIR_ERR_INVALID_DOMAIN', -1)
         if le.get_error_code() == VIR_ERR_INVALID_DOMAIN and VIR_ERR_INVALID_DOMAIN != -1: return False
         return False # Assume invalid on other errors too
    except Exception: return False # Assume invalid on unexpected errors

@app.command(name="run-challenge")
def run_challenge_workflow(
    challenge_id: Annotated[str, typer.Argument(help="The ID of the challenge to run (must match 'id' in a YAML file).")],
    vm_name: Annotated[str, typer.Option("--vm", help="Name of the libvirt VM to use.")] = Config.DEFAULT_VM_NAME,
    snapshot_name: Annotated[str, typer.Option("--snap", help="Name for the temporary VM snapshot.")] = Config.DEFAULT_SNAPSHOT_NAME,
    challenges_dir: Annotated[Path, typer.Option("--challenges-dir", "-d",
        help="Directory containing challenge YAML files.",
        exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True
    )] = Config.DEFAULT_CHALLENGES_DIR,
    ssh_user: Annotated[str, typer.Option("--user", help="SSH username inside the VM.")] = Config.DEFAULT_SSH_USER,
    ssh_key: Annotated[Path, typer.Option("--key",
        help="Path to the SSH private key file.",
        exists=True, file_okay=True, dir_okay=False, readable=True # Typer checks existence/readability
     )] = Config.DEFAULT_SSH_KEY_PATH,
    simulate_user: Annotated[bool, typer.Option("--simulate/--no-simulate", help="Run 'user_action_simulation' command automatically instead of pausing.")] = False,
    keep_snapshot: Annotated[bool, typer.Option("--keep-snapshot", help="Do not delete the snapshot after running (useful for debugging).")] = False,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Print detailed command output during setup and validation.")] = False,
    libvirt_uri: Annotated[str, typer.Option("--uri", help="Libvirt connection URI.")] = Config.LIBVIRT_URI
):
    """Runs a challenge: snapshot VM, start, setup, prompt/simulate user, validate, cleanup."""
    console.rule(f"[bold green]Starting Challenge: [cyan]{challenge_id}[/cyan][/]", style="green")
    conn: Optional[libvirt.virConnect] = None
    domain: Optional[libvirt.virDomain] = None
    vm_ip: Optional[str] = None
    snapshot_created = False
    challenge: Optional[Dict] = None
    challenge_passed = False
    current_score = 0
    hints_used_count = 0
    total_hint_cost = 0

    # Resolve and validate key path (including permissions) early
    try:
        ssh_key_path = _validate_ssh_key(ssh_key)
    except PracticeToolError as key_err:
         console.print(f"[bold red]:x: SSH Key Error:[/bold red] {key_err}", style="red")
         raise typer.Exit(code=1)

    try:
        # --- 0. Load Challenges & Select Target Challenge ---
        challenges = load_challenges_from_dir(challenges_dir) # Handles validation errors internally
        if not challenges: raise PracticeToolError("No valid challenges were loaded.") # Abort if none loaded

        challenge = challenges.get(challenge_id)
        if not challenge:
             ids_text = "\n".join([f"- {cid}" for cid in sorted(challenges.keys())]) or "[i]None[/]"
             panel_content = f"[bold red]Error:[/bold red] Challenge ID '[yellow]{challenge_id}[/]' not found among valid challenges in '{challenges_dir}'.\n\n[bold]Available valid challenges:[/]\n{ids_text}"
             if RICH_AVAILABLE: console.print(Panel(panel_content, title="[bold red]Challenge Not Found[/]", border_style="red"))
             else: console.print(panel_content)
             raise typer.Exit(code=1)

        current_score = challenge['score'] # Already validated int

        # --- 1. Connect to Libvirt & Find VM ---
        Config.LIBVIRT_URI = libvirt_uri # Update URI if passed as option
        conn = connect_libvirt()
        domain = find_vm(conn, vm_name) # Raises VMNotFoundError if not found

        # --- 2. Snapshot Management: Ensure Clean Slate ---
        console.print(f"\n:mag_right: Checking for existing snapshot '[cyan]{snapshot_name}[/cyan]'...")
        try:
            existing_snapshot = domain.snapshotLookupByName(snapshot_name, 0)
            console.print(f"  :warning: Found existing snapshot '[cyan]{snapshot_name}[/cyan]'. Attempting to delete it first...")
            # delete_external_snapshot handles VM shutdown if needed
            delete_external_snapshot(domain, snapshot_name) # Raises SnapshotOperationError on failure
            list_snapshots(domain) # Show state after deletion attempt
        except libvirt.libvirtError as e:
            # Only ignore "snapshot not found" error, raise others
            if e.get_error_code() != VIR_ERR_NO_DOMAIN_SNAPSHOT or VIR_ERR_NO_DOMAIN_SNAPSHOT == -1:
                 raise SnapshotOperationError(f"Error checking/deleting existing snapshot '{snapshot_name}': {e}") from e
            console.print(f"  [dim]No conflicting snapshot found. Proceeding.[/]")
        except SnapshotOperationError as delete_err:
             # Propagate error from delete_external_snapshot
             raise SnapshotOperationError(f"Failed to delete existing snapshot '{snapshot_name}': {delete_err}. Aborting.") from delete_err

        # Create the fresh snapshot for this run
        create_external_snapshot(domain, snapshot_name) # Raises SnapshotOperationError on failure
        snapshot_created = True
        list_snapshots(domain) # Show state after creation

        # --- 3. Start VM, Get IP, Wait for SSH ---
        start_vm(domain) # Handles already running, raises PracticeToolError on failure
        vm_ip = get_vm_ip(conn, domain) # Raises NetworkError on failure
        wait_for_vm_ready(vm_ip, ssh_user, ssh_key_path, timeout=Config.VM_READINESS_TIMEOUT_SECONDS) # Raises NetworkError on timeout/failure

        # --- 4. Display Challenge Info ---
        console.rule(f"[bold yellow]Challenge: {challenge.get('name', 'N/A')} ([cyan]{challenge_id}[/cyan])[/]", style="yellow")
        if RICH_AVAILABLE:
            info_table = Table.grid(padding=(0, 1))
            info_table.add_column(style="bold")
            info_table.add_column()
            info_table.add_row("Category:", f"[yellow]{challenge.get('category', 'N/A')}[/]")
            info_table.add_row("Difficulty:", f"[green]{challenge.get('difficulty', 'N/A')}[/]")
            info_table.add_row("Max Score:", f"[blue]{challenge['score']}[/]")
            if challenge.get('concepts'):
                info_table.add_row("Concepts:", f"[dim]{', '.join(challenge['concepts'])}[/]")
            console.print(info_table)
            console.print(Panel(Markdown(challenge.get('description', '[i]No description provided.[/]')), title="Objective", border_style="cyan"))
        else: # Basic fallback
            console.print(f"Category: {challenge.get('category', 'N/A')}")
            console.print(f"Difficulty: {challenge.get('difficulty', 'N/A')}")
            console.print(f"Max Score: {challenge['score']}")
            if challenge.get('concepts'): console.print(f"Concepts: {', '.join(challenge['concepts'])}")
            console.print("\n--- Objective ---")
            console.print(challenge.get('description', 'No description provided.'))
            console.print("--- End Objective ---")

        # --- 5. Run Setup Steps ---
        setup_steps = challenge.get("setup", []) # Already validated list
        if setup_steps:
             console.rule("[bold]Challenge Setup[/]", style="blue")
             for i, step in enumerate(setup_steps):
                 step_type = step.get("type")
                 setup_title = f"Setup Step {i+1}: [bold cyan]{step_type}[/]"
                 if step_type == "run_command":
                     command = step.get("command")
                     if not command: raise ChallengeLoadError(f"Setup step {i+1} (run_command) in challenge '{challenge_id}' is missing 'command'.")

                     panel_content = f"Executing: `{command}`"
                     if RICH_AVAILABLE: console.print(Panel(panel_content, title=setup_title, border_style="magenta", expand=False))
                     else: console.print(f"--- {setup_title} ---\n{panel_content}\n------")

                     if verbose: console.print("[yellow]Running setup command (Ensure challenge source is trusted!)[/]", style="yellow")

                     try:
                         setup_result = run_ssh_command(vm_ip, ssh_user, ssh_key_path, command, verbose=False)
                     except SSHCommandError as e:
                          # Abort challenge if setup SSH command fails to execute
                          raise PracticeToolError(f"Challenge setup failed: Error executing command '{command}': {e}") from e

                     if verbose: console.print(format_ssh_output(setup_result, command))

                     # CRITICAL FIX: Abort if setup command has error OR non-zero exit status
                     exec_error = setup_result.get('error')
                     exit_status = setup_result.get('exit_status', -1)
                     if exec_error or exit_status != 0:
                          details = exec_error or f"Exited with status {exit_status}"
                          raise PracticeToolError(f"Challenge setup failed: Command '{command}' did not succeed ({details}). Aborting.")

                     console.print(f"[green]:heavy_check_mark: Setup command successful.[/]")

                 # --- Placeholder for other setup types ---
                 # elif step_type == "copy_file":
                 #    # Needs implementation using Paramiko SFTP client
                 #    console.print(f"[yellow]Setup type '{step_type}' not yet implemented.[/]", style="yellow")
                 # elif step_type == "ensure_service_status":
                 #    # Needs implementation using systemctl over SSH
                 #    console.print(f"[yellow]Setup type '{step_type}' not yet implemented.[/]", style="yellow")
                 else:
                     raise ChallengeLoadError(f"Unsupported setup step type '{step_type}' in challenge '{challenge_id}'.")
             console.rule("[bold]Setup Complete[/]", style="blue")
        else:
            console.print("[dim]No setup steps defined for this challenge.[/]")

        # --- 6. User Action / Simulation ---
        console.rule("[bold]User Interaction[/]", style="green")
        if simulate_user:
             console.print(":robot: Simulating user action ([bold]--simulate[/] flag)...")
             sim_command = challenge.get("user_action_simulation")
             if sim_command:
                 panel_content = f"Executing simulation: `{sim_command}`"
                 if RICH_AVAILABLE: console.print(Panel(panel_content, title="Simulation Command", border_style="magenta", expand=False))
                 else: console.print(f"--- Simulation ---\n{panel_content}\n------")

                 try:
                     sim_result = run_ssh_command(vm_ip, ssh_user, ssh_key_path, sim_command, verbose=False)
                     if verbose: console.print(format_ssh_output(sim_result, sim_command))

                     # Warn on simulation failure, but don't abort
                     if sim_result.get('error') or sim_result.get('exit_status', -1) != 0:
                          err_details = sim_result.get('error') or f"Exit status: {sim_result.get('exit_status', 'N/A')}"
                          console.print(f"[yellow]Warning:[/yellow] User action simulation command failed: '{sim_command}' ({err_details}). Validation might fail.", style="yellow")
                     else:
                          console.print("[green]:heavy_check_mark: Simulation command successful.[/]")
                 except SSHCommandError as e:
                      # Also warn if SSH execution itself fails during simulation
                      console.print(f"[yellow]Warning:[/yellow] Failed to execute simulation command '{sim_command}': {e}. Validation might fail.", style="yellow")
             else:
                 console.print("[dim]No 'user_action_simulation' defined in challenge.[/]")
        else:
            # Display connection info and objective reminder
            connect_cmd = f"ssh {ssh_user}@{vm_ip} -i {ssh_key_path}"
            action_panel_content = Text.assemble(
                Text.from_markup("[bold]Connect to the VM:[/bold]\n"),
                f"`{connect_cmd}`\n\n",
                Text.from_markup("[bold]Your Objective Reminder:[/bold]\n"),
                challenge.get('description', 'N/A') # Already displayed above, but good reminder
            ) if RICH_AVAILABLE else f"Connect: {connect_cmd}\nObjective: {challenge.get('description', 'N/A')}"

            if RICH_AVAILABLE: console.print(Panel(action_panel_content, title=":keyboard: Your Turn! Perform the actions on the VM.", border_style="green", expand=False))
            else: console.print(f"\n--- Your Turn ---\n{action_panel_content}\n------")

            # Hint System
            available_hints = challenge.get("hints", []) # Already validated list
            if available_hints:
                 console.print("\n") # Spacer before hint prompt
                 remaining_hints = list(available_hints) # Copy to modify
                 while remaining_hints:
                      hint_prompt = f":bulb: Show hint? ({len(remaining_hints)} remaining, Current Score: {current_score})"
                      show_hint = Confirm.ask(hint_prompt, default=False)
                      if show_hint:
                          hint_data = remaining_hints.pop(0) # Get and remove first hint
                          hint_text = hint_data.get('text', '[i]No text[/]')
                          hint_cost = hint_data.get('cost', 0) # Already int

                          hint_panel_content = Markdown(hint_text) if RICH_AVAILABLE else hint_text
                          hint_title = f"Hint #{hints_used_count + 1} (Cost: {hint_cost})"
                          if RICH_AVAILABLE: console.print(Panel(hint_panel_content, title=hint_title, border_style="yellow", expand=False))
                          else: console.print(f"--- {hint_title} ---\n{hint_panel_content}\n------")

                          hints_used_count += 1
                          total_hint_cost += hint_cost
                          current_score = max(0, challenge['score'] - total_hint_cost) # Recalculate from base score
                          console.print(f"  -> [bold]Current Score Potential:[/bold] [blue]{current_score}[/]")
                      else:
                          console.print("[dim]Skipping remaining hints.[/]")
                          break # Stop asking for hints
                 if not remaining_hints:
                      console.print("[dim]All hints shown.[/]")

            # Wait for user confirmation to proceed
            Prompt.ask("\n:arrow_forward: Press Enter when ready to validate your work")

        # --- 7. Validation ---
        console.rule("[bold]Challenge Validation[/]", style="blue")
        validation_steps = challenge.get("validation") # Already validated non-empty list
        all_validations_passed = True

        for i, step in enumerate(validation_steps):
            try:
                # Security reminder for verbose mode
                if verbose and step.get("type") == "run_command" and "command" in step:
                     console.print(f"[dim]Executing validation command: '{step['command']}'[/]")

                execute_validation_step(i + 1, step, vm_ip, ssh_user, ssh_key_path, verbose)

            except ChallengeValidationError:
                # execute_validation_step already printed the failure panel
                all_validations_passed = False
                # Stop validation on first failure for clearer results
                console.print("[yellow]Stopping validation due to step failure.[/]", style="yellow")
                break
            except PracticeToolError as tool_err: # Catch unexpected tool errors during validation
                 console.print(f"[bold red]:x: Tool Error during validation step {i+1}:[/bold red] {tool_err}", style="red")
                 all_validations_passed = False
                 break


        # --- 8. Results ---
        console.rule("[bold]Challenge Results[/]", style="magenta")
        result_panel_title = ""
        result_panel_style = ""
        final_score = 0
        if all_validations_passed:
            final_score = current_score # Score after potential hint deductions
            result_panel_title="[bold green]Success![/]"
            result_panel_style="green"
            challenge_passed = True
        else:
            final_score = 0 # Failed challenges get 0 score
            result_panel_title="[bold red]Failure[/]"
            result_panel_style="red"

        # Build result table/text
        result_content: Any
        if RICH_AVAILABLE:
            result_table = Table.grid(padding=(0, 2))
            result_table.add_column(style="bold")
            result_table.add_column()
            result_table.add_row("Challenge:", f"[cyan]{challenge.get('name', challenge_id)}[/cyan]")
            result_table.add_row("Hints Used:", f"{hints_used_count} ([dim]Cost: {total_hint_cost}[/])")
            if challenge_passed:
                final_score_text = f"[bold green]{final_score}[/] / {challenge['score']}"
                result_table.add_row("Status:", "[bold green]:trophy: PASSED! :trophy:[/]")
                result_table.add_row("Final Score:", final_score_text)
                flag = challenge.get("flag")
                if flag: result_table.add_row("Flag:", f"[bold magenta]{flag}[/]")
            else:
                final_score_text = f"[bold red]{final_score}[/] / {challenge['score']}"
                result_table.add_row("Status:", "[bold red]:cross_mark: FAILED :cross_mark:[/]")
                result_table.add_row("Final Score:", final_score_text)
            result_content = result_table
        else: # Basic text fallback
            result_lines = [
                f"Challenge: {challenge.get('name', challenge_id)}",
                f"Hints Used: {hints_used_count} (Cost: {total_hint_cost})",
                f"Status: {'PASSED' if challenge_passed else 'FAILED'}",
                f"Final Score: {final_score} / {challenge['score']}"
            ]
            if challenge_passed and challenge.get("flag"): result_lines.append(f"Flag: {challenge['flag']}")
            result_content = "\n".join(result_lines)


        if RICH_AVAILABLE: console.print(Panel(result_content, title=result_panel_title, border_style=result_panel_style, expand=False))
        else: console.print(f"\n--- {result_panel_title} ---\n{result_content}\n------")

        console.print("\n>>> Practice session finished. <<<")

    # --- 9. Exception Handling for Workflow ---
    except (PracticeToolError, SnapshotOperationError, NetworkError, SSHCommandError, ChallengeLoadError) as e:
        # Catch specific operational errors
        console.print(f"\n[bold red]:rotating_light: Error during challenge execution:[/bold red]\n{e}", style="red")
        # Optionally add traceback for debugging these expected errors if needed
        # if RICH_AVAILABLE: console.print_exception(show_locals=False)
        raise typer.Exit(code=1)
    except typer.Exit:
         # Allow clean exit from Typer (e.g., challenge not found)
         raise
    except KeyboardInterrupt:
         console.print("\n[yellow]Challenge run interrupted by user.[/]", style="yellow")
         # Allow finally block to run for cleanup, exit code handled by finally
         # Set flag to indicate interruption for cleanup logic? Not strictly needed now.
         raise typer.Exit(code=130) # Standard exit code for Ctrl+C
    except Exception as e:
        # Catch unexpected critical errors
        console.print(f"\n[bold red]:rotating_light: An unexpected critical error occurred:[/]", style="red")
        if RICH_AVAILABLE: console.print_exception(show_locals=True) # Show locals for unexpected errors
        else: traceback.print_exc()
        raise typer.Exit(code=2) # Different exit code for unexpected errors

    # --- 10. Cleanup Phase (Always Runs) ---
    finally:
        console.rule("[bold]Cleanup Phase[/]", style="dim")
        cleanup_errors = []
        domain_still_valid = domain is not None # Track if domain object should be usable

        # Function to check if domain object is still valid (avoids repeating try/except)
        def is_domain_valid(dom: Optional[libvirt.virDomain]) -> bool:
            if not dom: return False
            try: dom.info(); return True # Simple check
            except libvirt.libvirtError as le:
                 if le.get_error_code() == VIR_ERR_INVALID_DOMAIN and VIR_ERR_INVALID_DOMAIN != -1: return False
                 # Log other errors checking validity? Maybe too verbose.
                 return False # Assume invalid on other errors too
            except Exception: return False # Assume invalid on unexpected errors

        domain_still_valid = is_domain_valid(domain)

        try:
            # Revert Snapshot (if created and domain is usable)
            if snapshot_created and domain_still_valid:
                console.print(f"[dim]Attempting to revert snapshot '{snapshot_name}'...[/]")
                try:
                    revert_to_snapshot(domain, snapshot_name) # Handles VM shutdown internally
                    time.sleep(3) # Wait after revert
                    domain_still_valid = is_domain_valid(domain) # Re-check validity after revert
                except (SnapshotOperationError, PracticeToolError) as revert_err:
                    cleanup_errors.append(f"Failed to revert snapshot: {revert_err}")
                    domain_still_valid = is_domain_valid(domain) # Re-check validity
                except Exception as revert_unexpected_err:
                     cleanup_errors.append(f"Unexpected error during snapshot revert: {revert_unexpected_err}")
                     domain_still_valid = False # Assume potentially bad state
            elif not snapshot_created:
                 console.print("[dim]Snapshot was not created, skipping revert.[/]")
            elif not domain_still_valid:
                 console.print("[dim]Domain object invalid/inaccessible, skipping revert.[/]")

            # Delete Snapshot (if created, not keeping, and domain usable)
            if snapshot_created and not keep_snapshot and domain_still_valid:
                 console.print(f"[dim]Attempting to delete snapshot '{snapshot_name}'...[/]")
                 try:
                     delete_external_snapshot(domain, snapshot_name) # Handles VM shutdown internally
                     list_snapshots(domain) # Show final snapshot state
                 except (SnapshotOperationError, PracticeToolError) as delete_err:
                     cleanup_errors.append(f"Failed to delete snapshot: {delete_err}")
                 except Exception as delete_unexpected_err:
                     cleanup_errors.append(f"Unexpected error during snapshot delete: {delete_unexpected_err}")
            elif not snapshot_created:
                 console.print("[dim]Snapshot was not created, skipping deletion.[/]")
            elif keep_snapshot:
                 console.print(f":information_source: Skipping snapshot deletion as requested ([bold]--keep-snapshot[/]). VM state reverted to '{snapshot_name}'.")
            elif not domain_still_valid:
                 console.print("[dim]Domain object invalid/inaccessible, skipping snapshot deletion.[/]")

        except Exception as cleanup_outer_err:
            # Catch errors in the cleanup logic/structure itself
            cleanup_errors.append(f"Unexpected error during cleanup block structure: {cleanup_outer_err}")
            console.print("[bold red]Unexpected error during cleanup structure:[/]", style="red")
            if RICH_AVAILABLE: console.print_exception(show_locals=False)
            else: traceback.print_exc()
        finally:
            # Always try to close the connection
            close_libvirt(conn)

            if cleanup_errors:
                error_text = "\n".join([f"- {err}" for err in cleanup_errors])
                error_title = "[bold red]Cleanup Issues Encountered[/]"
                if RICH_AVAILABLE: console.print(Panel(error_text, title=error_title, border_style="red"))
                else: console.print(f"\n--- {error_title} ---\n{error_text}\n------")
            else:
                 console.print("[green]:broom: Cleanup finished.[/]")

            console.rule(f"[bold green]Challenge Workflow Finished: [cyan]{challenge_id}[/cyan][/]", style="green")


# --- Part 16: Typer Commands (Challenge Management Sub-App) ---
@challenge_app.command("create-template")
def create_challenge_template(
    output_file: Annotated[Path, typer.Option("--output", "-o", help="Path to save the template YAML file.", dir_okay=False, writable=True)] = Path("challenge_template.yaml")
):
    """Creates a template YAML file for defining a new challenge."""
    try:
        if output_file.exists():
            overwrite = Confirm.ask(f"File '[cyan]{output_file.resolve()}[/cyan]' already exists. Overwrite?", default=False)
            if not overwrite:
                console.print("[yellow]Aborted.[/]")
                raise typer.Exit()

        with open(output_file, "w", encoding='utf-8') as f:
            f.write(CHALLENGE_TEMPLATE)

        console.print(f"\nChallenge template written to: [blue underline]{output_file.resolve()}[/]")
        # Display template content using Rich Syntax if available
        if RICH_AVAILABLE:
            try: # Guard against potential errors reading back the file immediately
                template_content = output_file.read_text(encoding='utf-8')
                syntax = Syntax(template_content, "yaml", theme="default", line_numbers=True, word_wrap=False)
                console.print(Panel(syntax, title="Template Content", border_style="green", expand=False))
            except Exception as read_err:
                 console.print(f"[yellow]Could not display template content: {read_err}[/]", style="yellow")
        else:
            console.print(f"\n--- Template Content ---\n{CHALLENGE_TEMPLATE}\n------") # Show fallback

        console.print("\n:pencil: Edit this file to define your challenge.")
        console.print(Panel("[bold red]SECURITY WARNING:[/bold red] Be extremely careful with 'run_command' steps in setup/validation.", border_style="red"))

    except IOError as e:
        console.print(f"[bold red]:x: Error writing template file '{output_file}': {e}[/]", style="red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]:x: An unexpected error occurred: {e}[/]", style="red")
        raise typer.Exit(code=1)


@challenge_app.command("validate")
def validate_challenge_yaml(
    file_path: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True, help="Path to the challenge YAML file to validate.")]
):
    """Validates the structure and basic syntax of a challenge YAML file."""
    console.print(f":magnifying_glass_right: Validating challenge file: [blue underline]{file_path}[/]")
    is_valid = False
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            challenge_data = yaml.safe_load(content) # Load first to catch YAML syntax errors

        # Display YAML content with syntax highlighting
        if RICH_AVAILABLE:
            syntax = Syntax(content, "yaml", theme="default", line_numbers=True, word_wrap=False)
            console.print(Panel(syntax, title=f"Content of '{file_path.name}'", border_style="dim"))
        else:
            console.print(f"\n--- Content of '{file_path.name}' ---\n{content}\n------------------------------")

        if not isinstance(challenge_data, dict):
            console.print(Panel("[bold red]Error:[/bold red] Root content is not a valid YAML dictionary (object).", title="Validation Failed", border_style="red"))
            raise typer.Exit(code=1)

        # Perform detailed structure validation
        errors = validate_challenge_structure(challenge_data, file_path.name)

        if errors:
            error_text = "\n".join([f"- {error}" for error in errors])
            if RICH_AVAILABLE: console.print(Panel(f"[bold red]Validation Failed:[/]\n{error_text}", title="Validation Results", border_style="red"))
            else: console.print(f"\n--- Validation Failed ---\n{error_text}\n------")
            raise typer.Exit(code=1)
        else:
            if RICH_AVAILABLE: console.print(Panel("[bold green]:heavy_check_mark: Validation Succeeded![/]", title="Validation Results", border_style="green"))
            else: console.print("\n--- Validation Succeeded! ---")
            is_valid = True

    except yaml.YAMLError as e:
        if RICH_AVAILABLE: console.print(Panel(f"[bold red]Error parsing YAML file '{file_path.name}':[/]\n{e}", title="YAML Parsing Error", border_style="red"))
        else: console.print(f"\n--- YAML Parsing Error ---\nError parsing YAML file '{file_path.name}':\n{e}\n------")
        raise typer.Exit(code=1)
    except FileNotFoundError: # Should be caught by Typer's exists=True, but belt-and-suspenders
        console.print(f"[bold red]Error:[/bold red] File not found: '{file_path}'", style="red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]:x: An unexpected error occurred during validation: {e}[/]", style="red")
        if RICH_AVAILABLE: console.print_exception(show_locals=False)
        else: traceback.print_exc()
        raise typer.Exit(code=1)

    # Ensure exit code reflects validation status even if no exception occurred
    if not is_valid:
        raise typer.Exit(code=1)


# -- Part 17:--- Main Execution Guard ---

if __name__ == "__main__":
    # Dependency checks already performed by imports at the top

    # Check default SSH key validity before Typer parsing (only checks default)
    try:
        _validate_ssh_key(Config.DEFAULT_SSH_KEY_PATH)
    except PracticeToolError as key_err:
        # Non-fatal warning if default key is bad, user might specify --key
        console.print(f"[yellow]Warning:[/yellow] Default SSH key issue: {key_err}", style="yellow")
        console.print("[yellow]         Specify a valid key using --key if needed.[/]", style="yellow")
    except Exception as key_check_err:
        # Catch potential errors during path resolution/check itself
        console.print(f"[yellow]Warning:[/yellow] Could not check default SSH key '{Config.DEFAULT_SSH_KEY_PATH}': {key_check_err}", style="yellow")

    # Check if default challenges directory exists
    if not Config.DEFAULT_CHALLENGES_DIR.exists():
         console.print(f"[yellow]Warning:[/yellow] Default challenges directory '{Config.DEFAULT_CHALLENGES_DIR}' not found.", style="yellow")
         console.print("[yellow]         Create it or specify a directory using --challenges-dir.", style="yellow")

    # Run the Typer app
    app()
    