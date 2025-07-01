"""VM snapshot management functions."""

import time
import xml.etree.ElementTree as ET
import libvirt
from pathlib import Path
from typing import List, Tuple, Optional

from .console import console, Table, Panel, Syntax
from .exceptions import SnapshotOperationError, PracticeToolError
from .config import (
    VIR_ERR_NO_DOMAIN, VIR_ERR_NO_DOMAIN_SNAPSHOT, VIR_ERR_OPERATION_INVALID, 
    VIR_ERR_AGENT_UNRESPONSIVE, VIR_ERR_CONFIG_EXIST
)
from .qemu_agent import qemu_agent_fsfreeze, qemu_agent_fsthaw
from .vm import shutdown_vm

def _generate_snapshot_xml(domain: libvirt.virDomain, snapshot_name: str, agent_frozen: bool) -> Tuple[str, List[str]]:
    """Generates the snapshot XML and returns XML string and list of snapshot disk file paths."""
    snapshot_disk_files = []
    try:
        raw_xml = domain.XMLDesc(0)
        tree = ET.fromstring(raw_xml)
        disks_xml = ""
        disk_count = 0
        
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
                try: 
                    domain.snapshotLookupByName(snapshot_name, 0)
                    snap_exists_after_fail = True
                except libvirt.libvirtError: 
                    pass
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

    from .console import Panel, Table
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
