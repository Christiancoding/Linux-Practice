#!/usr/bin/env python3
"""
Snapshot Management Module

Comprehensive VM snapshot operations including external snapshot creation,
reversion, and QEMU guest agent filesystem operations for consistent snapshots.
"""

import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple
import logging
import json
from .config import LibvirtErrorCodes
import stat
import os
import subprocess
# Third-party imports
try:
    import libvirt # type: ignore
except ImportError:
    raise ImportError("libvirt-python is required. Install with: pip install libvirt-python")

# Local imports
from .console_helper import console, RICH_AVAILABLE

from rich.console import Console  # Add this import for type hinting

console: 'Console'  # Type annotation for static analysis
from .exceptions import (
    PracticeToolError, 
    SnapshotOperationError
)
from .config import config

# Set up module logger
logger = logging.getLogger(__name__)

if RICH_AVAILABLE:
    from rich.panel import Panel
    from rich.table import Table
else:
    Panel = None  # Prevent unbound errors if RICH_AVAILABLE is False


class SnapshotManager:
    """
    Advanced VM snapshot management with external snapshot support
    and QEMU guest agent integration for filesystem consistency.
    """
    
    def __init__(self):
        """Initialize the snapshot manager."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    def _check_and_fix_vm_permissions(self, domain: libvirt.virDomain, auto_fix: bool = True) -> bool:
        """
        Check and optionally fix VM disk file permissions before snapshot operations.
        
        Args:
            domain: Libvirt domain object
            auto_fix: Whether to automatically attempt permission fixes
            
        Returns:
            bool: True if permissions are correct or successfully fixed
        """
        vm_name = domain.name()
        
        try:
            # Get VM XML to find disk files
            raw_xml = domain.XMLDesc(0)
            tree = ET.fromstring(raw_xml)
            
            permission_issues = []
            
            # Check each disk device
            for device in tree.findall('devices/disk'):
                if device.get('type') == 'file' and device.get('device') == 'disk':
                    source_node = device.find('source')
                    if source_node is not None and 'file' in source_node.attrib:
                        disk_path = Path(source_node.get('file'))
                        
                        if disk_path.exists():
                            # Check file ownership and permissions
                            stat_info = disk_path.stat()
                            
                            # Get file owner and group
                            import pwd
                            import grp
                            try:
                                owner = pwd.getpwuid(stat_info.st_uid).pw_name
                                group = grp.getgrgid(stat_info.st_gid).gr_name
                            except KeyError:
                                owner = str(stat_info.st_uid)
                                group = str(stat_info.st_gid)
                            
                            # Check if permissions are correct
                            expected_perms = 0o660  # rw-rw----
                            current_perms = stat.S_IMODE(stat_info.st_mode)
                            
                            # Check if libvirt can access the file
                            libvirt_access_ok = (
                                (owner == 'libvirt-qemu' or group == 'libvirt') and
                                (current_perms & 0o660) == 0o660
                            )
                            
                            if not libvirt_access_ok:
                                issue = {
                                    'path': disk_path,
                                    'current_owner': owner,
                                    'current_group': group,
                                    'current_perms': oct(current_perms),
                                    'expected_owner': 'libvirt-qemu',
                                    'expected_group': 'libvirt',
                                    'expected_perms': oct(expected_perms)
                                }
                                permission_issues.append(issue)
                                
                            # Also check for snapshot files in the same directory
                            disk_dir = disk_path.parent
                            vm_base = disk_path.stem.split('-')[0]
                            snapshot_files = list(disk_dir.glob(f"{vm_base}*snap*.qcow2"))
                            
                            for snap_file in snapshot_files:
                                snap_stat = snap_file.stat()
                                try:
                                    snap_owner = pwd.getpwuid(snap_stat.st_uid).pw_name
                                    snap_group = grp.getgrgid(snap_stat.st_gid).gr_name
                                except KeyError:
                                    snap_owner = str(snap_stat.st_uid)
                                    snap_group = str(snap_stat.st_gid)
                                
                                snap_perms = stat.S_IMODE(snap_stat.st_mode)
                                snap_access_ok = (
                                    (snap_owner == 'libvirt-qemu' or snap_group == 'libvirt') and
                                    (snap_perms & 0o660) == 0o660
                                )
                                
                                if not snap_access_ok:
                                    snap_issue = {
                                        'path': snap_file,
                                        'current_owner': snap_owner,
                                        'current_group': snap_group,
                                        'current_perms': oct(snap_perms),
                                        'expected_owner': 'libvirt-qemu',
                                        'expected_group': 'libvirt',
                                        'expected_perms': oct(expected_perms)
                                    }
                                    permission_issues.append(snap_issue)
            
            if not permission_issues:
                self.logger.debug(f"VM '{vm_name}' disk and snapshot permissions are correct")
                return True
            
            # Report permission issues
            console.print(f"[yellow]:warning: Permission issues detected for VM '{vm_name}' disk/snapshot files:[/]")
            for issue in permission_issues:
                console.print(f"  File: {issue['path']}")
                console.print(f"    Current: {issue['current_owner']}:{issue['current_group']} {issue['current_perms']}")
                console.print(f"    Expected: {issue['expected_owner']}:{issue['expected_group']} {issue['expected_perms']}")
            
            if not auto_fix:
                console.print("[yellow]Use --auto-fix-permissions to automatically correct these issues.[/]")
                return False
            
            # Attempt to fix permissions
            console.print("[yellow]Attempting to fix VM disk and snapshot file permissions...[/]")
            
            # Check if user is in libvirt group
            try:
                result = subprocess.run(['groups'], capture_output=True, text=True, check=True)
                user_groups = result.stdout.strip().split()
                if 'libvirt' not in user_groups:
                    console.print("[yellow]Adding current user to libvirt group...[/]")
                    subprocess.run(['sudo', 'usermod', '-a', '-G', 'libvirt', os.getenv('USER', 'user')], check=True)
                    console.print("[green]User added to libvirt group. You may need to log out and back in.[/]")
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Could not check/fix user groups: {e}")
            
            # Fix file ownership and permissions
            success_count = 0
            for issue in permission_issues:
                try:
                    file_path = issue['path']
                    
                    # Fix ownership
                    chown_cmd = ['sudo', 'chown', 'libvirt-qemu:libvirt', str(file_path)]
                    subprocess.run(chown_cmd, check=True, capture_output=True)
                    
                    # Fix permissions
                    chmod_cmd = ['sudo', 'chmod', '660', str(file_path)]
                    subprocess.run(chmod_cmd, check=True, capture_output=True)
                    
                    console.print(f"[green]Fixed permissions for: {file_path}[/]")
                    success_count += 1
                    
                except subprocess.CalledProcessError as e:
                    console.print(f"[red]Failed to fix permissions for {file_path}: {e}[/]")
                    self.logger.error(f"Permission fix failed for {file_path}: {e}")
            
            if success_count == len(permission_issues):
                console.print(f"[green]Successfully fixed all {success_count} permission issues.[/]")
                
                # Restart libvirtd to ensure changes take effect
                try:
                    console.print("[yellow]Restarting libvirtd service...[/]")
                    subprocess.run(['sudo', 'systemctl', 'restart', 'libvirtd'], check=True, capture_output=True)
                    console.print("[green]Libvirtd service restarted successfully.[/]")
                    # Give libvirtd time to restart
                    import time
                    time.sleep(3)
                except subprocess.CalledProcessError as e:
                    console.print(f"[yellow]Warning: Could not restart libvirtd: {e}[/]")
                
                return True
            else:
                console.print(f"[yellow]Fixed {success_count}/{len(permission_issues)} permission issues.[/]")
                return False
                
        except ET.ParseError as e:
            self.logger.error(f"Error parsing VM XML for '{vm_name}': {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error checking VM permissions for '{vm_name}': {e}")
            return False
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
            
            # Safely get qemuAgentCommand method
            qemu_agent_cmd = getattr(domain, "qemuAgentCommand", None)
            if not callable(qemu_agent_cmd):
                console.print("  [yellow]:warning: QEMU Agent: qemuAgentCommand not available on this libvirt version.[/]", style="yellow")
                return False
                
            # Execute guest agent filesystem freeze command
            response = qemu_agent_cmd(
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
                    
        except AttributeError as attr_err:
            console.print("  [yellow]:warning: QEMU Agent: qemuAgentCommand method not available on domain object.[/]", style="yellow")
            self.logger.warning(f"QEMU agent method not available: {attr_err}")
            return False
        except libvirt.libvirtError as e:
            error_code = e.get_error_code()
            if error_code == LibvirtErrorCodes.VIR_ERR_AGENT_UNRESPONSIVE and LibvirtErrorCodes.VIR_ERR_AGENT_UNRESPONSIVE != -1:
                console.print("  [yellow]:warning: QEMU Agent: Agent unresponsive, cannot freeze filesystems.[/]", style="yellow")
            else:
                console.print(f"  [yellow]:warning: QEMU Agent: Filesystem freeze failed: {e}[/]", style="yellow")
            self.logger.warning(f"QEMU agent fsfreeze failed: {e}")
            return False
        except Exception as e:
            console.print(f"  [yellow]:warning: QEMU Agent: Unexpected error during filesystem freeze: {e}[/]", style="yellow")
            self.logger.error(f"Unexpected error in qemu_agent_fsfreeze: {e}", exc_info=True)
            return False
    def cleanup_old_snapshots(self, domain: libvirt.virDomain, keep_count: int = 5) -> None:
        """
        Public method to clean up old snapshot files.
        
        Args:
            domain: The libvirt domain object
            keep_count: Number of recent snapshots to keep
        """
        return self._cleanup_old_snapshots(domain, keep_count)
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
            
            # Safely get qemuAgentCommand method
            qemu_agent_cmd = getattr(domain, "qemuAgentCommand", None)
            if not callable(qemu_agent_cmd):
                console.print("  [yellow]:warning: QEMU Agent: qemuAgentCommand not available on this libvirt version.[/]", style="yellow")
                return False
            
            # Execute guest agent filesystem thaw command
            response = qemu_agent_cmd(
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
                thawed_count: int = response.get('return', 0)
                if thawed_count >= 0:
                    console.print(f"  [green]:heavy_check_mark: QEMU Agent: Filesystems thawed successfully (Count: {thawed_count}).[/]")
                    return True
                else:
                    console.print(f"  [yellow]:warning: QEMU Agent: Filesystem thaw returned unexpected dict response: {response}[/]", style="yellow")
                    return False
            else:
                console.print(f"  [yellow]:warning: QEMU Agent: Filesystem thaw returned unexpected response type: {type(response)} {response}[/]", style="yellow")
                return False
                    
        except AttributeError as attr_err:
            console.print("  [yellow]:warning: QEMU Agent: qemuAgentCommand method not available on domain object.[/]", style="yellow")
            self.logger.warning(f"QEMU agent method not available: {attr_err}")
            return False
        except libvirt.libvirtError as e:
            error_code = e.get_error_code()
            if error_code == LibvirtErrorCodes.VIR_ERR_AGENT_UNRESPONSIVE and LibvirtErrorCodes.VIR_ERR_AGENT_UNRESPONSIVE != -1:
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
        snapshot_disk_files: List[str] = []
        try:
            raw_xml: str = domain.XMLDesc(0)
            tree = ET.fromstring(raw_xml)
            disks_xml = ""
            disk_count = 0
            
            # Create table for disk planning display
            disk_table = None
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
                    if original_disk_path_str is None:
                        console.print(f"[yellow]Warning:[/yellow] Disk '{target_dev}' source file attribute is missing, skipping snapshot for this disk.", style="yellow")
                        continue
                    
                    # Initialize the path variable for this iteration
                    original_disk_path = Path(original_disk_path_str).resolve()
                    original_disk_dir = original_disk_path.parent
                    
                    # Validate that the source file exists
                    if not original_disk_path.exists():
                        raise SnapshotOperationError(
                            f"Base disk file does not exist: {original_disk_path}. "
                            f"VM configuration may be corrupted. Please check the VM disk configuration."
                        )
                    
                    if not original_disk_dir.is_dir():
                        raise SnapshotOperationError(f"Directory '{original_disk_dir}' for base disk '{original_disk_path.name}' (target: {target_dev}) does not exist.")
                    
                    # Generate clean snapshot file path
                    base_name = original_disk_path.stem
                    # Clean the base name by removing previous snapshot suffixes
                    if '-practice' in base_name or '-snap' in base_name:
                        # Find the first occurrence of a snapshot pattern and truncate there
                        base_parts = base_name.split('-')
                        clean_parts: List[str] = []
                        for part in base_parts:
                            if any(x in part.lower() for x in ['practice', 'snapshot', 'external', 'snap']):
                                break
                            clean_parts.append(part)
                        base_name = '-'.join(clean_parts) if clean_parts else base_parts[0]

                    # Create a short, unique snapshot filename
                    import hashlib
                    unique_id = hashlib.md5(f"{snapshot_name}-{time.time()}".encode()).hexdigest()[:8]
                    snapshot_disk_name = f"{base_name}-snap-{unique_id}.qcow2"
                    snapshot_disk_path = original_disk_dir / snapshot_disk_name
                    snapshot_disk_files.append(str(snapshot_disk_path))
                    
                    # Add disk XML for this device
                    disks_xml += f'    <disk name="{target_dev}" snapshot="external">\n'
                    disks_xml += f'      <source file="{snapshot_disk_path}"/>\n'
                    disks_xml += f'      <driver type="{driver_type}"/>\n'
                    disks_xml += f'    </disk>\n'
                    
                    disk_count += 1
                    
                    # Add to table display
                    if disk_table is not None:
                        disk_table.add_row(
                            target_dev,
                            original_disk_path.name,
                            snapshot_disk_name
                        )
            
            # Display disk planning table
            if disk_table is not None and disk_count > 0:
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
    
    def create_external_snapshot(self, domain: libvirt.virDomain, snapshot_name: str, auto_fix_permissions: bool = True) -> bool:
        """
        Create an external snapshot with agent-based filesystem freeze/thaw and automatic permission checking.
        
        Args:
            domain: The libvirt domain object
            snapshot_name: Name for the snapshot
            auto_fix_permissions: Whether to automatically fix permission issues
            
        Returns:
            bool: True if snapshot creation was successful
            
        Raises:
            SnapshotOperationError: If snapshot creation fails
        """
        self._cleanup_old_snapshots(domain)
        if not domain:
            raise PracticeToolError("Invalid VM domain provided to create_external_snapshot.")
        
        console.rule(f"[bold]Creating EXTERNAL Snapshot: [cyan]{snapshot_name}[/][/]", style="blue")
        
        # Check and fix permissions before snapshot creation
        if auto_fix_permissions:
            console.print(f"[yellow]Checking VM disk permissions before snapshot creation...[/]")
            permission_ok = self._check_and_fix_vm_permissions(domain, auto_fix=True)
            if not permission_ok:
                console.print(f"[yellow]Warning: Could not fix all permission issues, attempting snapshot creation anyway...[/]")
        
        was_frozen_by_agent = False
        
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
            snapshot_xml, _ = self._generate_snapshot_xml(domain, snapshot_name, was_frozen_by_agent)
            
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
            
            try:
                snapshot = domain.snapshotCreateXML(str(snapshot_xml), flags)
                
                if snapshot:
                    console.print(f"[green]:camera_with_flash: Successfully created external snapshot metadata: '{snapshot.getName()}'[/]")
                    return True
                else:
                    raise SnapshotOperationError(f"Libvirt snapshotCreateXML returned None unexpectedly for '{snapshot_name}'.")
            
            except libvirt.libvirtError as create_error:
                # If snapshot creation fails due to permissions, try to fix and retry
                if "Permission denied" in str(create_error) and auto_fix_permissions:
                    console.print(f"[yellow]Snapshot creation failed due to permissions, attempting fix and retry...[/]")
                    
                    if self._check_and_fix_vm_permissions(domain, auto_fix=True):
                        console.print(f"[yellow]Retrying snapshot creation after permission fix...[/]")
                        snapshot = domain.snapshotCreateXML(str(snapshot_xml), flags)
                        
                        if snapshot:
                            console.print(f"[green]:camera_with_flash: Successfully created external snapshot metadata after permission fix: '{snapshot.getName()}'[/]")
                            return True
                        else:
                            raise SnapshotOperationError(f"Libvirt snapshotCreateXML returned None after permission fix for '{snapshot_name}'.")
                    else:
                        raise SnapshotOperationError(f"Could not fix permissions for snapshot creation: {create_error}") from create_error
                else:
                    raise create_error
            
        except libvirt.libvirtError as e:
            err_code = e.get_error_code()
            if err_code == LibvirtErrorCodes.VIR_ERR_CONFIG_EXIST and LibvirtErrorCodes.VIR_ERR_CONFIG_EXIST != -1:
                raise SnapshotOperationError(f"Snapshot metadata '{snapshot_name}' already exists. Delete it first.") from e
            elif err_code == LibvirtErrorCodes.VIR_ERR_AGENT_UNRESPONSIVE and LibvirtErrorCodes.VIR_ERR_AGENT_UNRESPONSIVE != -1 and quiesce_flag_used:
                msg = f"Snapshot creation failed: Libvirt QUIESCE flag requires guest agent interaction, but agent was unresponsive ({e})"
                console.print(f"[bold red]Error:[/bold red] {msg}", style="red")
                raise SnapshotOperationError(msg) from e
            elif err_code == LibvirtErrorCodes.VIR_ERR_OPERATION_INVALID and LibvirtErrorCodes.VIR_ERR_OPERATION_INVALID != -1:
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
            snapshot: libvirt.virDomainSnapshot = domain.snapshotLookupByName(snapshot_name, 0)
            console.print(f"  :mag_right: Found snapshot '{snapshot_name}', attempting revert...")
            
            # 2. Perform the revert
            # Use FORCE flag to revert even if VM state conflicts
            flags = libvirt.VIR_DOMAIN_SNAPSHOT_REVERT_FORCE
            domain.revertToSnapshot(snapshot, flags)
            
            console.print(f"[green]:heavy_check_mark: Successfully reverted to snapshot '{snapshot_name}'[/]")
            return True
            
        except libvirt.libvirtError as e:
            err_code = e.get_error_code()
            if err_code == LibvirtErrorCodes.VIR_ERR_NO_DOMAIN_SNAPSHOT and LibvirtErrorCodes.VIR_ERR_NO_DOMAIN_SNAPSHOT != -1:
                raise SnapshotOperationError(f"Snapshot '{snapshot_name}' not found.") from e
            else:
                raise SnapshotOperationError(f"Error reverting to snapshot '{snapshot_name}': {e}") from e
        except Exception as e:
            raise SnapshotOperationError(f"Unexpected error reverting to snapshot '{snapshot_name}': {e}") from e
        finally:
            console.rule(f"[bold]End Snapshot Revert[/]", style="blue")
    
    def delete_snapshot(self, domain: libvirt.virDomain, snapshot_name: str, delete_children: bool = False, auto_fix_permissions: bool = True) -> bool:
        """
        Delete a snapshot and optionally its children, with automatic permission checking and fixing.
        
        Args:
            domain: The libvirt domain object
            snapshot_name: Name of the snapshot to delete
            delete_children: Whether to delete child snapshots
            auto_fix_permissions: Whether to automatically fix permission issues
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            SnapshotOperationError: If snapshot deletion fails
        """
        if not domain:
            raise PracticeToolError("Invalid VM domain provided to delete_snapshot.")
        
        vm_name = domain.name()
        console.rule(f"[bold]Deleting Snapshot: [cyan]{snapshot_name}[/][/]", style="blue")
        
        # Check if VM is running and might need to be shut down
        if domain.isActive():
            console.print(f"[yellow]:warning: VM is running. Shutting down before deleting snapshot...[/]")
            try:
                # Gracefully shutdown VM first
                from .vm_manager import VMManager
                vm_manager = VMManager()
                vm_manager._shutdown_vm_gracefully(domain, timeout_seconds=120)
            except Exception as shutdown_error:
                console.print(f"[yellow]Warning: Could not gracefully shutdown VM: {shutdown_error}[/]")
                console.print(f"[yellow]Forcing VM shutdown...[/]")
                try:
                    domain.destroy()
                    console.print(f"[green]VM '{vm_name}' forced shutdown.[/]")
                except libvirt.libvirtError as force_error:
                    console.print(f"[red]Failed to force shutdown VM: {force_error}[/]")
        
        try:
            # Check and fix permissions before attempting deletion
            if auto_fix_permissions:
                console.print(f"[yellow]Checking VM disk permissions before snapshot deletion...[/]")
                permission_ok = self._check_and_fix_vm_permissions(domain, auto_fix=True)
                if not permission_ok:
                    console.print(f"[yellow]Warning: Could not fix all permission issues, attempting deletion anyway...[/]")
            
            # 1. Look up the snapshot
            console.print(f":wastebasket: Attempting to delete snapshot '[cyan]{snapshot_name}[/cyan]' (Flags=0). This might involve merging data...")
            snapshot = domain.snapshotLookupByName(snapshot_name, 0)
            
            # 2. Set deletion flags
            # Use metadata-only deletion to avoid disk file access issues
            flags = libvirt.VIR_DOMAIN_SNAPSHOT_DELETE_METADATA_ONLY
            if delete_children:
                flags |= libvirt.VIR_DOMAIN_SNAPSHOT_DELETE_CHILDREN
            
            # 3. Attempt the deletion
            try:
                snapshot.delete(flags)
                console.print(f"[green]:heavy_check_mark: Successfully deleted snapshot '[cyan]{snapshot_name}[/cyan]'[/]")
                return True
                
            except libvirt.libvirtError as delete_error:
                # If metadata-only deletion fails, try without any flags as fallback
                if "Permission denied" in str(delete_error) and auto_fix_permissions:
                    console.print(f"[yellow]Metadata deletion failed, retrying after additional permission fixes...[/]")
                    
                    # Try to fix permissions again and retry
                    if self._check_and_fix_vm_permissions(domain, auto_fix=True):
                        try:
                            # Retry the deletion with minimal flags
                            snapshot.delete(0)  # No flags - let libvirt decide
                            console.print(f"[green]:heavy_check_mark: Successfully deleted snapshot '[cyan]{snapshot_name}[/cyan]' after permission fix[/]")
                            return True
                        except libvirt.libvirtError as retry_error:
                            raise SnapshotOperationError(f"Snapshot deletion failed even after permission fix: {retry_error}") from retry_error
                    else:
                        raise SnapshotOperationError(f"Could not fix permissions for snapshot deletion: {delete_error}") from delete_error
                else:
                    raise delete_error
                
        except libvirt.libvirtError as e:
            err_code = e.get_error_code()
            if err_code == LibvirtErrorCodes.VIR_ERR_NO_DOMAIN_SNAPSHOT and LibvirtErrorCodes.VIR_ERR_NO_DOMAIN_SNAPSHOT != -1:
                raise SnapshotOperationError(f"Snapshot '{snapshot_name}' not found.") from e
            else:
                raise SnapshotOperationError(f"Error deleting snapshot '{snapshot_name}': {e}") from e
        except Exception as e:
            raise SnapshotOperationError(f"Unexpected error deleting snapshot '{snapshot_name}': {e}") from e
        finally:
            console.rule(f"[bold]End Snapshot Deletion[/]", style="blue")
    
    def list_snapshots(self, domain: libvirt.virDomain) -> None:
        """
        List all snapshots for a domain with detailed information.
        
        Args:
            domain: The libvirt domain object
            
        Raises:
            PracticeToolError: If listing snapshots fails
        """
        try:
            snapshot_names: List[str] = domain.listSnapshotNames(0)  # type: ignore
            
            if not snapshot_names:
                if RICH_AVAILABLE and Panel is not None:
                    console.print(Panel("[dim]No snapshots found.[/]", title=f"Snapshots for {domain.name()}", border_style="dim", style="dim"))
                else:
                    console.print(f"No snapshots found for {domain.name()}")
                return
            
            table = None
            if RICH_AVAILABLE and 'Table' in globals():
                table = Table(title=f"Snapshots for {domain.name()}", show_header=True, header_style="bold blue")
                table.add_column("Name", style="cyan")
                table.add_column("Created", style="green")
                table.add_column("State", style="yellow")
                table.add_column("Type", style="magenta")
                table.add_column("Description", style="white")
            
            for name in map(str, list(snapshot_names) if snapshot_names is not None else []):
                details = "[dim]N/A[/]"
                creation_time_str = "[dim]N/A[/]"
                state_str = "[dim]N/A[/]"
                type_str = "[dim]Unknown[/]"
                
                try:
                    snapshot = domain.snapshotLookupByName(str(name), 0)
                    xml_desc: str = snapshot.getXMLDesc(0)
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
                    
                    if creation_time_node is not None and creation_time_node.text is not None and creation_time_node.text.isdigit():
                        try:
                            creation_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(creation_time_node.text)))
                        except ValueError:
                            pass  # Handle potential large timestamps
                    
                    state_str = state_node.text if state_node is not None else '[dim]N/A[/]'
                    type_str = f"{'External' if is_external else 'Internal'}{'+Mem' if has_memory else ''}"
                    details = desc_node.text.strip() if desc_node is not None and desc_node.text else "[dim]No description[/]"
                    
                except libvirt.libvirtError as e_lookup:
                    if e_lookup.get_error_code() == LibvirtErrorCodes.VIR_ERR_NO_DOMAIN_SNAPSHOT and LibvirtErrorCodes.VIR_ERR_NO_DOMAIN_SNAPSHOT != -1:
                        details = "[yellow](Disappeared)[/]"
                    else:
                        details = f"[red](Error looking up: {e_lookup})[/]"
                except ET.ParseError:
                    details = "[red](Error parsing XML)[/]"
                except Exception as detail_err:
                    details = f"[red](Unexpected error: {detail_err})[/]"
                finally:
                    if RICH_AVAILABLE and table is not None:
                        table.add_row(name, creation_time_str, state_str, type_str, details)
                    else:
                        console.print(f"{name}: {creation_time_str} | {state_str} | {type_str} | {details}")
            if RICH_AVAILABLE and table is not None:
                console.print(table)
                
        except libvirt.libvirtError as e:
            raise PracticeToolError(f"Error listing snapshots for VM '{domain.name()}': {e}") from e
    def _cleanup_old_snapshots(self, domain: libvirt.virDomain, keep_count: int = 5) -> None:
        """
        Clean up old snapshot files to prevent disk space issues.
        
        Args:
            domain: The libvirt domain object
            keep_count: Number of recent snapshots to keep
        """
        try:
            # Get VM disk directory
            raw_xml = domain.XMLDesc(0)
            tree = ET.fromstring(raw_xml)
            
            for device in tree.findall('devices/disk'):
                if device.get('type') == 'file' and device.get('device') == 'disk':
                    source_node = device.find('source')
                    if source_node is not None and 'file' in source_node.attrib:
                        file_path = source_node.get('file')
                        if file_path is not None:
                            disk_path = Path(file_path)
                            disk_dir = disk_path.parent
                            
                            # Find all snapshot files for this VM
                            vm_base = disk_path.stem.split('-')[0]  # Get just the VM name part
                            snapshot_files = list(disk_dir.glob(f"{vm_base}-*-snap-*.qcow2"))
                            
                            # Sort by modification time (newest first)
                            snapshot_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                            
                            # Remove old snapshots beyond keep_count
                            for old_file in snapshot_files[keep_count:]:
                                try:
                                    old_file.unlink()
                                    self.logger.info(f"Cleaned up old snapshot file: {old_file.name}")
                                except OSError as e:
                                    self.logger.warning(f"Could not remove old snapshot file {old_file}: {e}")
                                
        except Exception as e:
            self.logger.warning(f"Error during snapshot cleanup: {e}")
        
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