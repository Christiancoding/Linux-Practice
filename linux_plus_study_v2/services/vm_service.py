#!/usr/bin/env python3
"""
VM Service Layer

Business logic for VM management operations with comprehensive
error handling and logging infrastructure.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from vm_integration.utils.vm_manager import VMManager
from vm_integration.utils.ssh_manager import SSHManager


class VMService:
    """Service layer for VM management operations."""
    
    def __init__(self):
        """Initialize VM service with proper logging."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.vm_manager = VMManager()
        self.ssh_manager = SSHManager()
    
    def list_vms(self) -> Dict[str, Any]:
        """
        List all available VMs with their current status.
        
        Returns:
            Dict containing success status and VM list
        """
        try:
            conn = self.vm_manager.connect_libvirt()
            vms = []
            
            # Get all defined VMs
            for vm_name in conn.listDefinedDomains():
                vm_info = self._get_vm_info(conn, vm_name)
                vms.append(vm_info)
            
            # Get all running VMs
            for vm_id in conn.listDomainsID():
                domain = conn.lookupByID(vm_id)
                vm_name = domain.name()
                
                # Skip if already processed
                if not any(vm['name'] == vm_name for vm in vms):
                    vm_info = self._get_vm_info(conn, vm_name)
                    vms.append(vm_info)
            
            conn.close()
            
            return {
                'success': True,
                'vms': sorted(vms, key=lambda x: x['name'])
            }
            
        except Exception as e:
            self.logger.error(f"Error listing VMs: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_vm_info(self, conn, vm_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific VM."""
        try:
            domain = conn.lookupByName(vm_name)
            is_active = domain.isActive()
            
            vm_info = {
                'name': vm_name,
                'status': 'running' if is_active else 'stopped',
                'id': domain.ID() if is_active else None,
                'ip': None
            }
            
            # Get IP address if running
            if is_active:
                try:
                    vm_info['ip'] = self.vm_manager.get_vm_ip(conn, domain)
                except Exception as e:
                    self.logger.debug(f"Could not get IP for VM {vm_name}: {e}")
                    vm_info['ip'] = 'Unknown'
            
            return vm_info
            
        except Exception as e:
            self.logger.error(f"Error getting VM info for {vm_name}: {e}")
            return {
                'name': vm_name,
                'status': 'error',
                'error': str(e)
            }
    def get_challenges(self) -> Dict[str, Any]:
        """
        Get list of available challenge files.
        
        Returns:
            Dict containing success status and challenge list
        """
        try:
            challenges_dir = Path('challenges')
            if not challenges_dir.exists():
                return {'success': True, 'challenges': []}
            
            challenges = []
            for challenge_file in challenges_dir.glob('*.yaml'):
                try:
                    challenge_info = {
                        'name': challenge_file.stem,
                        'filename': challenge_file.name,
                        'path': str(challenge_file),
                        'size': challenge_file.stat().st_size,
                        'modified': challenge_file.stat().st_mtime
                    }
                    challenges.append(challenge_info)
                except Exception as e:
                    self.logger.warning(f"Error processing challenge {challenge_file}: {e}")
            
            return {
                'success': True,
                'challenges': sorted(challenges, key=lambda x: x['name'])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting challenges: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def manage_snapshots(self, vm_name: str, action: str, snapshot_name: str = None, 
                        description: str = None) -> Dict[str, Any]:
        """
        Comprehensive snapshot management operations.
        
        Args:
            vm_name: Target VM name
            action: Operation type (list, create, restore, delete)
            snapshot_name: Name of snapshot for operations
            description: Optional description for new snapshots
            
        Returns:
            Dict containing operation results
        """
        try:
            conn = self.vm_manager.connect_libvirt()
            domain = self.vm_manager.find_vm(conn, vm_name)
            
            if action == 'list':
                return self._list_snapshots(domain)
            elif action == 'create':
                return self._create_snapshot(domain, snapshot_name, description)
            elif action == 'restore':
                return self._restore_snapshot(domain, snapshot_name)
            elif action == 'delete':
                return self._delete_snapshot(domain, snapshot_name)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            self.logger.error(f"Error managing snapshots for {vm_name}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            try:
                conn.close()
            except:
                pass

    def _list_snapshots(self, domain) -> Dict[str, Any]:
        """List all snapshots for a domain."""
        try:
            snapshots = []
            snapshot_objects = domain.listAllSnapshots()
            
            for snapshot in snapshot_objects:
                snapshot_info = {
                    'name': snapshot.getName(),
                    'current': snapshot.isCurrent(),
                    'description': self._extract_description(snapshot.getXMLDesc())
                }
                snapshots.append(snapshot_info)
            
            return {
                'success': True,
                'snapshots': sorted(snapshots, key=lambda x: x['name'])
            }
            
        except Exception as e:
            self.logger.error(f"Error listing snapshots: {e}")
            return {'success': False, 'error': str(e)}

    def _create_snapshot(self, domain, snapshot_name: str, description: str = None) -> Dict[str, Any]:
        """Create a new snapshot."""
        try:
            from vm_integration.utils.snapshot_manager import SnapshotManager
            
            snapshot_manager = SnapshotManager()
            snapshot_manager.create_snapshot(domain, snapshot_name, description)
            
            return {
                'success': True,
                'message': f'Snapshot {snapshot_name} created successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Error creating snapshot {snapshot_name}: {e}")
            return {'success': False, 'error': str(e)}

    def _restore_snapshot(self, domain, snapshot_name: str) -> Dict[str, Any]:
        """Restore VM from snapshot."""
        try:
            snapshot = domain.snapshotLookupByName(snapshot_name)
            domain.revertToSnapshot(snapshot)
            
            return {
                'success': True,
                'message': f'Successfully restored from snapshot {snapshot_name}'
            }
            
        except Exception as e:
            self.logger.error(f"Error restoring snapshot {snapshot_name}: {e}")
            return {'success': False, 'error': str(e)}

    def _delete_snapshot(self, domain, snapshot_name: str) -> Dict[str, Any]:
        """Delete a snapshot."""
        try:
            snapshot = domain.snapshotLookupByName(snapshot_name)
            snapshot.delete()
            
            return {
                'success': True,
                'message': f'Snapshot {snapshot_name} deleted successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Error deleting snapshot {snapshot_name}: {e}")
            return {'success': False, 'error': str(e)}

    def _extract_description(self, xml_desc: str) -> str:
        """Extract description from snapshot XML."""
        try:
            # Basic XML parsing to extract description
            # In production, use proper XML parsing
            import re
            match = re.search(r'<description>(.*?)</description>', xml_desc)
            return match.group(1) if match else ''
        except Exception:
            return ''