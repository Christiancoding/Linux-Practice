#!/usr/bin/env python3
"""
Linux+ Practice Environment Manager (LPEM) - Core Management Module

A comprehensive implementation integrating the ww.py functionality into the existing
VM management infrastructure. Provides VM lifecycle management, snapshot operations,
and challenge execution with robust error handling.
"""

import sys
import os
import time
import logging
import json
import socket
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("LPEM Manager requires Python 3.8+. Please upgrade.")
    sys.exit(1)

# Third-Party Library Imports
try:
    import libvirt  # type: ignore
except ImportError:
    print("Error: Missing required library 'libvirt-python'.\n"
          "Please install it (e.g., 'pip install libvirt-python' or via system package manager) and try again.", 
          file=sys.stderr)
    sys.exit(1)

try:
    import paramiko  # type: ignore
except ImportError:
    print("Error: Missing required library 'paramiko'.\n"
          "Please install it (e.g., 'pip install paramiko') and try again.", 
          file=sys.stderr)
    sys.exit(1)

try:
    import yaml  # type: ignore
except ImportError:
    print("Error: Missing required library 'PyYAML'.\n"
          "Please install it (e.g., 'pip install pyyaml') and try again.", 
          file=sys.stderr)
    sys.exit(1)

# Rich library for enhanced terminal output
try:
    import rich.console
    rich_available = True
    
    # Create console instance
    console = rich.console.Console()
    
except ImportError:
    rich_available = False
    
    # Provide dummy console implementation
    class DummyConsole:
        def print(self, *args: Any, **kwargs: Any) -> None: 
            print(*args)
    
    console = DummyConsole()

RICH_AVAILABLE = rich_available

# --- Custom Exceptions ---
class PracticeToolError(Exception):
    """Base exception for CLI operational errors."""
    pass

class LibvirtConnectionError(PracticeToolError):
    """Error connecting to libvirt."""
    pass

class VMNotFoundError(PracticeToolError):
    """VM definition not found in libvirt."""
    pass

class SnapshotOperationError(PracticeToolError):
    """Error during snapshot creation, revert, or deletion."""
    pass

class AgentCommandError(PracticeToolError):
    """Error communicating with the QEMU Guest Agent."""
    pass

class NetworkError(PracticeToolError):
    """Network-related errors (IP retrieval, SSH connection)."""
    pass

class SSHCommandError(PracticeToolError):
    """Error executing a command via SSH."""
    pass

class ChallengeLoadError(PracticeToolError):
    """Error loading or validating challenge definitions."""
    pass

class ChallengeValidationError(Exception):
    """Validation failed, containing specific reasons."""
    def __init__(self, reasons: List[str]):
        self.reasons = reasons
        super().__init__(f"Challenge validation failed: {', '.join(reasons)}")

# --- Constants and Configuration ---
class Config:
    # VM Defaults
    DEFAULT_VM_NAME: str = "ubuntu24.04-2"
    DEFAULT_SNAPSHOT_NAME: str = "practice_external_snapshot"
    VM_READINESS_TIMEOUT_SECONDS: int = 120
    VM_READINESS_POLL_INTERVAL_SECONDS: int = 5
    VM_SHUTDOWN_TIMEOUT_SECONDS: int = 120

    # SSH Defaults
    DEFAULT_SSH_USER: str = "roo"  # Updated to correct VM username
    DEFAULT_SSH_KEY_PATH: Path = Path("~/.ssh/id_ed25519").expanduser()  # Update if needed
    SSH_CONNECT_TIMEOUT_SECONDS: int = 10
    SSH_COMMAND_TIMEOUT_SECONDS: int = 120  # Increased for package management operations
    SSH_KEY_PERMISSIONS_MASK: int = 0o077  # Permissions check: only owner should have access

    # Challenge Defaults
    DEFAULT_CHALLENGES_DIR: Path = Path("./challenges")
    DEFAULT_CHALLENGE_SCORE: int = 100

    # Libvirt Connection URI
    LIBVIRT_URI: str = 'qemu:///system'

    # Exit Codes for systemctl status checks
    EXIT_CODE_ACTIVE: int = 0
    EXIT_CODE_INACTIVE: int = 3
    EXIT_CODE_FAILED_BASE: int = 1

# Get libvirt error codes safely
VIR_ERR_NO_DOMAIN = getattr(libvirt, 'VIR_ERR_NO_DOMAIN', -1)
VIR_ERR_NO_DOMAIN_SNAPSHOT = getattr(libvirt, 'VIR_ERR_NO_DOMAIN_SNAPSHOT', -1)
VIR_ERR_OPERATION_INVALID = getattr(libvirt, 'VIR_ERR_OPERATION_INVALID', -1)
VIR_ERR_AGENT_UNRESPONSIVE = getattr(libvirt, 'VIR_ERR_AGENT_UNRESPONSIVE', -1)
VIR_ERR_OPERATION_TIMEOUT = getattr(libvirt, 'VIR_ERR_OPERATION_TIMEOUT', -1)

class LPEMManager:
    """
    Linux+ Practice Environment Manager - Core management class.
    
    Integrates VM management, snapshot operations, SSH connectivity,
    and challenge execution into a unified interface.
    """
    
    def __init__(self, debug: bool = False):
        """Initialize LPEM Manager with comprehensive setup."""
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Initialize connection
        self.conn: Optional[libvirt.virConnect] = None
        
    def _setup_logging(self):
        """Setup logging configuration."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            if self.debug:
                self.logger.setLevel(logging.DEBUG)
            else:
                self.logger.setLevel(logging.INFO)

    # --- Libvirt Helper Functions ---
    def connect_libvirt(self) -> libvirt.virConnect:
        """Connect to libvirt specified by Config.LIBVIRT_URI."""
        try:
            if self.conn and self.conn.isAlive():
                return self.conn
            
            self.conn = libvirt.open(Config.LIBVIRT_URI)  # type: ignore
            if not self.conn:
                raise LibvirtConnectionError(f"Failed to connect to libvirt at {Config.LIBVIRT_URI}")
            
            self.logger.info(f"Connected to libvirt at {Config.LIBVIRT_URI}")
            return self.conn
            
        except libvirt.libvirtError as e:
            raise LibvirtConnectionError(f"Libvirt connection error: {e}")

    def find_vm(self, vm_name: str) -> libvirt.virDomain:
        """Find a VM domain by name."""
        conn = self.connect_libvirt()
        try:
            domain = conn.lookupByName(vm_name)  # type: ignore
            return domain
        except libvirt.libvirtError as e:
            if e.get_error_code() == VIR_ERR_NO_DOMAIN:
                raise VMNotFoundError(f"VM '{vm_name}' not found in libvirt")
            else:
                raise PracticeToolError(f"Error looking up VM '{vm_name}': {e}")

    def close_libvirt(self):
        """Safely close the libvirt connection."""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                self.logger.info("Libvirt connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing libvirt connection: {e}")

    # --- Core VM Operations ---
    def list_vms(self) -> List[Dict[str, Any]]:
        """List all defined VMs (active and inactive)."""
        conn = self.connect_libvirt()
        vms: List[Dict[str, Any]] = []

        try:
            # Get all domains (defined and running)
            all_domains = conn.listAllDomains()
            
            for domain in all_domains:
                vm_info: Dict[str, Any] = {
                    'name': domain.name(),
                    'status': 'running' if domain.isActive() else 'stopped',  # Changed from 'state' to 'status'
                    'id': domain.ID() if domain.isActive() else None
                }
                
                # Try to get IP if running
                if domain.isActive():
                    try:
                        vm_info['ip'] = self.get_vm_ip(domain)
                    except Exception:
                        vm_info['ip'] = 'Unknown'
                else:
                    vm_info['ip'] = 'Not running'
                
                vms.append(vm_info)

        except libvirt.libvirtError as e:
            raise PracticeToolError(f"Error listing VMs: {e}")

        return sorted(vms, key=lambda x: x['name'])

    def start_vm(self, vm_name: str) -> bool:
        """Start the specified VM."""
        domain = self.find_vm(vm_name)
        
        if domain.isActive():
            self.logger.info(f"VM '{vm_name}' is already running")
            return True
        
        try:
            if RICH_AVAILABLE:
                console.print(f":rocket: Starting VM '{vm_name}'...")
            
            domain.create()
            
            if RICH_AVAILABLE:
                console.print(f":white_check_mark: VM '{vm_name}' started successfully", style="green")
            
            self.logger.info(f"VM '{vm_name}' started successfully")
            return True
            
        except libvirt.libvirtError as e:
            error_msg = f"Failed to start VM '{vm_name}': {e}"
            self.logger.error(error_msg)
            if RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
            raise PracticeToolError(error_msg)

    def shutdown_vm(self, vm_name: str, force: bool = False) -> bool:
        """Shutdown the specified VM."""
        domain = self.find_vm(vm_name)
        
        if not domain.isActive():
            self.logger.info(f"VM '{vm_name}' is already stopped")
            return True
        
        try:
            if RICH_AVAILABLE:
                action = "force stopping" if force else "shutting down"
                console.print(f":stop_sign: {action.title()} VM '{vm_name}'...")
            
            if force:
                domain.destroy()  # Force shutdown
            else:
                domain.shutdown()  # Graceful shutdown
            
            # Wait for shutdown with timeout
            timeout = Config.VM_SHUTDOWN_TIMEOUT_SECONDS
            start_time = time.time()
            
            while domain.isActive() and (time.time() - start_time) < timeout:
                time.sleep(2)
            
            if domain.isActive():
                self.logger.warning(f"VM '{vm_name}' didn't shutdown gracefully, forcing...")
                domain.destroy()
            
            if RICH_AVAILABLE:
                console.print(f":white_check_mark: VM '{vm_name}' stopped successfully", style="green")
            
            self.logger.info(f"VM '{vm_name}' stopped successfully")
            return True
            
        except libvirt.libvirtError as e:
            error_msg = f"Failed to stop VM '{vm_name}': {e}"
            self.logger.error(error_msg)
            if RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
            raise PracticeToolError(error_msg)

    # --- QEMU Agent Functions ---
    def qemu_agent_command(self, domain: libvirt.virDomain, command_json_str: str, timeout_sec: int = 10) -> Optional[Any]:
        """Send a command to the QEMU guest agent and return the parsed JSON response."""
        if not domain.isActive():
            raise AgentCommandError("VM is not running - cannot communicate with guest agent")

        try:
            response: str = domain.qemuAgentCommand(command_json_str, timeout_sec, 0)  # type: ignore
            if response:
                return json.loads(response)  # type: ignore
            return {}

        except libvirt.libvirtError as e:
            if e.get_error_code() == VIR_ERR_AGENT_UNRESPONSIVE:
                raise AgentCommandError("QEMU guest agent is unresponsive")
            elif e.get_error_code() == VIR_ERR_OPERATION_TIMEOUT:
                raise AgentCommandError(f"QEMU guest agent command timed out after {timeout_sec} seconds")
            else:
                raise AgentCommandError(f"QEMU guest agent error: {e}")

    def qemu_agent_fsfreeze(self, domain: libvirt.virDomain) -> bool:
        """Attempt to freeze VM filesystems using the QEMU guest agent."""
        try:
            if RICH_AVAILABLE:
                console.print(":snowflake: Attempting filesystem freeze via QEMU agent...")
            
            response = self.qemu_agent_command(domain, '{"execute": "guest-fsfreeze-freeze"}')
            
            if response is None:
                return False
            elif isinstance(response, dict) and ('return' in response or response == {}):
                if RICH_AVAILABLE:
                    console.print(":white_check_mark: Filesystem freeze successful", style="green")
                return True
            else:
                return False
                
        except AgentCommandError as e:
            if RICH_AVAILABLE:
                console.print(f":warning: Filesystem freeze failed: {e}", style="yellow")
            return False

    def qemu_agent_fsthaw(self, domain: libvirt.virDomain) -> bool:
        """Attempt to thaw VM filesystems using the QEMU guest agent."""
        try:
            if RICH_AVAILABLE:
                console.print(":fire: Attempting filesystem thaw via QEMU agent...")
            
            response = self.qemu_agent_command(domain, '{"execute": "guest-fsfreeze-thaw"}')
            
            if response is None:
                return False
            elif isinstance(response, dict) and ('return' in response or response == {}):
                if RICH_AVAILABLE:
                    console.print(":white_check_mark: Filesystem thaw successful", style="green")
                return True
            else:
                return False
                
        except AgentCommandError as e:
            if RICH_AVAILABLE:
                console.print(f":warning: Filesystem thaw failed: {e}", style="yellow")
            return False

    # --- Network and SSH Functions ---
    def get_vm_ip(self, domain: libvirt.virDomain) -> str:
        """Get the VM IP address using multiple methods."""
        if not domain.isActive():
            raise NetworkError("VM is not running")

        # Try Agent method first
        ip = self._get_vm_ip_address_agent(domain)
        if ip:
            if RICH_AVAILABLE:
                console.print(f":satellite: VM IP obtained via agent: [magenta]{ip}[/]")
            return ip

        # Try DHCP leases method
        ip = self._get_vm_ip_address_dhcp(domain)
        if ip:
            if RICH_AVAILABLE:
                console.print(f":satellite: VM IP obtained via DHCP: [magenta]{ip}[/]")
            return ip

        raise NetworkError("Could not determine VM IP address")

    def _get_vm_ip_address_agent(self, domain: libvirt.virDomain) -> Optional[str]:
        """Get the VM IP address using the QEMU Guest Agent."""
        try:
            # Try interfaceAddresses if available
            if hasattr(domain, 'interfaceAddresses') and hasattr(libvirt, 'VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT'):
                interfaces: Dict[str, Any] = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)  # type: ignore
                for interface, data in interfaces.items():  # type: ignore
                    if interface != 'lo' and data.get('addrs'):  # type: ignore
                        for addr in data['addrs']:  # type: ignore
                            if addr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:  # type: ignore
                                return addr['addr']  # type: ignore

            # Fallback: Try guest-network-get-interfaces command
            response = self.qemu_agent_command(domain, '{"execute": "guest-network-get-interfaces"}')
            if isinstance(response, dict) and "return" in response:
                for interface in response["return"]:  # type: ignore
                    if interface.get("name") != "lo" and "ip-addresses" in interface:  # type: ignore
                        for ip_info in interface["ip-addresses"]:  # type: ignore
                            if ip_info.get("ip-address-type") == "ipv4":  # type: ignore
                                return ip_info.get("ip-address")  # type: ignore

        except Exception as e:
            self.logger.debug(f"Agent IP lookup failed: {e}")

        return None

    def _get_vm_ip_address_dhcp(self, domain: libvirt.virDomain) -> Optional[str]:
        """Get the VM IP address via Libvirt DHCP leases."""
        try:
            conn = self.connect_libvirt()
            vm_mac = None
            network_name = None

            # Get VM's MAC address from XML
            xml_desc: str = domain.XMLDesc(0)  # type: ignore
            root = ET.fromstring(xml_desc)  # type: ignore
            
            # Find interface with source network
            for interface in root.findall(".//interface[@type='network']"):
                source = interface.find("source")
                mac = interface.find("mac")
                if source is not None and mac is not None:
                    network_name = source.get("network")
                    vm_mac = mac.get("address")
                    break

            if not vm_mac or not network_name:
                return None

            # Get DHCP leases for the network
            network = conn.networkLookupByName(network_name)  # type: ignore
            leases = network.DHCPLeases()  # type: ignore
            
            for lease in leases:  # type: ignore
                if lease['mac'].lower() == vm_mac.lower():  # type: ignore
                    return lease['ipaddr']  # type: ignore

        except Exception as e:
            self.logger.debug(f"DHCP IP lookup failed: {e}")

        return None

    def run_ssh_command(self, ip_address: str, user: str, key_path: Path, command: str, 
                       timeout: int = Config.SSH_COMMAND_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """Execute a command via SSH and return results."""
        if not ip_address:
            raise SSHCommandError("No IP address provided")

        # Validate SSH key
        key_path = key_path.expanduser().resolve()
        if not key_path.is_file():
            raise SSHCommandError(f"SSH key not found: {key_path}")

        # Check permissions
        try:
            stat_info = key_path.stat()
            if stat_info.st_mode & Config.SSH_KEY_PERMISSIONS_MASK:
                self.logger.warning(f"SSH key {key_path} has overly permissive permissions")
        except OSError as e:
            raise SSHCommandError(f"Cannot check SSH key permissions: {e}")

        result: Dict[str, Any] = {'stdout': '', 'stderr': '', 'exit_status': None, 'error': None}
        ssh_client = None

        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh_client.connect(
                hostname=ip_address,
                username=user,
                key_filename=str(key_path),
                timeout=Config.SSH_CONNECT_TIMEOUT_SECONDS,
                banner_timeout=30
            )

            _, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
            
            result['stdout'] = stdout.read().decode('utf-8', errors='replace')
            result['stderr'] = stderr.read().decode('utf-8', errors='replace')
            result['exit_status'] = stdout.channel.recv_exit_status()

        except paramiko.AuthenticationException as e:
            result['error'] = f"SSH authentication failed: {e}"
        except (paramiko.SSHException, socket.timeout, ConnectionRefusedError, OSError) as e:
            result['error'] = f"SSH connection error: {e}"
        except Exception as e:
            result['error'] = f"Unexpected SSH error: {e}"
        finally:
            if ssh_client:
                ssh_client.close()

        return result

    def run_interactive_ssh_command(self, ip_address: str, user: str, key_path: Path, 
                                   command: str, timeout: int = Config.SSH_COMMAND_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """
        Execute an interactive command via SSH with TTY allocation.
        
        This method enables proper execution of interactive programs like vim, nano, htop.
        
        Args:
            ip_address: Target IP address
            user: SSH username
            key_path: Path to SSH private key
            command: Interactive command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Dict containing stdout, stderr, exit_status, and error info
        """
        from .ssh_manager import SSHManager
        
        ssh_manager = SSHManager(debug=self.debug)
        return ssh_manager.run_interactive_ssh_command(
            host=ip_address,
            username=user,
            key_path=key_path,
            command=command,
            timeout=timeout,
            verbose=self.debug
        )

    def wait_for_vm_ready(self, vm_name: str, user: str = Config.DEFAULT_SSH_USER, 
                         key_path: Path = Config.DEFAULT_SSH_KEY_PATH,
                         timeout: int = Config.VM_READINESS_TIMEOUT_SECONDS) -> str:
        """Wait for the VM to become accessible via SSH."""
        domain = self.find_vm(vm_name)
        
        if RICH_AVAILABLE:
            console.print(f":hourglass_flowing_sand: Waiting for VM '{vm_name}' to become SSH-ready...")

        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                if not domain.isActive():
                    raise NetworkError(f"VM '{vm_name}' is not running")
                
                ip_address = self.get_vm_ip(domain)
                
                # Test SSH connectivity
                result = self.run_ssh_command(ip_address, user, key_path, "echo 'ready'", timeout=5)
                
                if result.get('exit_status') == 0 and 'ready' in result.get('stdout', ''):
                    if RICH_AVAILABLE:
                        console.print(f":white_check_mark: VM '{vm_name}' is SSH-ready at {ip_address}", style="green")
                    return ip_address
                    
            except Exception as e:
                self.logger.debug(f"VM readiness check failed: {e}")
            
            time.sleep(Config.VM_READINESS_POLL_INTERVAL_SECONDS)

        raise NetworkError(f"VM '{vm_name}' did not become SSH-ready within {timeout} seconds")

    # --- Challenge Management Functions ---
    def load_challenge(self, challenge_file: Path) -> Dict[str, Any]:
        """Load and validate a challenge definition from YAML file."""
        if not challenge_file.exists():
            raise ChallengeLoadError(f"Challenge file not found: {challenge_file}")

        try:
            with open(challenge_file, 'r', encoding='utf-8') as f:
                challenge_data = yaml.safe_load(f)
            
            # Basic validation
            required_fields = ['name', 'description', 'tasks']
            missing_fields = [field for field in required_fields if field not in challenge_data]
            
            if missing_fields:
                raise ChallengeLoadError(f"Missing required fields in challenge: {missing_fields}")
            
            # Set defaults
            challenge_data.setdefault('score', Config.DEFAULT_CHALLENGE_SCORE)
            challenge_data.setdefault('timeout', 300)  # 5 minutes default
            
            self.logger.info(f"Loaded challenge: {challenge_data['name']}")
            return challenge_data
            
        except yaml.YAMLError as e:
            raise ChallengeLoadError(f"Invalid YAML in challenge file: {e}")
        except Exception as e:
            raise ChallengeLoadError(f"Error loading challenge file: {e}")

    def execute_challenge(self, vm_name: str, challenge_data: Dict[str, Any],
                         user: str = Config.DEFAULT_SSH_USER,
                         key_path: Path = Config.DEFAULT_SSH_KEY_PATH) -> Dict[str, Any]:
        """Execute a challenge on the specified VM."""
        if RICH_AVAILABLE:
            console.print(f":rocket: Executing challenge: {challenge_data['name']}")
        
        # Ensure VM is running and ready
        ip_address = self.wait_for_vm_ready(vm_name, user, key_path)
        
        results: Dict[str, Any] = {
            'challenge_name': challenge_data['name'],
            'vm_name': vm_name,
            'ip_address': ip_address,
            'tasks_completed': 0,
            'total_tasks': len(challenge_data['tasks']),
            'score': 0,
            'max_score': challenge_data.get('score', Config.DEFAULT_CHALLENGE_SCORE),
            'task_results': [],
            'success': False,
            'error': None
        }
        
        try:
            # Execute each task in the challenge
            for i, task in enumerate(challenge_data['tasks'], 1):
                if RICH_AVAILABLE:
                    console.print(f":gear: Executing task {i}/{len(challenge_data['tasks'])}: {task.get('name', f'Task {i}')}")
                
                task_result = self._execute_challenge_task(ip_address, task, user, key_path)
                results['task_results'].append(task_result)
                
                if task_result['success']:
                    results['tasks_completed'] += 1
                    results['score'] += task_result.get('score', 0)
                    
                    if RICH_AVAILABLE:
                        console.print(f":white_check_mark: Task {i} completed successfully", style="green")
                else:
                    if RICH_AVAILABLE:
                        console.print(f":x: Task {i} failed: {task_result.get('error', 'Unknown error')}", style="red")
                    
                    # Stop on first failure if specified
                    if task.get('stop_on_failure', False):
                        break
            
            # Calculate final success
            results['success'] = results['tasks_completed'] == results['total_tasks']
            
            if RICH_AVAILABLE:
                if results['success']:
                    console.print(f":trophy: Challenge completed! Score: {results['score']}/{results['max_score']}", style="green")
                else:
                    console.print(f":warning: Challenge incomplete. Tasks completed: {results['tasks_completed']}/{results['total_tasks']}", style="yellow")
                    
        except Exception as e:
            results['error'] = str(e)
            results['success'] = False
            if RICH_AVAILABLE:
                console.print(f":x: Challenge execution failed: {e}", style="red")
        
        return results

    def _execute_challenge_task(self, ip_address: str, task: Dict[str, Any],
                               user: str, key_path: Path) -> Dict[str, Any]:
        """Execute a single challenge task."""
        task_result: Dict[str, Any] = {
            'name': task.get('name', 'Unnamed Task'),
            'type': task.get('type', 'command'),
            'success': False,
            'score': 0,
            'error': None,
            'output': None
        }
        
        try:
            task_type = task.get('type', 'command')
            
            if task_type == 'command':
                # Execute a single command
                command = task.get('command')
                if not command:
                    raise ChallengeValidationError(['Task missing required "command" field'])
                
                result = self.run_ssh_command(ip_address, user, key_path, command, 
                                            timeout=task.get('timeout', Config.SSH_COMMAND_TIMEOUT_SECONDS))
                
                task_result['output'] = result
                
                # Check success criteria
                expected_exit_code = task.get('expected_exit_code', 0)
                if result.get('exit_status') == expected_exit_code:
                    # Additional validation if specified
                    if self._validate_task_output(task, result):
                        task_result['success'] = True
                        task_result['score'] = task.get('score', Config.DEFAULT_CHALLENGE_SCORE // 10)
                    else:
                        task_result['error'] = "Output validation failed"
                else:
                    task_result['error'] = f"Expected exit code {expected_exit_code}, got {result.get('exit_status')}"
            
            elif task_type == 'file_check':
                # Check if a file exists and optionally verify its content
                file_path = task.get('file_path')
                if not file_path:
                    raise ChallengeValidationError(['File check task missing required "file_path" field'])
                
                # Check file existence
                result = self.run_ssh_command(ip_address, user, key_path, f"test -f {file_path}")
                
                if result.get('exit_status') == 0:
                    # File exists, check content if specified
                    if 'expected_content' in task:
                        content_result = self.run_ssh_command(ip_address, user, key_path, f"cat {file_path}")
                        if task['expected_content'] in content_result.get('stdout', ''):
                            task_result['success'] = True
                            task_result['score'] = task.get('score', Config.DEFAULT_CHALLENGE_SCORE // 10)
                        else:
                            task_result['error'] = "File content does not match expected"
                    else:
                        task_result['success'] = True
                        task_result['score'] = task.get('score', Config.DEFAULT_CHALLENGE_SCORE // 10)
                else:
                    task_result['error'] = f"File {file_path} does not exist"
                
                task_result['output'] = result
            
            elif task_type == 'service_check':
                # Check if a service is running
                service_name = task.get('service_name')
                if not service_name:
                    raise ChallengeValidationError(['Service check task missing required "service_name" field'])
                
                result = self.run_ssh_command(ip_address, user, key_path, 
                                            f"systemctl is-active {service_name}")
                
                expected_state = task.get('expected_state', 'active')
                if expected_state in result.get('stdout', ''):
                    task_result['success'] = True
                    task_result['score'] = task.get('score', Config.DEFAULT_CHALLENGE_SCORE // 10)
                else:
                    task_result['error'] = f"Service {service_name} is not in expected state: {expected_state}"
                
                task_result['output'] = result
            
            else:
                raise ChallengeValidationError([f'Unsupported task type: {task_type}'])
                
        except Exception as e:
            task_result['error'] = str(e)
            task_result['success'] = False
        
        return task_result

    def _validate_task_output(self, task: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Validate task output against specified criteria."""
        # Check stdout contains expected text
        if 'expected_stdout' in task:
            if task['expected_stdout'] not in result.get('stdout', ''):
                return False
        
        # Check stderr contains expected text
        if 'expected_stderr' in task:
            if task['expected_stderr'] not in result.get('stderr', ''):
                return False
        
        # Check stdout does not contain forbidden text
        if 'forbidden_stdout' in task:
            if task['forbidden_stdout'] in result.get('stdout', ''):
                return False
        
        # Check stderr does not contain forbidden text
        if 'forbidden_stderr' in task:
            if task['forbidden_stderr'] in result.get('stderr', ''):
                return False
        
        return True

    # --- Snapshot Management Functions ---
    def create_snapshot(self, vm_name: str, snapshot_name: str = Config.DEFAULT_SNAPSHOT_NAME,
                       description: str = "Practice session snapshot") -> bool:
        """Create an external snapshot of the VM."""
        domain = self.find_vm(vm_name)
        
        if RICH_AVAILABLE:
            console.print(f":camera: Creating snapshot '{snapshot_name}' for VM '{vm_name}'...")
        
        try:
            # Attempt filesystem freeze if VM is running
            freeze_successful = False
            if domain.isActive():
                freeze_successful = self.qemu_agent_fsfreeze(domain)
            
            # Create external snapshot XML
            snapshot_xml = f"""
            <domainsnapshot>
                <name>{snapshot_name}</name>
                <description>{description}</description>
                <disks>
                    <disk name='vda' snapshot='external'>
                        <source file='/var/lib/libvirt/images/{vm_name}_{snapshot_name}.qcow2'/>
                    </disk>
                </disks>
            </domainsnapshot>
            """
            
            # Create the snapshot
            snapshot = domain.snapshotCreateXML(snapshot_xml,   # type: ignore
                libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY |
                libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_ATOMIC)
            
            if RICH_AVAILABLE:
                console.print(f":white_check_mark: Snapshot '{snapshot_name}' created successfully", style="green")
            
            # Thaw filesystem if we froze it
            if freeze_successful:
                self.qemu_agent_fsthaw(domain)
            
            self.logger.info(f"Created snapshot '{snapshot_name}' for VM '{vm_name}'")
            return True
            
        except libvirt.libvirtError as e:
            error_msg = f"Failed to create snapshot '{snapshot_name}': {e}"
            self.logger.error(error_msg)
            if RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
            
            # Ensure filesystem is thawed on error
            if domain.isActive():
                try:
                    self.qemu_agent_fsthaw(domain)
                except:
                    pass
            
            raise SnapshotOperationError(error_msg)

    def list_snapshots(self, vm_name: str) -> List[Dict[str, Any]]:
        """List all snapshots for the specified VM."""
        domain = self.find_vm(vm_name)
        snapshots: List[Dict[str, Any]] = []
        
        try:
            snapshot_names = domain.listAllSnapshots()
            
            for snapshot in snapshot_names:
                snapshot_info: Dict[str, Any] = {
                    'name': snapshot.getName(),
                    'creation_time': snapshot.getXMLDesc(),  # Would need parsing for actual time
                    'state': 'disk-snapshot' if snapshot.isCurrent() else 'available'
                }
                snapshots.append(snapshot_info)
                
        except libvirt.libvirtError as e:
            self.logger.error(f"Error listing snapshots for VM '{vm_name}': {e}")
            raise SnapshotOperationError(f"Failed to list snapshots: {e}")
        
        return snapshots

    def revert_to_snapshot(self, vm_name: str, snapshot_name: str) -> bool:
        """Revert VM to the specified snapshot."""
        domain = self.find_vm(vm_name)
        
        if RICH_AVAILABLE:
            console.print(f":rewind: Reverting VM '{vm_name}' to snapshot '{snapshot_name}'...")
        
        try:
            # Find the snapshot
            snapshot = domain.snapshotLookupByName(snapshot_name)  # type: ignore
            
            # Revert to snapshot
            domain.revertToSnapshot(snapshot)  # type: ignore
            
            if RICH_AVAILABLE:
                console.print(f":white_check_mark: Successfully reverted to snapshot '{snapshot_name}'", style="green")
            
            self.logger.info(f"Reverted VM '{vm_name}' to snapshot '{snapshot_name}'")
            return True
            
        except libvirt.libvirtError as e:
            if e.get_error_code() == VIR_ERR_NO_DOMAIN_SNAPSHOT:
                error_msg = f"Snapshot '{snapshot_name}' not found for VM '{vm_name}'"
            else:
                error_msg = f"Failed to revert to snapshot '{snapshot_name}': {e}"
                
            self.logger.error(error_msg)
            if RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
            
            raise SnapshotOperationError(error_msg)

    def delete_snapshot(self, vm_name: str, snapshot_name: str) -> bool:
        """Delete the specified snapshot."""
        domain = self.find_vm(vm_name)
        
        if RICH_AVAILABLE:
            console.print(f":wastebasket: Deleting snapshot '{snapshot_name}' for VM '{vm_name}'...")
        
        try:
            # Find the snapshot
            snapshot = domain.snapshotLookupByName(snapshot_name)  # type: ignore
            
            # Delete the snapshot
            snapshot.delete(libvirt.VIR_DOMAIN_SNAPSHOT_DELETE_METADATA_ONLY)
            
            if RICH_AVAILABLE:
                console.print(f":white_check_mark: Snapshot '{snapshot_name}' deleted successfully", style="green")
            
            self.logger.info(f"Deleted snapshot '{snapshot_name}' for VM '{vm_name}'")
            return True
            
        except libvirt.libvirtError as e:
            if e.get_error_code() == VIR_ERR_NO_DOMAIN_SNAPSHOT:
                error_msg = f"Snapshot '{snapshot_name}' not found for VM '{vm_name}'"
            else:
                error_msg = f"Failed to delete snapshot '{snapshot_name}': {e}"
                
            self.logger.error(error_msg)
            if RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
            
            raise SnapshotOperationError(error_msg)

    # --- VM Creation Methods ---
    def create_vm(self, vm_name: str, memory_gb: int = 2, cpus: int = 1, disk_gb: int = 20, iso_path: Optional[str] = None) -> bool:
        """Create a new VM with basic configuration and optional ISO attachment."""
        try:
            conn = self.connect_libvirt()
            
            # Check if VM already exists
            try:
                existing = conn.lookupByName(vm_name)  # type: ignore
                if existing:
                    raise PracticeToolError(f"VM '{vm_name}' already exists")
            except libvirt.libvirtError as e:
                if e.get_error_code() != VIR_ERR_NO_DOMAIN:
                    raise
            
            # Generate MAC address based on VM name
            import hashlib
            hash_obj = hashlib.md5(vm_name.encode())
            mac_suffix = hash_obj.hexdigest()[:6]
            mac_address = f"52:54:00:{mac_suffix[:2]}:{mac_suffix[2:4]}:{mac_suffix[4:6]}"
            
            memory_kb = memory_gb * 1024 * 1024
            
            # Use user-accessible directory for VM disk images
            import os
            vm_storage_dir = os.path.expanduser('~/vm-storage')
            os.makedirs(vm_storage_dir, exist_ok=True)
            disk_path = f'{vm_storage_dir}/{vm_name}.qcow2'
            
            # Basic Ubuntu VM XML template
            vm_xml = f"""<domain type='qemu'>
  <name>{vm_name}</name>
  <memory unit='KiB'>{memory_kb}</memory>
  <currentMemory unit='KiB'>{memory_kb}</currentMemory>
  <vcpu placement='static'>{cpus}</vcpu>
  <os>
    <type arch='x86_64' machine='pc-q35-noble'>hvm</type>
    <boot dev='hd'/>
    <boot dev='cdrom'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <vmport state='off'/>
  </features>
  <cpu mode='host-model' check='partial'/>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{disk_path}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <interface type='network'>
      <mac address='{mac_address}'/>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <serial type='pty'>
      <target type='isa-serial' port='0'>
        <model name='isa-serial'/>
      </target>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <controller type='sata' index='0'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x1f' function='0x2'/>
    </controller>
    <channel type='unix'>
      <target type='virtio' name='org.qemu.guest_agent.0'/>
    </channel>
    <input type='tablet' bus='usb'/>
    <input type='mouse' bus='ps2'/>
    <input type='keyboard' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes' listen='127.0.0.1'>
      <listen type='address' address='127.0.0.1'/>
    </graphics>
    <video>
      <model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1' primary='yes'/>
    </video>
    <memballoon model='virtio'/>
    <rng model='virtio'>
      <backend model='random'>/dev/urandom</backend>
    </rng>
  </devices>
</domain>"""
            
            # Create the disk image in user directory
            try:
                # Create qcow2 disk image
                create_disk_cmd = [
                    'qemu-img', 'create', '-f', 'qcow2', 
                    disk_path, f'{disk_gb}G'
                ]
                subprocess.run(create_disk_cmd, capture_output=True, text=True, check=True)
                self.logger.info(f"Created disk image: {disk_path}")
                
                # Make sure the file has proper permissions for libvirt access
                try:
                    os.chmod(disk_path, 0o644)
                except OSError as e:
                    self.logger.warning(f"Could not set disk permissions: {e}")
                    
            except subprocess.CalledProcessError as e:
                error_msg = f"Failed to create disk image: {e.stderr or str(e)}"
                self.logger.error(error_msg)
                raise PracticeToolError(error_msg)
            
            # Define the VM in libvirt
            try:
                conn.defineXML(vm_xml)  # type: ignore
                
                # Attach ISO if provided
                if iso_path and os.path.exists(iso_path):
                    try:
                        # Get the newly created domain
                        domain = conn.lookupByName(vm_name)  # type: ignore
                        
                        # Create CDROM device XML
                        cdrom_xml = f"""<disk type='file' device='cdrom'>
  <driver name='qemu' type='raw'/>
  <source file='{iso_path}'/>
  <target dev='sda' bus='sata'/>
  <readonly/>
</disk>"""
                        
                        # Attach the CDROM device
                        domain.attachDeviceFlags(cdrom_xml, libvirt.VIR_DOMAIN_AFFECT_CONFIG)  # type: ignore
                        self.logger.info(f"Attached ISO {iso_path} to VM '{vm_name}'")
                        
                    except Exception as iso_error:
                        # Don't fail VM creation if ISO attachment fails
                        self.logger.warning(f"Failed to attach ISO to VM {vm_name}: {iso_error}")
                
                if RICH_AVAILABLE:
                    console.print(f":white_check_mark: VM '{vm_name}' created successfully", style="green")
                
                iso_msg = f" with ISO {iso_path}" if iso_path else ""
                self.logger.info(f"Created VM '{vm_name}' with {memory_gb}GB RAM, {cpus} CPU(s), {disk_gb}GB disk{iso_msg}")
                return True
                
            except libvirt.libvirtError as e:
                # Clean up disk if VM definition failed
                try:
                    os.remove(disk_path)
                except OSError:
                    pass
                
                error_msg = f"Failed to define VM: {str(e)}"
                self.logger.error(error_msg)
                raise PracticeToolError(error_msg)
                
        except libvirt.libvirtError as e:
            error_msg = f"Libvirt error creating VM '{vm_name}': {e}"
            self.logger.error(error_msg)
            if RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
            raise PracticeToolError(error_msg)

    # --- Cleanup ---
    def cleanup(self):
        """Clean up connections properly"""
        try:
            if hasattr(self, '_conn') and self._conn is not None:
                try:
                    self._conn.close()
                except Exception as e:
                    self.logger.warning(f"Error closing libvirt connection: {e}")
                finally:
                    self._conn = None
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    def delete_vm(self, vm_name: str, remove_disk: bool = True) -> bool:
        """Delete a VM and optionally remove its disk file."""
        try:
            conn = self.connect_libvirt()
            
            # Find the VM
            try:
                domain = conn.lookupByName(vm_name)  # type: ignore
            except libvirt.libvirtError:
                self.logger.error(f"VM '{vm_name}' not found")
                return False
            
            # Get disk path before destroying
            disk_path = None
            if remove_disk:
                try:
                    # Get the VM XML to find disk path
                    vm_xml: str = domain.XMLDesc(0)  # type: ignore
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(vm_xml)  # type: ignore
                    for disk in root.findall('.//disk[@device="disk"]'):
                        source = disk.find('source')
                        if source is not None and 'file' in source.attrib:
                            disk_path = source.attrib['file']
                            break
                except Exception as e:
                    self.logger.warning(f"Could not get disk path for {vm_name}: {e}")
            
            # Stop the VM if running
            try:
                if domain.isActive():
                    domain.destroy()  # Force stop
                    self.logger.info(f"Stopped VM '{vm_name}'")
            except Exception as e:
                self.logger.warning(f"Could not stop VM {vm_name}: {e}")
            
            # Undefine (delete) the VM
            try:
                domain.undefine()
                self.logger.info(f"Deleted VM '{vm_name}' from libvirt")
            except Exception as e:
                self.logger.error(f"Failed to delete VM {vm_name}: {e}")
                return False
            
            # Remove disk file if requested and found
            if remove_disk and disk_path and os.path.exists(disk_path):
                try:
                    os.remove(disk_path)
                    self.logger.info(f"Removed disk file: {disk_path}")
                except Exception as e:
                    self.logger.warning(f"Could not remove disk file {disk_path}: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting VM {vm_name}: {e}")
            return False
            
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during destruction
