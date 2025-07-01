"""VM lifecycle management functions."""

import libvirt
import time
from typing import Optional

from .config import Config, VIR_ERR_NO_DOMAIN
from .console import console
from .exceptions import PracticeToolError, LibvirtConnectionError, VMNotFoundError

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

def list_vms(conn: libvirt.virConnect):
    """Lists all defined VMs (active and inactive) using Rich Table."""
    if not conn:
        console.print("[bold red]:x: Error: Invalid libvirt connection passed to list_vms.[/]", style="red")
        return

    from .console import Table
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
            from .console import Progress, SpinnerColumn, TextColumn
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
                from .console import Progress, TextColumn, BarColumn, TimeElapsedColumn
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
        from .config import VIR_ERR_OPERATION_INVALID
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

def is_domain_valid(dom: Optional[libvirt.virDomain]) -> bool:
    """Check if a domain object is still valid and usable."""
    if not dom: return False
    try: 
        dom.info()
        return True # Simple check
    except libvirt.libvirtError as le:
         from .config import VIR_ERR_INVALID_DOMAIN
         if le.get_error_code() == VIR_ERR_INVALID_DOMAIN and VIR_ERR_INVALID_DOMAIN != -1: 
             return False
         return False # Assume invalid on other errors too
    except Exception: 
        return False # Assume invalid on unexpected errors
