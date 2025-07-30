#!/usr/bin/env python3
"""
Snapshot Management Utility

Comprehensive snapshot lifecycle management for libvirt VMs including creation,
deletion, restoration, and listing operations with support for external snapshots
and QEMU guest agent integration for filesystem consistency.
"""

import sys
import time
import logging
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("Snapshot Manager requires Python 3.8+. Please upgrade.")
    sys.exit(1)

try:
    import libvirt  # type: ignore
except ImportError:
    print("Error: Missing required library 'libvirt-python'.\n"
          "Please install it and try again.", file=sys.stderr)
    sys.exit(1)

# Rich library for enhanced output
try:
    from rich.console import Console as RichConsole
    from rich.table import Table as RichTable
    rich_available = True
except ImportError:
    rich_available = False
    class RichConsole:
        def print(self, *args: Any, **kwargs: Any) -> None: 
            print(*args)
        def rule(self, *args: Any, **kwargs: Any) -> None: 
            print("="*50)
    
    class RichTable:
        def __init__(self, *args: Any, **kwargs: Any) -> None: 
            pass
        def add_column(self, *args: Any, **kwargs: Any) -> None: 
            pass
        def add_row(self, *args: Any, **kwargs: Any) -> None: 
            pass

# Initialize console
console = RichConsole()

from .exceptions import SnapshotOperationError

# Get libvirt error codes safely
VIR_ERR_NO_DOMAIN_SNAPSHOT = getattr(libvirt, 'VIR_ERR_NO_DOMAIN_SNAPSHOT', -1)
VIR_ERR_OPERATION_INVALID = getattr(libvirt, 'VIR_ERR_OPERATION_INVALID', -1)

class SnapshotManager:
    """
    Comprehensive snapshot management for libvirt VMs.
    
    Supports external snapshots with QEMU guest agent integration
    for filesystem consistency and robust error handling.
    """
    
    def __init__(self, debug: bool = False):
        """Initialize snapshot manager."""
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def create_external_snapshot(self, domain: libvirt.virDomain, snapshot_name: str, 
                                description: str = "", freeze_fs: bool = True) -> bool:
        """
        Create an external snapshot with optional filesystem freeze.
        
        Args:
            domain: Libvirt domain object
            snapshot_name: Name for the snapshot
            description: Optional description
            freeze_fs: Whether to attempt filesystem freeze/thaw
            
        Returns:
            True if successful
            
        Raises:
            SnapshotOperationError: If snapshot creation fails
        """
        if not domain:
            raise SnapshotOperationError("Invalid domain object")
        
        if rich_available:
            console.rule(f"[bold]Creating EXTERNAL Snapshot: [cyan]{snapshot_name}[/][/]", style="blue")
        
        was_frozen = False
        snapshot_files = []
        
        try:
            # Attempt filesystem freeze if requested and VM is running
            if freeze_fs and domain.isActive():
                try:
                    was_frozen = self._qemu_agent_fsfreeze(domain)
                    if was_frozen:
                        self.logger.info("Filesystem frozen successfully")
                except Exception as e:
                    self.logger.warning(f"Filesystem freeze failed: {e}")
            
            # Generate snapshot XML and get file paths
            snapshot_xml, snapshot_files = self._generate_snapshot_xml(domain, snapshot_name, description)
            
            if rich_available:
                console.print(f":camera: Creating external snapshot '{snapshot_name}'...")
            
            # Create the snapshot
            domain.snapshotCreateXML(snapshot_xml, 
                                   libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY |
                                   libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_ATOMIC)
            
            # Verify snapshot files were created
            missing_files: List[str] = []
            for file_path in snapshot_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                raise SnapshotOperationError(f"Snapshot files not created: {missing_files}")
            
            if rich_available:
                console.print(f":white_check_mark: External snapshot '{snapshot_name}' created successfully", 
                            style="green")
                console.print(f"Snapshot files: {', '.join(snapshot_files)}")
            
            self.logger.info(f"External snapshot '{snapshot_name}' created successfully")
            return True
            
        except libvirt.libvirtError as e:
            error_msg = f"Failed to create snapshot '{snapshot_name}': {e}"
            self.logger.error(error_msg)
            if rich_available:
                console.print(f":x: {error_msg}", style="red")
            raise SnapshotOperationError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error creating snapshot '{snapshot_name}': {e}"
            self.logger.error(error_msg)
            if rich_available:
                console.print(f":x: {error_msg}", style="red")
            raise SnapshotOperationError(error_msg)
            
        finally:
            # Always attempt to thaw if we froze
            if was_frozen:
                try:
                    self._qemu_agent_fsthaw(domain)
                    self.logger.info("Filesystem thawed successfully")
                except Exception as e:
                    self.logger.warning(f"Filesystem thaw failed: {e}")

    def revert_to_snapshot(self, domain: libvirt.virDomain, snapshot_name: str) -> bool:
        """
        Revert VM to a previously created snapshot.
        
        Args:
            domain: Libvirt domain object
            snapshot_name: Name of snapshot to revert to
            
        Returns:
            True if successful
            
        Raises:
            SnapshotOperationError: If revert operation fails
        """
        if not domain:
            raise SnapshotOperationError("Invalid domain object")
        
        if rich_available:
            console.rule(f"[bold]Reverting to Snapshot: [cyan]{snapshot_name}[/][/]", style="blue")
        
        snapshot = None
        try:
            # Find the snapshot
            snapshot = domain.snapshotLookupByName(snapshot_name)
            
            if rich_available:
                console.print(f":rewind: Reverting to snapshot '{snapshot_name}'...")
            
            # Revert to snapshot
            domain.revertToSnapshot(snapshot, 0)
            
            if rich_available:
                console.print(f":white_check_mark: Successfully reverted to snapshot '{snapshot_name}'", 
                            style="green")
            
            self.logger.info(f"Successfully reverted to snapshot '{snapshot_name}'")
            return True
            
        except libvirt.libvirtError as e:
            if e.get_error_code() == VIR_ERR_NO_DOMAIN_SNAPSHOT:
                error_msg = f"Snapshot '{snapshot_name}' not found"
            else:
                error_msg = f"Failed to revert to snapshot '{snapshot_name}': {e}"
            
            self.logger.error(error_msg)
            if rich_available:
                console.print(f":x: {error_msg}", style="red")
            raise SnapshotOperationError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error reverting to snapshot '{snapshot_name}': {e}"
            self.logger.error(error_msg)
            if rich_available:
                console.print(f":x: {error_msg}", style="red")
            raise SnapshotOperationError(error_msg)
            
        finally:
            if snapshot:
                # Clean up snapshot reference if needed
                pass

    def delete_external_snapshot(self, domain: libvirt.virDomain, snapshot_name: str) -> bool:
        """
        Delete an external snapshot.
        
        Note: External snapshots usually require the VM to be stopped for safe deletion.
        
        Args:
            domain: Libvirt domain object
            snapshot_name: Name of snapshot to delete
            
        Returns:
            True if successful
            
        Raises:
            SnapshotOperationError: If deletion fails
        """
        if not domain:
            raise SnapshotOperationError("Invalid domain object")
        
        if rich_available:
            console.rule(f"[bold]Deleting Snapshot: [cyan]{snapshot_name}[/][/]", style="red")
        
        snapshot = None
        try:
            # Check if VM is running
            if domain.isActive():
                if rich_available:
                    console.print(":warning: Warning: VM is running. External snapshot deletion may require VM shutdown.", 
                                style="yellow")
            
            # Find the snapshot
            snapshot = domain.snapshotLookupByName(snapshot_name)
            
            if rich_available:
                console.print(f":wastebasket: Deleting snapshot '{snapshot_name}'...")
            
            # Delete the snapshot
            snapshot.delete(libvirt.VIR_DOMAIN_SNAPSHOT_DELETE_METADATA_ONLY)
            
            if rich_available:
                console.print(f":white_check_mark: Snapshot '{snapshot_name}' deleted successfully", 
                            style="green")
                console.print(":information: Note: Snapshot disk files may need manual cleanup.", 
                            style="blue")
            
            self.logger.info(f"Snapshot '{snapshot_name}' deleted successfully")
            return True
            
        except libvirt.libvirtError as e:
            if e.get_error_code() == VIR_ERR_NO_DOMAIN_SNAPSHOT:
                error_msg = f"Snapshot '{snapshot_name}' not found"
            else:
                error_msg = f"Failed to delete snapshot '{snapshot_name}': {e}"
            
            self.logger.error(error_msg)
            if rich_available:
                console.print(f":x: {error_msg}", style="red")
            raise SnapshotOperationError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error deleting snapshot '{snapshot_name}': {e}"
            self.logger.error(error_msg)
            if rich_available:
                console.print(f":x: {error_msg}", style="red")
            raise SnapshotOperationError(error_msg)
            
        finally:
            if snapshot:
                # Clean up snapshot reference if needed
                pass

    def list_snapshots(self, domain: libvirt.virDomain) -> List[Dict[str, Any]]:
        """
        List all snapshots for a domain.
        
        Args:
            domain: Libvirt domain object
            
        Returns:
            List of snapshot information dictionaries
            
        Raises:
            SnapshotOperationError: If listing fails
        """
        if not domain:
            raise SnapshotOperationError("Invalid domain object")
        
        snapshots: List[Dict[str, Any]] = []
        
        try:
            snapshot_list = domain.listAllSnapshots()
            
            for snapshot in snapshot_list:
                try:
                    # Get snapshot metadata
                    snapshot_info: Dict[str, Any] = {
                        'name': snapshot.getName(),
                        'description': '',
                        'creation_time': 'Unknown',
                        'vm_state': 'Unknown',
                        'type': 'Unknown'
                    }
                    
                    # Parse XML for additional info
                    try:
                        xml_desc = snapshot.getXMLDesc()
                        root = ET.fromstring(xml_desc)
                        
                        # Get description
                        desc_elem = root.find('description')
                        if desc_elem is not None:
                            snapshot_info['description'] = desc_elem.text or ''
                        
                        # Get creation time
                        creation_elem = root.find('creationTime')
                        if creation_elem is not None and creation_elem.text:
                            timestamp = int(creation_elem.text)
                            snapshot_info['creation_time'] = time.strftime('%Y-%m-%d %H:%M:%S', 
                                                                         time.localtime(timestamp))
                        
                        # Get VM state at snapshot time
                        state_elem = root.find('state')
                        if state_elem is not None:
                            snapshot_info['vm_state'] = state_elem.text
                        
                        # Determine snapshot type
                        memory_elem = root.find('memory')
                        disks_elem = root.find('disks')
                        
                        if memory_elem is not None and memory_elem.get('snapshot') == 'external':
                            snapshot_info['type'] = 'External (Memory + Disk)'
                        elif disks_elem is not None:
                            disk_types = [disk.get('snapshot') for disk in disks_elem.findall('disk')]
                            if 'external' in disk_types:
                                snapshot_info['type'] = 'External (Disk Only)'
                            else:
                                snapshot_info['type'] = 'Internal'
                        else:
                            snapshot_info['type'] = 'Internal'
                    
                    except ET.ParseError:
                        self.logger.warning(f"Could not parse XML for snapshot {snapshot.getName()}")
                    
                    snapshots.append(snapshot_info)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing snapshot {snapshot.getName()}: {e}")
                    # Add minimal info for problematic snapshots
                    snapshots.append({
                        'name': snapshot.getName(),
                        'description': f'Error: {e}',
                        'creation_time': 'Unknown',
                        'vm_state': 'Unknown',
                        'type': 'Unknown'
                    })
            
            # Display results if Rich is available
            if rich_available and snapshots:
                table = RichTable(title=f"[bold blue]Snapshots for VM '[cyan]{domain.name()}[/]'[/]", 
                            show_header=True, header_style="bold magenta")
                table.add_column("Snapshot Name", style="cyan")
                table.add_column("Created", style="dim", justify="center")
                table.add_column("VM State", justify="center")
                table.add_column("Type", justify="center")
                table.add_column("Description", justify="left")
                
                for snap in snapshots:
                    table.add_row(
                        snap['name'],
                        snap['creation_time'],
                        snap['vm_state'],
                        snap['type'],
                        snap['description'][:50] + '...' if len(snap['description']) > 50 else snap['description']
                    )
                
                console.print(table)
            elif rich_available:
                console.print(f"[yellow]No snapshots found for VM '{domain.name()}'[/]")
            
            return snapshots
            
        except libvirt.libvirtError as e:
            error_msg = f"Failed to list snapshots for VM '{domain.name()}': {e}"
            self.logger.error(error_msg)
            if rich_available:
                console.print(f":x: {error_msg}", style="red")
            raise SnapshotOperationError(error_msg)

    def _generate_snapshot_xml(self, domain: libvirt.virDomain, snapshot_name: str, 
                              description: str = "") -> Tuple[str, List[str]]:
        """Generate snapshot XML and return XML string and list of snapshot file paths."""
        snapshot_disk_files: List[str] = []
        
        try:
            # Get domain XML to extract disk information
            domain_xml = domain.XMLDesc(0)
            domain_root = ET.fromstring(domain_xml)
            
            # Create snapshot XML structure
            snapshot_root = ET.Element("domainsnapshot")
            
            # Add basic snapshot metadata
            name_elem = ET.SubElement(snapshot_root, "name")
            name_elem.text = snapshot_name
            
            if description:
                desc_elem = ET.SubElement(snapshot_root, "description")
                desc_elem.text = description
            
            # Add disk configuration for external snapshot
            disks_elem = ET.SubElement(snapshot_root, "disks")
            
            # Process each disk in the domain
            for disk in domain_root.findall(".//disk[@device='disk']"):
                source = disk.find("source")
                target = disk.find("target")
                
                if source is not None and target is not None:
                    # Get source file path
                    source_file = source.get("file")
                    target_dev = target.get("dev")
                    
                    if source_file and target_dev:
                        # Generate external snapshot filename
                        source_path = Path(source_file)
                        snapshot_file = source_path.parent / f"{source_path.stem}.{snapshot_name}{source_path.suffix}"
                        snapshot_disk_files.append(str(snapshot_file))
                        
                        # Add disk element to snapshot XML
                        disk_elem = ET.SubElement(disks_elem, "disk", name=target_dev, snapshot="external")
                        ET.SubElement(disk_elem, "driver", type="qcow2")
                        ET.SubElement(disk_elem, "source", file=str(snapshot_file))
            
            # Convert to XML string
            snapshot_xml = ET.tostring(snapshot_root, encoding='unicode')
            
            return snapshot_xml, snapshot_disk_files
            
        except ET.ParseError as e:
            raise SnapshotOperationError(f"Failed to parse domain XML: {e}")
        except Exception as e:
            raise SnapshotOperationError(f"Failed to generate snapshot XML: {e}")

    def _qemu_agent_fsfreeze(self, domain: libvirt.virDomain) -> bool:
        """Attempt to freeze VM filesystems using QEMU guest agent."""
        try:
            if rich_available:
                console.print(":snowflake: Attempting filesystem freeze via QEMU agent...")
            
            response = domain.qemuAgentCommand('{"execute": "guest-fsfreeze-freeze"}', 10, 0)
            
            if response:
                response_data = json.loads(response)
                if isinstance(response_data, dict) and ('return' in response_data or response_data == {}):
                    if rich_available:
                        console.print(":white_check_mark: Filesystem freeze successful", style="green")
                    return True
            
            return False
            
        except Exception as e:
            if rich_available:
                console.print(f":warning: Filesystem freeze failed: {e}", style="yellow")
            return False

    def _qemu_agent_fsthaw(self, domain: libvirt.virDomain) -> bool:
        """Attempt to thaw VM filesystems using QEMU guest agent."""
        try:
            if rich_available:
                console.print(":fire: Attempting filesystem thaw via QEMU agent...")
            
            response = domain.qemuAgentCommand('{"execute": "guest-fsfreeze-thaw"}', 10, 0)
            
            if response:
                response_data = json.loads(response)
                if isinstance(response_data, dict) and ('return' in response_data or response_data == {}):
                    if rich_available:
                        console.print(":white_check_mark: Filesystem thaw successful", style="green")
                    return True
            
            return False
            
        except Exception as e:
            if rich_available:
                console.print(f":warning: Filesystem thaw failed: {e}", style="yellow")
            return False
