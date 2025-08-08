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
from typing import Optional, Dict, List, Any, Tuple, Union
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
from .lpem_manager import LPEMManager
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
        Initialize VM Manager.
        
        Args:
            debug: Enable debug logging
        """
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        
        # Initialize LPEM Manager
        self.lpem = LPEMManager(debug=debug)

    def connect_libvirt(self) -> libvirt.virConnect:
        """Connect to libvirt using LPEM Manager."""
        return self.lpem.connect_libvirt()

    def find_vm(self, conn: libvirt.virConnect, vm_name: str) -> libvirt.virDomain:
        """Find a VM domain by name."""
        return self.lpem.find_vm(vm_name)

    def list_vms(self) -> List[Dict[str, Any]]:
        """List all VMs with their status."""
        return self.lpem.list_vms()

    def start_vm(self, domain: libvirt.virDomain) -> bool:
        """Start a VM using its domain object."""
        vm_name = domain.name()
        return self.lpem.start_vm(vm_name)

    def shutdown_vm(self, domain: libvirt.virDomain, force: bool = False) -> bool:
        """Shutdown a VM using its domain object."""
        vm_name = domain.name()
        return self.lpem.shutdown_vm(vm_name, force=force)

    def get_vm_ip(self, conn: libvirt.virConnect, domain: libvirt.virDomain) -> str:
        """Get VM IP address."""
        return self.lpem.get_vm_ip(domain)

    def wait_for_vm_ready(self, vm_name: str, user: str = "root", 
                         key_path: Optional[Path] = None, 
                         timeout: int = 120) -> str:
        """Wait for VM to become SSH-ready."""
        if key_path is None:
            key_path = Path("~/.ssh/id_ed25519").expanduser()
        
        return self.lpem.wait_for_vm_ready(vm_name, user, key_path, timeout)

    def run_ssh_command(self, host: str, username: str, key_path: Path, 
                       command: str, timeout: int = 30, verbose: bool = False) -> Dict[str, Any]:
        """Execute SSH command on a VM."""
        return self.lpem.run_ssh_command(host, username, key_path, command, timeout)

    def close_connection(self):
        """Close libvirt connection."""
        self.lpem.close_libvirt()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close_connection()

# Maintain backward compatibility
class VMConfiguration:
    """VM Configuration class for backward compatibility."""
    
    def __init__(self):
        self.libvirt_uri = 'qemu:///system'
        self.vm_readiness_timeout = 120
        self.vm_readiness_poll_interval = 5
        self.vm_shutdown_timeout = 120
        self.ssh_user = "root"
        self.ssh_key_path = Path("~/.ssh/id_ed25519").expanduser()
        self.ssh_connect_timeout = 10
        self.ssh_command_timeout = 30
        self.agent_timeout = 10

# Legacy function wrappers for backward compatibility
def connect_libvirt() -> libvirt.virConnect:
    """Legacy function - use VMManager instead."""
    manager = VMManager()
    return manager.connect_libvirt()

def find_vm(conn: libvirt.virConnect, vm_name: str) -> libvirt.virDomain:
    """Legacy function - use VMManager instead."""
    manager = VMManager()
    return manager.find_vm(conn, vm_name)

def list_vms(conn: libvirt.virConnect) -> List[Dict[str, Any]]:
    """Legacy function - use VMManager instead."""
    manager = VMManager()
    return manager.list_vms()

def start_vm(domain: libvirt.virDomain) -> bool:
    """Legacy function - use VMManager instead."""
    manager = VMManager()
    return manager.start_vm(domain)

def shutdown_vm(domain: libvirt.virDomain, force: bool = False) -> bool:
    """Legacy function - use VMManager instead."""
    manager = VMManager()
    return manager.shutdown_vm(domain, force)

def get_vm_ip(conn: libvirt.virConnect, domain: libvirt.virDomain) -> str:
    """Legacy function - use VMManager instead."""
    manager = VMManager()
    return manager.get_vm_ip(conn, domain)

console: Console  # type annotation for static analysis

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
            conn: libvirt.virConnect = libvirt.open(self.libvirt_uri)  # type: ignore
            
            # Verify connection functionality
            try:
                hostname = cast(str, conn.getHostname())
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
            
            # Add explicit type annotation for the lookup result
            domain = cast(libvirt.virDomain, conn.lookupByName(vm_name))
            
            # Verify domain accessibility
            try:
                domain_info = cast(DomainInfo, domain.info())
                state_code = cast(int, domain_info[0])
                self.logger.info(f"VM '{vm_name}' found with state: {self._get_domain_state_name(state_code)}")
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
            active_domains = cast(List[DomainID], conn.listDomainsID())
            defined_domains = cast(List[DomainName], conn.listDefinedDomains())
            
            if not active_domains and not defined_domains:
                console.print("[yellow]No virtual machines found in libvirt.[/]")
                return
            
            # Create comprehensive VM status table
            table = None
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
            for domain_id in active_domains:
                try:
                    domain_id_int = cast(int, domain_id)
                    domain = cast(libvirt.virDomain, conn.lookupByID(domain_id_int))
                    self._add_vm_to_display(domain, table, domain_id_int)
                except libvirt.libvirtError as e:
                    self.logger.warning(f"Error accessing active domain ID {domain_id}: {e}")
            
            # Process defined (inactive) domains
            for domain_name in defined_domains:
                try:
                    domain_name_str = cast(str, domain_name)
                    domain = cast(libvirt.virDomain, conn.lookupByName(domain_name_str))
                    self._add_vm_to_display(domain, table)
                except libvirt.libvirtError as e:
                    self.logger.warning(f"Error accessing defined domain '{domain_name}': {e}")
            
            # Display the results
            if RICH_AVAILABLE and table:
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
            name = cast(str, domain.name())
            info = cast(DomainInfo, domain.info())
            state = self._get_domain_state_name(cast(int, info[0]))
            max_mem = f"{info[1] // 1024} MB"
            cpu_count = str(cast(int, info[3]))
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
    
    def _check_and_fix_vm_permissions(self, domain: libvirt.virDomain, auto_fix: bool = True) -> bool:
        """
        Check and optionally fix VM disk file permissions.
        
        Args:
            domain: Libvirt domain object
            auto_fix: Whether to automatically attempt permission fixes
            
        Returns:
            bool: True if permissions are correct or successfully fixed
        """
        vm_name = cast(str, domain.name())
        
        try:
            # Get VM XML to find disk files
            raw_xml = cast(str, domain.XMLDesc(0))
            tree = ET.fromstring(raw_xml)
            
            permission_issues: List[Dict[str, Any]] = []
            
            # Check each disk device
            for device in tree.findall('devices/disk'):
                if device.get('type') == 'file' and device.get('device') == 'disk':
                    source_node = device.find('source')
                    if source_node is not None and 'file' in source_node.attrib:
                        file_path = source_node.get('file')
                        if file_path is not None:
                            disk_path = Path(file_path)
                            
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
            
            if not permission_issues:
                self.logger.debug(f"VM '{vm_name}' disk permissions are correct")
                return True
            
            # Report permission issues
            console.print(f"[yellow]:warning: Permission issues detected for VM '{vm_name}':[/]")
            for issue in permission_issues:
                console.print(f"  File: {issue['path']}")
                console.print(f"    Current: {issue['current_owner']}:{issue['current_group']} {issue['current_perms']}")
                console.print(f"    Expected: {issue['expected_owner']}:{issue['expected_group']} {issue['expected_perms']}")
            
            if not auto_fix:
                console.print("[yellow]Use --auto-fix-permissions to automatically correct these issues.[/]")
                return False
            
            # Attempt to fix permissions
            console.print("[yellow]Attempting to fix VM disk permissions...[/]")
            
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
                    disk_path = cast(Path, issue['path'])
                    
                    # Fix ownership
                    chown_cmd = ['sudo', 'chown', 'libvirt-qemu:libvirt', str(disk_path)]
                    subprocess.run(chown_cmd, check=True, capture_output=True)
                    
                    # Fix permissions
                    chmod_cmd = ['sudo', 'chmod', '660', str(disk_path)]
                    subprocess.run(chmod_cmd, check=True, capture_output=True)
                    
                    console.print(f"[green]Fixed permissions for: {disk_path}[/]")
                    success_count += 1
                    
                except subprocess.CalledProcessError as e:
                    # Ensure disk_path is defined before using it
                    path_str = str(issue.get('path', 'unknown path'))
                    console.print(f"[red]Failed to fix permissions for {path_str}: {e}[/]")
                    self.logger.error(f"Permission fix failed for {path_str}: {e}")
            
            if success_count == len(permission_issues):
                console.print(f"[green]Successfully fixed all {success_count} permission issues.[/]")
                
                # Restart libvirtd to ensure changes take effect
                try:
                    console.print("[yellow]Restarting libvirtd service...[/]")
                    subprocess.run(['sudo', 'systemctl', 'restart', 'libvirtd'], check=True, capture_output=True)
                    console.print("[green]Libvirtd service restarted successfully.[/]")
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

    def start_vm(self, domain: libvirt.virDomain, auto_fix_permissions: bool = True) -> None:
        """
        Start a virtual machine with automatic permission checking and fixing.
        
        Args:
            domain: Libvirt domain object to start
            auto_fix_permissions: Whether to automatically fix permission issues
            
        Raises:
            PracticeToolError: If VM startup fails
        """
        vm_name = cast(str, domain.name())
        
        try:
            # Check current VM state
            info = cast(Tuple[Any, ...], domain.info())
            current_state = cast(int, info[0])
            
            if current_state == libvirt.VIR_DOMAIN_RUNNING:
                console.print(f"[green]VM '{vm_name}' is already running.[/]")
                return
            
            console.print(f"[yellow]Starting VM '{vm_name}'...[/]")
            self.logger.info(f"Attempting to start VM: {vm_name}")
            
            # First attempt to start
            try:
                result = cast(int, domain.create())
                if result == 0:
                    console.print(f"[green]VM '{vm_name}' started successfully.[/]")
                    self.logger.info(f"VM '{vm_name}' started successfully")
                    return
                else:
                    raise PracticeToolError(
                        f"VM start operation returned unexpected result: {result}",
                        error_code="VM_START_UNEXPECTED_RESULT",
                        context={"vm_name": vm_name, "result": result}
                    )
            
            except libvirt.libvirtError as e:
                # Check if this is a permission issue
                if "Permission denied" in str(e):
                    console.print(f"[yellow]Permission issue detected. Checking VM disk permissions...[/]")
                    
                    # Try to fix permissions
                    if auto_fix_permissions and self._check_and_fix_vm_permissions(domain, auto_fix=True):
                        console.print(f"[yellow]Retrying VM start after permission fix...[/]")
                        
                        # Retry starting the VM
                        try:
                            result = domain.create()
                            if result == 0:
                                console.print(f"[green]VM '{vm_name}' started successfully after permission fix.[/]")
                                self.logger.info(f"VM '{vm_name}' started successfully after permission fix")
                                return
                        except libvirt.libvirtError as retry_error:
                            # If retry fails, fall through to original error handling
                            e = retry_error
                    
                    # Permission fix failed or not attempted
                    error_msg = f"Failed to start VM '{vm_name}': {e}"
                    error_msg += "\n\nThis is likely a permission issue. Try:"
                    error_msg += "\n1. sudo usermod -a -G libvirt $USER"
                    error_msg += "\n2. Log out and back in"
                    error_msg += "\n3. Or run: sudo chown libvirt-qemu:libvirt /var/lib/libvirt/images/*.qcow2"
                    error_msg += "\n4. sudo chmod 660 /var/lib/libvirt/images/*.qcow2"
                    
                    self.logger.error(error_msg)
                    raise PracticeToolError(
                        error_msg,
                        error_code="VM_START_FAILED",
                        context={"vm_name": vm_name, "libvirt_error": str(e)}
                    ) from e
                else:
                    # Not a permission issue, raise original error
                    raise
                    
        except libvirt.libvirtError as e:
            error_msg = f"Failed to start VM '{vm_name}': {e}"
            self.logger.error(error_msg)
            raise PracticeToolError(
                error_msg,
                error_code="VM_START_FAILED",
                context={"vm_name": vm_name, "libvirt_error": str(e)}
            ) from e
    def _shutdown_vm_gracefully(self, domain: libvirt.virDomain, timeout: int = 30) -> bool:
        """
        Attempt graceful shutdown of VM with timeout.
        
        Args:
            domain: Libvirt domain object
            timeout: Timeout in seconds for graceful shutdown
            
        Returns:
            bool: True if shutdown was successful, False if forced shutdown needed
        """
        vm_name = domain.name()
        try:
            if not domain.isActive():
                return True
                
            console.print(f"[yellow]Attempting graceful shutdown of VM '{vm_name}'...[/]")
            domain.shutdown()
            
            # Wait for graceful shutdown
            import time
            for _ in range(timeout):
                if not domain.isActive():
                    console.print(f"[green]VM '{vm_name}' shutdown gracefully.[/]")
                    return True
                time.sleep(1)
            
            console.print(f"[yellow]Graceful shutdown timeout, forcing shutdown...[/]")
            return False
            
        except Exception as e:
            self.logger.warning(f"Error during graceful shutdown of '{vm_name}': {e}")
            return False
    def shutdown_vm(self, domain: libvirt.virDomain, 
                    timeout: int = VMConfiguration.SHUTDOWN_TIMEOUT_SECONDS) -> bool:
        """
        Gracefully shutdown virtual machine with ACPI signal and force fallback.
        
        Args:
            domain: Libvirt domain object to shutdown
            timeout: Maximum wait time for graceful shutdown in seconds
            
        Returns:
            bool: True if shutdown was successful
            
        Raises:
            PracticeToolError: If shutdown fails completely
        """
        vm_name = cast(str, domain.name())
        
        try:
            # Check current VM state
            if not domain.isActive():
                console.print(f"[yellow]VM '{vm_name}' is already shut down.[/]")
                return True
            
            console.print(f"[yellow]Attempting graceful shutdown for VM '{vm_name}' (ACPI)...[/]")
            self.logger.info(f"Initiating graceful shutdown for VM: {vm_name}")
            
            # Attempt graceful ACPI shutdown
            shutdown_failed = False
            try:
                result = cast(int, domain.shutdown())
                if result < 0:
                    shutdown_failed = True
                    console.print(f"[yellow]ACPI shutdown command failed for VM '{vm_name}'. Will try force destroy if needed.[/]")
                else:
                    console.print("[dim]ACPI shutdown signal sent.[/]")
            except libvirt.libvirtError as e:
                shutdown_failed = True
                console.print(f"[yellow]Error sending ACPI shutdown signal for VM '{vm_name}': {e}[/]")
            
            # Wait for graceful shutdown with progress tracking
            if not shutdown_failed:
                console.print(f"[dim]Waiting up to {timeout}s for graceful shutdown...[/]")
                
                if RICH_AVAILABLE:
                    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
                    
                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        TimeElapsedColumn(),
                        console=console
                    ) as progress:
                        task = progress.add_task(f"Shutting down '{vm_name}'...", total=timeout)
                        start_time = time.time()
                        
                        while (time.time() - start_time) < timeout:
                            try:
                                if not domain.isActive():
                                    progress.update(task, completed=timeout, 
                                                description=f"VM '{vm_name}' shut down.")
                                    break
                                
                                elapsed = time.time() - start_time
                                progress.update(task, completed=elapsed, 
                                            description=f"Shutting down '{vm_name}'...")
                                time.sleep(3)
                                
                            except libvirt.libvirtError as e:
                                if e.get_error_code() == LibvirtErrorCodes.VIR_ERR_NO_DOMAIN:
                                    progress.update(task, completed=timeout, 
                                                description=f"VM '{vm_name}' disappeared (assumed shut down)")
                                    console.print("\n[yellow]VM disappeared during shutdown wait.[/]")
                                    return True
                                raise
                        else:
                            progress.update(task, description=f"VM '{vm_name}' still active after timeout.")
                else:
                    # Fallback progress for non-Rich environments
                    start_time = time.time()
                    while (time.time() - start_time) < timeout:
                        if not domain.isActive():
                            break
                        console.print(".", end="")
                        time.sleep(3)
                    console.print()
            
            # Check final state and force destroy if needed
            if domain.isActive():
                console.print(f"[yellow]VM '{vm_name}' did not shut down gracefully. Forcing power off (destroy)...[/]")
                self.logger.warning(f"Forcing destroy on VM '{vm_name}' after timeout")
                
                result = domain.destroy()
                if result < 0:
                    raise PracticeToolError(
                        f"Failed to destroy (force power off) VM '{vm_name}' after timeout",
                        error_code="VM_DESTROY_FAILED",
                        context={"vm_name": vm_name, "timeout": timeout}
                    )
                else:
                    console.print(f"[green]VM '{vm_name}' destroyed (forced power off).[/]")
                    time.sleep(2)  # Brief pause after destroy
                    return True
            else:
                console.print(f"[green]VM '{vm_name}' shut down successfully.[/]")
                self.logger.info(f"VM '{vm_name}' shut down gracefully")
                return True
                
        except libvirt.libvirtError as e:
            err_code = e.get_error_code()
            
            # Handle cases where VM is already gone
            if err_code == LibvirtErrorCodes.VIR_ERR_NO_DOMAIN:
                console.print(f"[yellow]VM '{vm_name}' disappeared or is already shut down.[/]")
                return True
            elif err_code == LibvirtErrorCodes.VIR_ERR_OPERATION_INVALID:
                try:
                    if not domain.isActive():
                        console.print(f"[yellow]VM '{vm_name}' is already shut down (operation invalid).[/]")
                        return True
                except libvirt.libvirtError:
                    console.print(f"[yellow]VM '{vm_name}' disappeared or is already shut down.[/]")
                    return True
            
            # Unexpected libvirt error
            error_msg = f"Error during shutdown process for VM '{vm_name}': {e}"
            self.logger.error(error_msg)
            raise PracticeToolError(
                error_msg,
                error_code="VM_SHUTDOWN_ERROR", 
                context={"vm_name": vm_name, "libvirt_error": str(e)}
            ) from e
            
        except Exception as e:
            error_msg = f"Unexpected error shutting down VM '{vm_name}': {e}"
            self.logger.error(error_msg, exc_info=True)
            raise PracticeToolError(
                error_msg,
                error_code="VM_SHUTDOWN_UNEXPECTED_ERROR",
                context={"vm_name": vm_name}
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
        if not hasattr(conn, 'getHostname'):
            raise PracticeToolError(
                "Invalid libvirt connection object provided",
                error_code="INVALID_CONNECTION_TYPE"
            )
        
        vm_name = cast(str, domain.name())
        self.logger.info(f"Attempting to get IP address for VM: {vm_name}")
        
        try:
            # Method 1: Try libvirt guest agent
            try:
                interfaces_raw = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT)  # type: ignore
                if interfaces_raw and isinstance(interfaces_raw, dict):
                    interfaces = cast(Dict[str, Any], interfaces_raw)
                    ip_address = self._extract_ip_from_interfaces(interfaces, vm_name)
                    if ip_address:
                        self.logger.info(f"Got IP from guest agent for '{vm_name}': {ip_address}")
                        return ip_address
            except libvirt.libvirtError as agent_error:
                self.logger.debug(f"Guest agent method failed for '{vm_name}': {agent_error}")

            # Method 2: Try DHCP lease information
            try:
                interfaces_raw = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)  # type: ignore
                if interfaces_raw and isinstance(interfaces_raw, dict):
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
                if interfaces_raw and isinstance(interfaces_raw, dict):
                    interfaces = cast(Dict[str, Any], interfaces_raw)
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
# Convenience functions for backward compatibility with ww.py
def connect_libvirt(uri: Optional[str] = None) -> 'libvirt.virConnect':
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
def get_vm_ip_address(domain: libvirt.virDomain) -> str:
    """Backward compatibility function for IP retrieval with just domain parameter."""
    # Get the connection from the domain
    conn = domain.connect()
    manager = VMManager()
    return manager.get_vm_ip(conn, domain)
def wait_for_vm_ready(vm_ip: str, ssh_user: str, ssh_key_path: Path, timeout: int = VMConfiguration.READINESS_TIMEOUT_SECONDS) -> None:
    """Backward compatibility function for readiness waiting."""
    manager = VMManager()
    manager.wait_for_vm_ready(vm_ip, ssh_user, ssh_key_path, timeout)
def shutdown_vm(domain: libvirt.virDomain, timeout: int = VMConfiguration.SHUTDOWN_TIMEOUT_SECONDS) -> bool:
    """Backward compatibility function for VM shutdown."""
    manager = VMManager()
    return manager.shutdown_vm(domain, timeout)

# Export all public components
__all__ = [
    'VMManager',
    'connect_libvirt', 'close_libvirt', 'find_vm', 'list_vms', 
    'start_vm', 'get_vm_ip', 'shutdown_vm', 'get_vm_ip_address', 'wait_for_vm_ready'
]