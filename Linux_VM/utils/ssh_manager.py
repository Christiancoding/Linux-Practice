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
