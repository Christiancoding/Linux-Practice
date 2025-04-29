"""QEMU Guest Agent interaction functions."""

import json
import time
import libvirt
from typing import Optional, Any

from .console import console
from .exceptions import AgentCommandError
from .config import VIR_ERR_AGENT_UNRESPONSIVE, VIR_ERR_OPERATION_TIMEOUT, VIR_ERR_OPERATION_INVALID, VIR_ERR_ARGUMENT_UNSUPPORTED

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
