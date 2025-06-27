#!/usr/bin/env python3
"""
Virtual Machine Management Utility

Comprehensive libvirt VM lifecycle management including connection handling,
VM discovery, startup/shutdown operations, and network configuration.
Provides robust error handling and user-friendly status reporting.
"""

import sys
import time
import logging
from typing import Optional, Dict, List, Any, Tuple
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
from .config import VMConfiguration, LibvirtErrorCodes
from .exceptions import (
    PracticeToolError, VMNotFoundError, NetworkError
)
from .console_helper import console, Table, RICH_AVAILABLE

from typing import Any
from rich.console import Console

console: Console  # type annotation for static analysis
domain_info: Tuple[int, int, int, int, int]  # type annotation for static analysis

class VMManager:
    """
    Advanced virtual machine lifecycle management with libvirt integration.
    
    Provides comprehensive VM operations including connection management,
    VM discovery, lifecycle control, and network configuration with
    robust error handling and detailed status reporting.
    """
    
    def __init__(self, libvirt_uri: Optional[str] = None):
        """
        Initialize VM manager with optional libvirt connection URI.
        
        Args:
            libvirt_uri: Optional libvirt connection URI override
        """
        self._setup_logging()
        self.libvirt_uri = libvirt_uri or VMConfiguration.LIBVIRT_URI
        self.connection = None
        self.logger = logging.getLogger(__name__)
    
    def _setup_logging(self) -> None:
        """Configure comprehensive logging infrastructure for VM operations."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('vm_manager.log')
            ]
        )
    
    def connect_libvirt(self) -> libvirt.virConnect:
        """
        Establish connection to libvirt daemon with comprehensive error handling.
        
        Returns:
            libvirt.virConnect: Active libvirt connection object
            
        Raises:
            PracticeToolError: If connection establishment fails
        """
        try:
            self.logger.info(f"Connecting to libvirt at: {self.libvirt_uri}")
            
            # Attempt connection to libvirt daemon
            raw_conn = libvirt.open(self.libvirt_uri)  # type: ignore
            conn = raw_conn
            
            # Verify connection functionality
            try:
                hostname = conn.getHostname()
                self.logger.info(f"Successfully connected to libvirt host: {hostname}")
            except libvirt.libvirtError as e:
                self.logger.warning(f"Connection established but hostname query failed: {e}")
            
            self.connection = conn
            return conn
            
        except libvirt.libvirtError as e:
            error_msg = f"Libvirt connection error: {e}"
            self.logger.error(error_msg)
            raise PracticeToolError(
                error_msg,
                error_code="LIBVIRT_ERROR",
                context={"uri": self.libvirt_uri, "libvirt_error": str(e)}
            ) from e
        except Exception as e:
            error_msg = f"Unexpected error during libvirt connection: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise PracticeToolError(
                error_msg,
                error_code="UNEXPECTED_CONNECTION_ERROR",
                context={"uri": self.libvirt_uri}
            ) from e
    
    def close_libvirt(self, conn: Optional[libvirt.virConnect] = None) -> None:
        """
        Safely close libvirt connection with proper cleanup.
        
        Args:
            conn: Optional specific connection to close, defaults to instance connection
        """
        connection_to_close = conn or self.connection
        
        if connection_to_close is not None:
            try:
                connection_to_close.close()
                self.logger.info("Libvirt connection closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing libvirt connection: {e}")
            finally:
                if conn is None:  # Only clear instance connection if closing default
                    self.connection = None
    
    def find_vm(self, conn: libvirt.virConnect, vm_name: str) -> libvirt.virDomain:
        """
        Locate virtual machine by name with comprehensive error handling.
        
        Args:
            conn: Active libvirt connection
            vm_name: Name of the virtual machine to locate
            
        Returns:
            libvirt.virDomain: Domain object for the specified VM
            
        Raises:
            VMNotFoundError: If VM cannot be found or accessed
        """
        try:
            self.logger.debug(f"Searching for VM: {vm_name}")
            
            # Attempt to lookup domain by name
            domain = conn.lookupByName(vm_name)
            
            # Verify domain accessibility
            try:
                domain_info: Tuple[int, int, int, int, int] = domain.info()
                self.logger.info(f"VM '{vm_name}' found with state: {self._get_domain_state_name(domain_info[0])}")
            except libvirt.libvirtError as e:
                self.logger.warning(f"VM found but info query failed: {e}")
            
            return domain
            
        except libvirt.libvirtError as e:
            if e.get_error_code() == LibvirtErrorCodes.VIR_ERR_NO_DOMAIN:
                self.logger.error(f"VM '{vm_name}' not found in libvirt")
                raise VMNotFoundError(vm_name, self.libvirt_uri) from e
            else:
                error_msg = f"Error accessing VM '{vm_name}': {e}"
                self.logger.error(error_msg)
                raise PracticeToolError(
                    error_msg,
                    error_code="VM_ACCESS_ERROR",
                    context={"vm_name": vm_name, "libvirt_error": str(e)}
                ) from e
    
    def list_vms(self, conn: libvirt.virConnect) -> None:
        """
        Display comprehensive list of available virtual machines.
        
        Args:
            conn: Active libvirt connection
        """
        try:
            self.logger.info("Retrieving VM list from libvirt")
            
            # Get all domains (running and defined)
            active_domains = conn.listDomainsID()
            defined_domains: List[str] = conn.listDefinedDomains()
            
            if not active_domains and not defined_domains:
                console.print("[yellow]No virtual machines found in libvirt.[/]")
                return
            
            # Create comprehensive VM status table
            if RICH_AVAILABLE:
                table = Table(title="Available Virtual Machines", show_header=True, header_style="bold cyan")
                table.add_column("Name", style="bold", min_width=20)
                table.add_column("State", width=12)
                table.add_column("CPU(s)", width=8)
                table.add_column("Memory", width=12)
                table.add_column("ID", min_width=8)
            else:
                console.print("--- Available Virtual Machines ---")
                console.print(f"{'Name':<20} {'State':<12} {'CPU(s)':<8} {'Memory':<12} {'ID':<8}")
                console.print("-" * 70)
            
            # Process active (running) domains
            for domain_id in (int(x) for x in active_domains):
                try:
                    domain = conn.lookupByID(int(domain_id))
                    self._add_vm_to_display(domain, table if RICH_AVAILABLE else None, domain_id)
                except libvirt.libvirtError as e:
                    self.logger.warning(f"Error accessing active domain ID {domain_id}: {e}")
            
            # Process defined (inactive) domains
            for domain_name in defined_domains:
                try:
                    domain = conn.lookupByName(domain_name)
                    self._add_vm_to_display(domain, table if RICH_AVAILABLE else None)
                except libvirt.libvirtError as e:
                    self.logger.warning(f"Error accessing defined domain '{domain_name}': {e}")
            
            # Display the results
            if RICH_AVAILABLE:
                console.print(table)
            
        except libvirt.libvirtError as e:
            error_msg = f"Error retrieving VM list: {e}"
            self.logger.error(error_msg)
            console.print(f"[red]Error listing VMs: {e}[/]")
            
    def _add_vm_to_display(self, domain: libvirt.virDomain, table: Optional[Any], 
                          domain_id: Optional[int] = None) -> None:
        """
        Add VM information to display table or console output.
        
        Args:
            domain: Libvirt domain object
            table: Rich table object (if available)
            domain_id: Optional domain ID for active domains
        """
        try:
            name: str = domain.name()
            info = domain.info()
            state = self._get_domain_state_name(info[0])
            max_mem = f"{info[1] // 1024} MB"
            cpu_count = str(int(info[3]))
            vm_id = str(domain_id) if domain_id is not None else "-"
            
            # Color coding for states
            if state == "running":
                state_display = f"[green]{state}[/]" if RICH_AVAILABLE else state
            elif state == "shut off":
                state_display = f"[red]{state}[/]" if RICH_AVAILABLE else state
            else:
                state_display = f"[yellow]{state}[/]" if RICH_AVAILABLE else state
            
            if RICH_AVAILABLE and table:
                table.add_row(name, state_display, cpu_count, max_mem, vm_id)
            else:
                # Fallback console output
                console.print(f"{name:<20} {state:<12} {cpu_count:<8} {max_mem:<12} {vm_id:<8}")
                
        except Exception as e:
            self.logger.warning(f"Error retrieving domain info for display: {e}")
    
    def _get_domain_state_name(self, state_code: int) -> str:
        """
        Convert libvirt domain state code to human-readable name.
        
        Args:
            state_code: Libvirt domain state code
            
        Returns:
            str: Human-readable state name
        """
        state_names = {
            libvirt.VIR_DOMAIN_NOSTATE: "no state",
            libvirt.VIR_DOMAIN_RUNNING: "running", 
            libvirt.VIR_DOMAIN_BLOCKED: "blocked",
            libvirt.VIR_DOMAIN_PAUSED: "paused",
            libvirt.VIR_DOMAIN_SHUTDOWN: "shutting down",
            libvirt.VIR_DOMAIN_SHUTOFF: "shut off",
            libvirt.VIR_DOMAIN_CRASHED: "crashed",
            libvirt.VIR_DOMAIN_PMSUSPENDED: "suspended"
        }
        return state_names.get(state_code, f"unknown({state_code})")
    
    def start_vm(self, domain: libvirt.virDomain) -> None:
        """
        Start virtual machine with comprehensive state management.
        
        Args:
            domain: Libvirt domain object to start
            
        Raises:
            PracticeToolError: If VM startup fails
        """
        vm_name = domain.name()
        
        try:
            # Check current VM state
            info: tuple = domain.info()
            current_state = info[0]
            
            if current_state == libvirt.VIR_DOMAIN_RUNNING:
                console.print(f"[green]VM '{vm_name}' is already running.[/]")
                return
            
            console.print(f"[yellow]Starting VM '{vm_name}'...[/]")
            self.logger.info(f"Attempting to start VM: {vm_name}")
            
            # Start the domain
            result = domain.create()
            if result == 0:
                console.print(f"[green]VM '{vm_name}' started successfully.[/]")
                self.logger.info(f"VM '{vm_name}' started successfully")
            else:
                raise PracticeToolError(
                    f"VM start operation returned unexpected result: {result}",
                    error_code="VM_START_UNEXPECTED_RESULT",
                    context={"vm_name": vm_name, "result": result}
                )
                
        except libvirt.libvirtError as e:
            error_msg = f"Failed to start VM '{vm_name}': {e}"
            self.logger.error(error_msg)
            raise PracticeToolError(
                error_msg,
                error_code="VM_START_FAILED",
                context={"vm_name": vm_name, "libvirt_error": str(e)}
            ) from e
    
    def get_vm_ip(self, conn: libvirt.virConnect, domain: libvirt.virDomain) -> str:
        """
        Retrieve VM IP address using libvirt guest agent or DHCP lease information.
        
        Args:
            conn: Active libvirt connection
            domain: Libvirt domain object
            
        Returns:
            str: VM IP address
            
        Raises:
            NetworkError: If IP address cannot be determined
        """
        vm_name = domain.name()
        self.logger.info(f"Attempting to get IP address for VM: {vm_name}")
        
        try:
            # Method 1: Try libvirt guest agent
            try:
                interfaces_raw = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT)  # type: ignore
                interfaces = interfaces_raw  # type: Dict[str, Any]
                ip_address = self._extract_ip_from_interfaces(interfaces, vm_name)
                if ip_address:
                    self.logger.info(f"Got IP from guest agent for '{vm_name}': {ip_address}")
                    return ip_address
            except libvirt.libvirtError as agent_error:
                self.logger.debug(f"Guest agent method failed for '{vm_name}': {agent_error}")

            # Method 2: Try DHCP lease information
            try:
                interfaces_raw = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)  # type: ignore
                from typing import cast
                interfaces = cast(Dict[str, Any], interfaces_raw)
                ip_address = self._extract_ip_from_interfaces(interfaces, vm_name)
                if ip_address:
                    self.logger.info(f"Got IP from DHCP lease for '{vm_name}': {ip_address}")
                    return ip_address
            except libvirt.libvirtError as lease_error:
                self.logger.debug(f"DHCP lease method failed for '{vm_name}': {lease_error}")

            # Method 3: Try ARP information
            try:
                interfaces_raw = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_ARP)  # type: ignore
                interfaces: Dict[str, Any] = interfaces_raw
                ip_address = self._extract_ip_from_interfaces(interfaces, vm_name)
                if ip_address:
                    self.logger.info(f"Got IP from ARP for '{vm_name}': {ip_address}")
                    return ip_address
            except libvirt.libvirtError as arp_error:
                self.logger.debug(f"ARP method failed for '{vm_name}': {arp_error}")

            # If all methods fail
            error_msg = f"Could not determine IP address for VM '{vm_name}' using any available method"
            self.logger.error(error_msg)
            raise NetworkError(error_msg, str(vm_name))

        except Exception as e:
            if isinstance(e, NetworkError):
                raise
            error_msg = f"Unexpected error getting IP for VM '{vm_name}': {e}"
            self.logger.error(error_msg, exc_info=True)
            raise NetworkError(error_msg, host=str(vm_name)) from e
    def get_vm_ip_address(domain: libvirt.virDomain) -> str:
        """Backward compatibility function for IP retrieval with just domain parameter."""
        # Get the connection from the domain
        conn = domain.connect()
        manager = VMManager()
        return manager.get_vm_ip(conn, domain)
    def _extract_ip_from_interfaces(self, interfaces: Dict[str, Any], vm_name: str) -> Optional[str]:
        """
        Extract IPv4 address from libvirt interface information.
        
        Args:
            interfaces: Interface information from libvirt
            vm_name (str): VM name for logging context
            
        Returns:
            Optional[str]: IPv4 address if found, None otherwise
        """
        try:
            for interface_name, interface_data in interfaces.items():
                if interface_data is None:
                    continue
                
                addresses = interface_data.get('addrs', [])
                for addr_info in addresses:
                    if addr_info['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                        ip_addr = addr_info['addr']
                        # Skip loopback addresses
                        if not ip_addr.startswith('127.'):
                            self.logger.debug(f"Found IPv4 address for '{vm_name}' on {interface_name}: {ip_addr}")
                            return ip_addr
                            
        except Exception as e:
            self.logger.debug(f"Error extracting IP from interfaces for '{vm_name}': {e}")
        
        return None
    
    def wait_for_vm_ready(self, vm_ip: str, ssh_user: str, ssh_key_path: Path, 
                         timeout: int = VMConfiguration.READINESS_TIMEOUT_SECONDS) -> None:
        """
        Wait for VM to become SSH accessible with comprehensive readiness checking.
        
        Args:
            vm_ip: VM IP address to test
            ssh_user: SSH username for connection testing
            ssh_key_path: Path to SSH private key
            timeout: Maximum wait time in seconds
            
        Raises:
            NetworkError: If VM doesn't become ready within timeout
        """
        from .ssh_manager import SSHManager  # Import here to avoid circular dependency
        
        console.print(f"[yellow]Waiting for VM at {vm_ip} to become ready (timeout: {timeout}s)...[/]")
        self.logger.info(f"Testing SSH connectivity to {vm_ip} as user '{ssh_user}'")
        
        ssh_manager = SSHManager()
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                # Quick SSH connectivity test
                result = ssh_manager.test_connection(vm_ip, ssh_user, ssh_key_path)
                if result:
                    elapsed = int(time.time() - start_time)
                    console.print(f"[green]VM is ready! SSH connection established after {elapsed}s.[/]")
                    self.logger.info(f"VM at {vm_ip} became ready after {elapsed} seconds")
                    return
                    
            except Exception as e:
                self.logger.debug(f"SSH test failed (will retry): {e}")
            
            # Wait before next attempt
            time.sleep(VMConfiguration.READINESS_POLL_INTERVAL_SECONDS)
            console.print(".", end="")
        
        # Timeout reached
        elapsed = int(time.time() - start_time)
        error_msg = f"VM at {vm_ip} did not become ready within {timeout} seconds"
        self.logger.error(error_msg)
        console.print(f"\n[red]Timeout: VM not ready after {elapsed}s[/]")
        
        raise NetworkError(
            error_msg,
            host=vm_ip,
            timeout=timeout
        )

def get_vm_ip_address(domain: libvirt.virDomain) -> str:
    """Backward compatibility function for IP retrieval with just domain parameter."""
    # Get the connection from the domain
    conn = domain.connect()
    manager = VMManager()
    return manager.get_vm_ip(conn, domain)
# Convenience functions for backward compatibility with ww.py
def connect_libvirt(uri: Optional[str] = None) -> libvirt.virConnect:
    """Backward compatibility function for libvirt connection."""
    manager = VMManager(uri)
    return manager.connect_libvirt()

def close_libvirt(conn: libvirt.virConnect) -> None:
    """Backward compatibility function for libvirt disconnection."""
    manager = VMManager()
    manager.close_libvirt(conn)

def find_vm(conn: libvirt.virConnect, vm_name: str) -> libvirt.virDomain:
    """Backward compatibility function for VM lookup."""
    manager = VMManager()
    return manager.find_vm(conn, vm_name)

def list_vms(conn: libvirt.virConnect) -> None:
    """Backward compatibility function for VM listing."""
    manager = VMManager()
    manager.list_vms(conn)

def start_vm(domain: libvirt.virDomain) -> None:
    """Backward compatibility function for VM startup."""
    manager = VMManager()
    manager.start_vm(domain)

def get_vm_ip(conn: libvirt.virConnect, domain: libvirt.virDomain) -> str:
    """Backward compatibility function for IP retrieval."""
    manager = VMManager()
    return manager.get_vm_ip(conn, domain)

def wait_for_vm_ready(vm_ip: str, ssh_user: str, ssh_key_path: Path, timeout: int = VMConfiguration.READINESS_TIMEOUT_SECONDS) -> None:
    """Backward compatibility function for readiness waiting."""
    manager = VMManager()
    manager.wait_for_vm_ready(vm_ip, ssh_user, ssh_key_path, timeout)


# Export all public components
__all__ = [
    'VMManager',
    'connect_libvirt', 'close_libvirt', 'find_vm', 'list_vms', 
    'start_vm', 'get_vm_ip', 'get_vm_ip_address', 'wait_for_vm_ready'
]