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