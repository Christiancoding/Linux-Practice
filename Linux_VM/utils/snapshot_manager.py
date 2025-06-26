#!/usr/bin/env python3
"""
Snapshot Management Module

Comprehensive VM snapshot operations including external snapshot creation,
reversion, and QEMU guest agent filesystem operations for consistent snapshots.
"""

import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

# Third-party imports
try:
    import libvirt
except ImportError:
    raise ImportError("libvirt-python is required. Install with: pip install libvirt-python")

# Local imports
from .console_helper import console, RICH_AVAILABLE
from .exceptions import (
    PracticeToolError, 
    SnapshotOperationError, 
    AgentCommandError
)
from .config import config

# Set up module logger
logger = logging.getLogger(__name__)

# Libvirt error codes for specific error handling
try:
    VIR_ERR_CONFIG_EXIST = libvirt.VIR_ERR_CONFIG_EXIST
    VIR_ERR_AGENT_UNRESPONSIVE = libvirt.VIR_ERR_AGENT_UNRESPONSIVE  
    VIR_ERR_OPERATION_INVALID = libvirt.VIR_ERR_OPERATION_INVALID
    VIR_ERR_NO_DOMAIN_SNAPSHOT = libvirt.VIR_ERR_NO_DOMAIN_SNAPSHOT
except AttributeError:
    # Fallback for older libvirt versions
    VIR_ERR_CONFIG_EXIST = -1
    VIR_ERR_AGENT_UNRESPONSIVE = -1
    VIR_ERR_OPERATION_INVALID = -1
    VIR_ERR_NO_DOMAIN_SNAPSHOT = -1

if RICH_AVAILABLE:
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax


class SnapshotManager:
    """
    Advanced VM snapshot management with external snapshot support
    and QEMU guest agent integration for filesystem consistency.
    """
    
    def __init__(self):
        """Initialize the snapshot manager."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    # --- QEMU Guest Agent Functions ---
    
    def qemu_agent_fsfreeze(self, domain: libvirt.virDomain) -> bool:
        """
        Freeze filesystems using QEMU Guest Agent for snapshot consistency.
        
        Args:
            domain: The libvirt domain object
            
        Returns:
            bool: True if freeze was successful, False otherwise
        """
        if not domain:
            self.logger.error("Invalid domain provided to qemu_agent_fsfreeze")
            return False
            
        try:
            console.print("  :ice_cube: Attempting QEMU Agent filesystem freeze...")
            
            # Execute guest agent filesystem freeze command
            response = domain.qemuAgentCommand(
                '{"execute":"guest-fsfreeze-freeze"}',
                timeout=10,  # 10 second timeout
                flags=0
            )
            
            self.logger.debug(f"Agent fsfreeze response: {response}")
            
            if response is None:
                console.print("  [yellow]:warning: QEMU Agent: Filesystem freeze returned None response.[/]", style="yellow")
                return False
            elif isinstance(response, str):
                # Try to parse JSON response
                try:
                    import json
                    response_data = json.loads(response)
                    frozen_count = response_data.get('return', 0)
                    if frozen_count > 0:
                        console.print(f"  [green]:heavy_check_mark: QEMU Agent: Filesystems frozen successfully (Count: {frozen_count}).[/]")
                        return True
                    else:
                        console.print(f"  [yellow]:warning: QEMU Agent: Filesystem freeze returned no frozen filesystems: {response}[/]", style="yellow")
                        return False
                except (json.JSONDecodeError, KeyError):
                    console.print(f"  [yellow]:warning: QEMU Agent: Filesystem freeze returned unexpected string response: {response}[/]", style="yellow")
                    return False
            elif isinstance(response, dict):
                frozen_count = response.get('return', 0)
                if frozen_count > 0:
                    console.print(f"  [green]:heavy_check_mark: QEMU Agent: Filesystems frozen successfully (Count: {frozen_count}).[/]")
                    return True
                else:
                    console.print(f"  [yellow]:warning: QEMU Agent: Filesystem freeze returned unexpected dict response: {response}[/]", style="yellow")
                    return False
            else:
                console.print(f"  [yellow]:warning: QEMU Agent: Filesystem freeze returned unexpected response type: {type(response)} {response}[/]", style="yellow")
                return False
                
        except libvirt.libvirtError as e:
            error_code = e.get_error_code()
            if error_code == VIR_ERR_AGENT_UNRESPONSIVE and VIR_ERR_AGENT_UNRESPONSIVE != -1:
                console.print("  [yellow]:warning: QEMU Agent: Agent unresponsive, cannot freeze filesystems.[/]", style="yellow")
            else:
                console.print(f"  [yellow]:warning: QEMU Agent: Filesystem freeze failed: {e}[/]", style="yellow")
            self.logger.warning(f"QEMU agent fsfreeze failed: {e}")
            return False
        except Exception as e:
            console.print(f"  [yellow]:warning: QEMU Agent: Unexpected error during filesystem freeze: {e}[/]", style="yellow")
            self.logger.error(f"Unexpected error in qemu_agent_fsfreeze: {e}", exc_info=True)
            return False
    
    def qemu_agent_fsthaw(self, domain: libvirt.virDomain) -> bool:
        """
        Thaw filesystems using QEMU Guest Agent after snapshot creation.
        
        Args:
            domain: The libvirt domain object
            
        Returns:
            bool: True if thaw was successful, False otherwise
        """
        if not domain:
            self.logger.error("Invalid domain provided to qemu_agent_fsthaw")
            return False
            
        try:
            console.print("  :fire: Attempting QEMU Agent filesystem thaw...")
            
            # Execute guest agent filesystem thaw command
            response = domain.qemuAgentCommand(
                '{"execute":"guest-fsfreeze-thaw"}',
                timeout=10,  # 10 second timeout
                flags=0
            )
            
            self.logger.debug(f"Agent fsthaw response: {response}")
            
            if response is None:
                console.print("  [yellow]:warning: QEMU Agent: Filesystem thaw returned None response.[/]", style="yellow")
                return False
            elif isinstance(response, str):
                # Try to parse JSON response
                try:
                    import json
                    response_data = json.loads(response)
                    thawed_count = response_data.get('return', 0)
                    if thawed_count >= 0:
                        console.print(f"  [green]:heavy_check_mark: QEMU Agent: Filesystems thawed successfully (Count: {thawed_count}).[/]")
                        return True
                    else:
                        console.print(f"  [yellow]:warning: QEMU Agent: Filesystem thaw returned unexpected string response: {response}[/]", style="yellow")
                        return False
                except (json.JSONDecodeError, KeyError):
                    console.print(f"  [yellow]:warning: QEMU Agent: Filesystem thaw returned unparseable string response: {response}[/]", style="yellow")
                    return False
            elif isinstance(response, dict):
                thawed_count = response.get('return', 0)
                if thawed_count >= 0:
                    console.print(f"  [green]:heavy_check_mark: QEMU Agent: Filesystems thawed successfully (Count: {thawed_count}).[/]")
                    return True
                else:
                    console.print(f"  [yellow]:warning: QEMU Agent: Filesystem thaw returned unexpected dict response: {response}[/]", style="yellow")
                    return False
            else:
                console.print(f"  [yellow]:warning: QEMU Agent: Filesystem thaw returned unexpected response type: {type(response)} {response}[/]", style="yellow")
                return False
                
        except libvirt.libvirtError as e:
            error_code = e.get_error_code()
            if error_code == VIR_ERR_AGENT_UNRESPONSIVE and VIR_ERR_AGENT_UNRESPONSIVE != -1:
                console.print("  [yellow]:warning: QEMU Agent: Agent unresponsive, cannot thaw filesystems.[/]", style="yellow")
            else:
                console.print(f"  [yellow]:warning: QEMU Agent: Filesystem thaw failed: {e}[/]", style="yellow")
            self.logger.warning(f"QEMU agent fsthaw failed: {e}")
            return False
        except Exception as e:
            console.print(f"  [yellow]:warning: QEMU Agent: Unexpected error during filesystem thaw: {e}[/]", style="yellow")
            self.logger.error(f"Unexpected error in qemu_agent_fsthaw: {e}", exc_info=True)
            return False
    
    # --- Core Snapshot Functions ---
    
    def _generate_snapshot_xml(self, domain: libvirt.virDomain, snapshot_name: str, agent_frozen: bool) -> Tuple[str, List[str]]:
        """
        Generate snapshot XML configuration and return disk file paths.
        
        Args:
            domain: The libvirt domain object
            snapshot_name: Name for the snapshot
            agent_frozen: Whether agent freeze was successful
            
        Returns:
            Tuple[str, List[str]]: XML configuration and list of snapshot disk file paths
            
        Raises:
            SnapshotOperationError: If XML generation fails
        """
        snapshot_disk_files = []
        
        try:
            raw_xml = domain.XMLDesc(0)
            tree = ET.fromstring(raw_xml)
            disks_xml = ""
            disk_count = 0
            
            # Create table for disk planning display
            if RICH_AVAILABLE:
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
                    if target_dev_node is None:
                        continue  # Skip disks without target
                    target_dev = target_dev_node.get('dev')
                    
                    driver_node = device.find('driver')
                    driver_type = driver_node.get('type') if driver_node is not None else 'qcow2'
                    
                    source_file_node = device.find('source')
                    if source_file_node is None or 'file' not in source_file_node.attrib:
                        console.print(f"[yellow]Warning:[/yellow] Disk '{target_dev}' has no source file defined, skipping snapshot for this disk.", style="yellow")
                        continue
                    
                    original_disk_path_str = source_file_node.get('file')
                    original_disk_path = Path(original_disk_path_str).resolve()
                    original_disk_dir = original_disk_path.parent
                    
                    if not original_disk_dir.is_dir():
                        raise SnapshotOperationError(f"Directory '{original_disk_dir}' for base disk '{original_disk_path.name}' (target: {target_dev}) does not exist.")
                    
                    # Generate snapshot file path
                    timestamp_suffix = int(time.time())
                    snapshot_disk_name = f"{original_disk_path.stem}-{snapshot_name}-{timestamp_suffix}.qcow2"
                    snapshot_disk_path = original_disk_dir / snapshot_disk_name
                    snapshot_disk_files.append(str(snapshot_disk_path))
                    
                    # Add disk XML for this device
                    disks_xml += f'    <disk name="{target_dev}" snapshot="external">\n'
                    disks_xml += f'      <source file="{snapshot_disk_path}"/>\n'
                    disks_xml += f'      <driver type="{driver_type}"/>\n'
                    disks_xml += f'    </disk>\n'
                    
                    disk_count += 1
                    
                    # Add to table display
                    if RICH_AVAILABLE:
                        disk_table.add_row(
                            target_dev,
                            original_disk_path.name,
                            snapshot_disk_name
                        )
            
            # Display disk planning table
            if RICH_AVAILABLE and disk_count > 0:
                console.print(disk_table)
            
            if disk_count == 0:
                raise SnapshotOperationError("No eligible disks found for snapshot creation.")
            
            if not disks_xml:
                raise SnapshotOperationError("Failed to generate disk XML for snapshot.")
            
            # Generate final snapshot XML
            snapshot_xml = f"""<domainsnapshot>
  <name>{snapshot_name}</name>
  <description>External snapshot for practice session (Agent Freeze: {agent_frozen})</description>
  <disks>
{disks_xml}  </disks>
</domainsnapshot>"""
            
            self.logger.debug(f"Generated snapshot XML for {disk_count} disks")
            return snapshot_xml, snapshot_disk_files
            
        except ET.ParseError as e:
            raise SnapshotOperationError(f"Error parsing VM XML description: {e}") from e
        except (SnapshotOperationError, PracticeToolError):
            raise
        except Exception as e:
            raise SnapshotOperationError(f"Unexpected error generating snapshot XML: {e}") from e
    
    def create_external_snapshot(self, domain: libvirt.virDomain, snapshot_name: str) -> bool:
        """
        Create an external snapshot with agent-based filesystem freeze/thaw.
        
        Args:
            domain: The libvirt domain object
            snapshot_name: Name for the snapshot
            
        Returns:
            bool: True if snapshot creation was successful
            
        Raises:
            SnapshotOperationError: If snapshot creation fails
        """
        if not domain:
            raise PracticeToolError("Invalid VM domain provided to create_external_snapshot.")
        
        console.rule(f"[bold]Creating EXTERNAL Snapshot: [cyan]{snapshot_name}[/][/]", style="blue")
        
        was_frozen_by_agent = False
        snapshot_files_to_check = []
        
        try:
            # 1. Filesystem Freeze (if VM is running)
            if domain.isActive():
                was_frozen_by_agent = self.qemu_agent_fsfreeze(domain)
                if was_frozen_by_agent:
                    time.sleep(2)  # Give FS time to sync/settle after freeze signal
                else:
                    console.print("[yellow]:warning: Agent freeze failed or unavailable. Snapshot consistency depends on libvirt QUIESCE flag or app quiescing.[/]", style="yellow")
            else:
                console.print("[dim]VM not running, skipping agent filesystem freeze.[/]")
            
            # 2. Generate Snapshot XML
            snapshot_xml, snapshot_files_to_check = self._generate_snapshot_xml(domain, snapshot_name, was_frozen_by_agent)
            
            # 3. Determine Snapshot Flags
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
            
            if snapshot:
                console.print(f"[green]:camera_with_flash: Successfully created external snapshot metadata: '{snapshot.getName()}'[/]")
                return True
            else:
                raise SnapshotOperationError(f"Libvirt snapshotCreateXML returned None unexpectedly for '{snapshot_name}'.")
            
        except libvirt.libvirtError as e:
            err_code = e.get_error_code()
            if err_code == VIR_ERR_CONFIG_EXIST and VIR_ERR_CONFIG_EXIST != -1:
                raise SnapshotOperationError(f"Snapshot metadata '{snapshot_name}' already exists. Delete it first.") from e
            elif err_code == VIR_ERR_AGENT_UNRESPONSIVE and VIR_ERR_AGENT_UNRESPONSIVE != -1 and quiesce_flag_used:
                msg = f"Snapshot creation failed: Libvirt QUIESCE flag requires guest agent interaction, but agent was unresponsive ({e})"
                console.print(f"[bold red]Error:[/bold red] {msg}", style="red")
                raise SnapshotOperationError(msg) from e
            elif err_code == VIR_ERR_OPERATION_INVALID and VIR_ERR_OPERATION_INVALID != -1:
                msg = f"Snapshot creation failed (Operation Invalid): Check snapshot flags and disk configuration. Libvirt error: {e}"
                console.print(f"[bold red]Error:[/bold red] {msg}", style="red")
                raise SnapshotOperationError(msg) from e
            else:
                raise SnapshotOperationError(f"Error creating external snapshot '{snapshot_name}': {e}") from e
        except (SnapshotOperationError, PracticeToolError):
            raise
        except Exception as e:
            raise SnapshotOperationError(f"Unexpected error creating snapshot '{snapshot_name}': {e}") from e
        finally:
            # Thaw filesystem ONLY if freeze was successful
            if was_frozen_by_agent:
                if not self.qemu_agent_fsthaw(domain):
                    console.print("[bold red]:rotating_light: CRITICAL:[/bold red] Filesystem thaw command failed after successful freeze. VM filesystems might be stuck frozen!", style="red")
                    console.print("  Manual intervention (e.g., 'fsfreeze -u /' inside VM or reboot) might be required.", style="red")
            console.rule(f"[bold]End Snapshot Creation[/]", style="blue")
    
    def revert_to_snapshot(self, domain: libvirt.virDomain, snapshot_name: str) -> bool:
        """
        Revert the VM to a previously created snapshot.
        
        Args:
            domain: The libvirt domain object
            snapshot_name: Name of the snapshot to revert to
            
        Returns:
            bool: True if revert was successful
            
        Raises:
            SnapshotOperationError: If snapshot revert fails
        """
        if not domain:
            raise PracticeToolError("Invalid VM domain provided to revert_to_snapshot.")
        
        console.rule(f"[bold]Reverting to Snapshot: [cyan]{snapshot_name}[/][/]", style="blue")
        
        try:
            # 1. Look up the snapshot
            snapshot = domain.snapshotLookupByName(snapshot_name, 0)
            console.print(f"  :mag_right: Found snapshot '{snapshot_name}', attempting revert...")
            
            # 2. Perform the revert
            # Use FORCE flag to revert even if VM state conflicts
            flags = libvirt.VIR_DOMAIN_SNAPSHOT_REVERT_FORCE
            domain.revertToSnapshot(snapshot, flags)
            
            console.print(f"[green]:heavy_check_mark: Successfully reverted to snapshot '{snapshot_name}'[/]")
            return True
            
        except libvirt.libvirtError as e:
            err_code = e.get_error_code()
            if err_code == VIR_ERR_NO_DOMAIN_SNAPSHOT and VIR_ERR_NO_DOMAIN_SNAPSHOT != -1:
                raise SnapshotOperationError(f"Snapshot '{snapshot_name}' not found.") from e
            else:
                raise SnapshotOperationError(f"Error reverting to snapshot '{snapshot_name}': {e}") from e
        except Exception as e:
            raise SnapshotOperationError(f"Unexpected error reverting to snapshot '{snapshot_name}': {e}") from e
        finally:
            console.rule(f"[bold]End Snapshot Revert[/]", style="blue")
    
    def delete_snapshot(self, domain: libvirt.virDomain, snapshot_name: str, delete_children: bool = False) -> bool:
        """
        Delete a snapshot and optionally its children.
        
        Args:
            domain: The libvirt domain object
            snapshot_name: Name of the snapshot to delete
            delete_children: Whether to delete child snapshots
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            SnapshotOperationError: If snapshot deletion fails
        """
        if not domain:
            raise PracticeToolError("Invalid VM domain provided to delete_snapshot.")
        
        console.print(f":wastebasket: Deleting snapshot: [cyan]{snapshot_name}[/]")
        
        try:
            # 1. Look up the snapshot
            snapshot = domain.snapshotLookupByName(snapshot_name, 0)
            
            # 2. Set deletion flags
            flags = libvirt.VIR_DOMAIN_SNAPSHOT_DELETE_METADATA_ONLY
            if delete_children:
                flags |= libvirt.VIR_DOMAIN_SNAPSHOT_DELETE_CHILDREN
            
            # 3. Delete the snapshot
            snapshot.delete(flags)
            
            console.print(f"[green]:heavy_check_mark: Successfully deleted snapshot '{snapshot_name}'[/]")
            return True
            
        except libvirt.libvirtError as e:
            err_code = e.get_error_code()
            if err_code == VIR_ERR_NO_DOMAIN_SNAPSHOT and VIR_ERR_NO_DOMAIN_SNAPSHOT != -1:
                raise SnapshotOperationError(f"Snapshot '{snapshot_name}' not found.") from e
            else:
                raise SnapshotOperationError(f"Error deleting snapshot '{snapshot_name}': {e}") from e
        except Exception as e:
            raise SnapshotOperationError(f"Unexpected error deleting snapshot '{snapshot_name}': {e}") from e
    
    def list_snapshots(self, domain: libvirt.virDomain) -> None:
        """
        List all snapshots for a domain with detailed information.
        
        Args:
            domain: The libvirt domain object
            
        Raises:
            PracticeToolError: If listing snapshots fails
        """
        try:
            snapshot_names = domain.listSnapshotNames(0)
            
            if not snapshot_names:
                if RICH_AVAILABLE:
                    console.print(Panel("[dim]No snapshots found.[/]", title=f"Snapshots for {domain.name()}", border_style="dim", style="dim"))
                else:
                    console.print(f"No snapshots found for {domain.name()}")
                return
            
            if RICH_AVAILABLE:
                table = Table(title=f"Snapshots for {domain.name()}", show_header=True, header_style="bold blue")
                table.add_column("Name", style="cyan")
                table.add_column("Created", style="green")
                table.add_column("State", style="yellow")
                table.add_column("Type", style="magenta")
                table.add_column("Description", style="white")
            
            for name in snapshot_names:
                details = "[dim]N/A[/]"
                creation_time_str = "[dim]N/A[/]"
                state_str = "[dim]N/A[/]"
                type_str = "[dim]Unknown[/]"
                
                try:
                    snapshot = domain.snapshotLookupByName(name, 0)
                    xml_desc = snapshot.getXMLDesc(0)
                    snap_tree = ET.fromstring(xml_desc)
                    
                    creation_time_node = snap_tree.find('creationTime')
                    state_node = snap_tree.find('state')
                    disks_node = snap_tree.find('disks')
                    desc_node = snap_tree.find('description')
                    memory_node = snap_tree.find('memory')
                    
                    is_external = disks_node is not None and any(
                        d.get('snapshot') == 'external' for d in disks_node.findall('disk')
                    )
                    has_memory = memory_node is not None and memory_node.get('snapshot', 'no') != 'no'
                    
                    if creation_time_node is not None and creation_time_node.text.isdigit():
                        try:
                            creation_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(creation_time_node.text)))
                        except ValueError:
                            pass  # Handle potential large timestamps
                    
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
                    if RICH_AVAILABLE:
                        table.add_row(name, creation_time_str, state_str, type_str, details)
                    else:
                        console.print(f"{name}: {creation_time_str} | {state_str} | {type_str} | {details}")
            
            if RICH_AVAILABLE:
                console.print(table)
                
        except libvirt.libvirtError as e:
            raise PracticeToolError(f"Error listing snapshots for VM '{domain.name()}': {e}") from e


# Convenience functions for backward compatibility with ww.py
def qemu_agent_fsfreeze(domain: libvirt.virDomain) -> bool:
    """Backward compatibility function for agent filesystem freeze."""
    manager = SnapshotManager()
    return manager.qemu_agent_fsfreeze(domain)

def qemu_agent_fsthaw(domain: libvirt.virDomain) -> bool:
    """Backward compatibility function for agent filesystem thaw."""
    manager = SnapshotManager()
    return manager.qemu_agent_fsthaw(domain)

def create_external_snapshot(domain: libvirt.virDomain, snapshot_name: str) -> bool:
    """Backward compatibility function for external snapshot creation."""
    manager = SnapshotManager()
    return manager.create_external_snapshot(domain, snapshot_name)

def revert_to_snapshot(domain: libvirt.virDomain, snapshot_name: str) -> bool:
    """Backward compatibility function for snapshot revert."""
    manager = SnapshotManager()
    return manager.revert_to_snapshot(domain, snapshot_name)

def delete_snapshot(domain: libvirt.virDomain, snapshot_name: str, delete_children: bool = False) -> bool:
    """Backward compatibility function for snapshot deletion."""
    manager = SnapshotManager()
    return manager.delete_snapshot(domain, snapshot_name, delete_children)

def list_snapshots(domain: libvirt.virDomain) -> None:
    """Backward compatibility function for snapshot listing."""
    manager = SnapshotManager()
    return manager.list_snapshots(domain)


# Export all public components
__all__ = [
    'SnapshotManager',
    'qemu_agent_fsfreeze',
    'qemu_agent_fsthaw', 
    'create_external_snapshot',
    'revert_to_snapshot',
    'delete_snapshot',
    'list_snapshots'
]