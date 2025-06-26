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
