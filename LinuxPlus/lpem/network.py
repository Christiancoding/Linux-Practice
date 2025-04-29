"""Network and SSH functions for the LPEM tool."""

import time
import socket
import stat
import paramiko
import shlex
from pathlib import Path
from typing import Dict, Any, Optional

import libvirt

from .config import Config, VIR_ERR_NO_DOMAIN
from .console import console, Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from .exceptions import NetworkError, SSHCommandError, PracticeToolError

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
             from .config import VIR_ERR_AGENT_UNRESPONSIVE, VIR_ERR_OPERATION_TIMEOUT, VIR_ERR_OPERATION_INVALID, VIR_ERR_ARGUMENT_UNSUPPORTED
             if err_code not in [VIR_ERR_AGENT_UNRESPONSIVE, VIR_ERR_OPERATION_TIMEOUT, VIR_ERR_OPERATION_INVALID, VIR_ERR_ARGUMENT_UNSUPPORTED]:
                 console.print(f"  [yellow]Libvirt error querying agent interfaces: {e}[/]", style="yellow")
        except Exception as e:
             console.print(f"  [yellow]Unexpected error getting IP via agent (interfaceAddresses): {e}[/]", style="yellow")

    # Fallback: Try guest-network-get-interfaces command via agent
    from .qemu_agent import qemu_agent_command
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
        import xml.etree.ElementTree as ET
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
    from .console import Panel, Text, RICH_AVAILABLE
    if RICH_AVAILABLE:
        return Panel(Text(content, no_wrap=False), title=title, border_style=border_style, expand=False)
    else:
        return f"--- {title} ---\n{content}\n--- End {title} ---"
