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
import re
import socket
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, cast

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
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.syntax import Syntax
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Provide dummy classes if rich is not available
    class Console:
        def print(self, *args, **kwargs): print(*args)
    class Panel:
        def __init__(self, *args, **kwargs): pass
    class Table:
        def __init__(self, *args, **kwargs): pass
        def add_column(self, *args, **kwargs): pass
        def add_row(self, *args, **kwargs): pass
    class Text:
        def __init__(self, *args, **kwargs): pass

# Initialize Rich Console
console = Console(highlight=False, stderr=False)

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
    def __init__(self, reasons: list):
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
    DEFAULT_SSH_USER: str = "root"  # Update if needed
    DEFAULT_SSH_KEY_PATH: Path = Path("~/.ssh/id_ed25519").expanduser()  # Update if needed
    SSH_CONNECT_TIMEOUT_SECONDS: int = 10
    SSH_COMMAND_TIMEOUT_SECONDS: int = 30
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
            
            self.conn = libvirt.open(Config.LIBVIRT_URI)
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
            domain = conn.lookupByName(vm_name)
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
        vms = []

        try:
            # Get all domains (defined and running)
            all_domains = conn.listAllDomains()
            
            for domain in all_domains:
                vm_info = {
                    'name': domain.name(),
                    'state': 'running' if domain.isActive() else 'stopped',
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
            response = domain.qemuAgentCommand(command_json_str, timeout_sec, 0)
            if response:
                return json.loads(response)
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
                interfaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)
                for interface, data in interfaces.items():
                    if interface != 'lo' and data.get('addrs'):
                        for addr in data['addrs']:
                            if addr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                                return addr['addr']

            # Fallback: Try guest-network-get-interfaces command
            response = self.qemu_agent_command(domain, '{"execute": "guest-network-get-interfaces"}')
            if isinstance(response, dict) and "return" in response:
                for interface in response["return"]:
                    if interface.get("name") != "lo" and "ip-addresses" in interface:
                        for ip_info in interface["ip-addresses"]:
                            if ip_info.get("ip-address-type") == "ipv4":
                                return ip_info.get("ip-address")

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
            xml_desc = domain.XMLDesc(0)
            root = ET.fromstring(xml_desc)
            
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
            network = conn.networkLookupByName(network_name)
            leases = network.DHCPLeases()
            
            for lease in leases:
                if lease['mac'].lower() == vm_mac.lower():
                    return lease['ipaddr']

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

        result = {'stdout': '', 'stderr': '', 'exit_status': None, 'error': None}
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

            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
            
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
        
        results = {
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
        task_result = {
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
            snapshot = domain.snapshotCreateXML(snapshot_xml, 
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
        snapshots = []
        
        try:
            snapshot_names = domain.listAllSnapshots()
            
            for snapshot in snapshot_names:
                snapshot_info = {
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
            snapshot = domain.snapshotLookupByName(snapshot_name)
            
            # Revert to snapshot
            domain.revertToSnapshot(snapshot)
            
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
            snapshot = domain.snapshotLookupByName(snapshot_name)
            
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

    # --- Cleanup ---
    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close_libvirt()

    def __del__(self):
        """Destructor with cleanup."""
        self.close_libvirt()
