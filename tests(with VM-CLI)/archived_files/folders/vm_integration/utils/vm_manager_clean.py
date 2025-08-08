#!/usr/bin/env python3
"""
Virtual Machine Management Utility

Comprehensive libvirt VM lifecycle management including connection handling,
VM discovery, startup/shutdown operations, and network configuration.
Integrates with the LPEM Manager for enhanced functionality.
"""

import sys
import time
import logging
from typing import Optional, Dict, List, Any, Union
from pathlib import Path

# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("VM Manager requires Python 3.8+. Please upgrade.")
    sys.exit(1)

# Import required dependencies
try:
    import libvirt  # type: ignore
except ImportError:
    print("Error: Missing required library 'libvirt-python'.\n"
          "Please install it (e.g., 'pip install libvirt-python' or via system package manager) and try again.", 
          file=sys.stderr)
    sys.exit(1)

# Import local modules
from .lpem_manager import LPEMManager, Config
from .exceptions import (
    PracticeToolError, VMNotFoundError, NetworkError, LibvirtConnectionError
)

# Rich console support with fallback
try:
    from rich.console import Console as RichConsole
    _rich_available = True
    console = RichConsole()
except ImportError:
    _rich_available = False
    class FallbackConsole:
        def print(self, *args: Any, **kwargs: Any) -> None:
            print(*args)
    
    console = FallbackConsole()

class VMManager:
    """
    VM Management wrapper that integrates with LPEMManager.
    
    Provides a simplified interface for VM operations while leveraging
    the comprehensive functionality of the LPEM Manager.
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize VM Manager with LPEM integration.
        
        Args:
            debug: Enable debug logging
        """
        self.debug = debug
        self.lpem = LPEMManager(debug=debug)
        self.logger = logging.getLogger(__name__)

    def list_vms(self) -> List[Dict[str, Any]]:
        """List all VMs with their current status."""
        return self.lpem.list_vms()

    def find_vm(self, vm_name: str) -> libvirt.virDomain:
        """Find a VM by name."""
        return self.lpem.find_vm(vm_name)

    def start_vm(self, vm_name: Union[str, libvirt.virDomain]) -> bool:
        """Start a VM by name or domain object."""
        if isinstance(vm_name, str):
            return self.lpem.start_vm(vm_name)
        else:
            # If passed a domain object, get its name
            domain_name = vm_name.name()
            return self.lpem.start_vm(domain_name)

    def shutdown_vm(self, vm_name: Union[str, libvirt.virDomain], force: bool = False) -> bool:
        """Shutdown a VM by name or domain object."""
        if isinstance(vm_name, str):
            return self.lpem.shutdown_vm(vm_name, force=force)
        else:
            # If passed a domain object, get its name
            domain_name = vm_name.name()
            return self.lpem.shutdown_vm(domain_name, force=force)

    def get_vm_ip(self, vm_name: Union[str, libvirt.virDomain]) -> str:
        """Get VM IP address."""
        if isinstance(vm_name, str):
            domain = self.lpem.find_vm(vm_name)
        else:
            domain = vm_name
        return self.lpem.get_vm_ip(domain)

    def wait_for_vm_ready(self, vm_name: str, user: str = Config.DEFAULT_SSH_USER, 
                         key_path: Path = Config.DEFAULT_SSH_KEY_PATH,
                         timeout: int = Config.VM_READINESS_TIMEOUT_SECONDS) -> str:
        """Wait for VM to become SSH accessible."""
        return self.lpem.wait_for_vm_ready(vm_name, user, key_path, timeout)

    def run_ssh_command(self, vm_name: Union[str, libvirt.virDomain], command: str,
                       user: str = Config.DEFAULT_SSH_USER,
                       key_path: Path = Config.DEFAULT_SSH_KEY_PATH,
                       timeout: int = Config.SSH_COMMAND_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Execute SSH command on VM."""
        # Get IP address
        if isinstance(vm_name, str):
            domain = self.lpem.find_vm(vm_name)
        else:
            domain = vm_name
        
        ip_address = self.lpem.get_vm_ip(domain)
        return self.lpem.run_ssh_command(ip_address, user, key_path, command, timeout)

    def connect_libvirt(self) -> libvirt.virConnect:
        """Connect to libvirt."""
        return self.lpem.connect_libvirt()

    def close_libvirt(self) -> None:
        """Close libvirt connection."""
        self.lpem.close_libvirt()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit with cleanup."""
        self.close_libvirt()

    def __del__(self):
        """Destructor with cleanup."""
        self.close_libvirt()

# Legacy function wrappers for backward compatibility
def connect_libvirt(uri: str = Config.LIBVIRT_URI) -> libvirt.virConnect:
    """Legacy function - use VMManager instead."""
    manager = LPEMManager()
    return manager.connect_libvirt()

def close_libvirt(conn: Optional[libvirt.virConnect] = None) -> None:
    """Legacy function - use VMManager instead."""
    if conn:
        try:
            conn.close()
        except Exception:
            pass

def list_vms(conn: Optional[libvirt.virConnect] = None) -> List[Dict[str, Any]]:
    """Legacy function - use VMManager instead."""
    manager = LPEMManager()
    return manager.list_vms()

def find_vm(vm_name: str, conn: Optional[libvirt.virConnect] = None) -> libvirt.virDomain:
    """Legacy function - use VMManager instead."""
    manager = LPEMManager()
    return manager.find_vm(vm_name)

def start_vm(domain: libvirt.virDomain) -> bool:
    """Legacy function - use VMManager instead."""
    manager = LPEMManager()
    vm_name = domain.name()
    return manager.start_vm(vm_name)

def shutdown_vm(domain: libvirt.virDomain, force: bool = False) -> bool:
    """Legacy function - use VMManager instead."""
    manager = LPEMManager()
    vm_name = domain.name()
    return manager.shutdown_vm(vm_name, force=force)

def get_vm_ip(domain: libvirt.virDomain) -> str:
    """Legacy function - use VMManager instead."""
    manager = LPEMManager()
    return manager.get_vm_ip(domain)

def wait_for_vm_ready(vm_name: str, timeout: int = Config.VM_READINESS_TIMEOUT_SECONDS) -> str:
    """Legacy function - use VMManager instead."""
    manager = LPEMManager()
    return manager.wait_for_vm_ready(vm_name, timeout=timeout)
