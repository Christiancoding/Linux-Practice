#!/usr/bin/env python3
"""
SSH Connection and Command Execution Manager

Comprehensive SSH session management with robust error handling,
security validation, and user-friendly output formatting for
remote Linux system administration and practice environments.
"""

import sys
import time
import logging
import socket
import stat
from pathlib import Path
from typing import Dict, Optional, Any, Union, List

# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("SSH Manager requires Python 3.8+. Please upgrade.")
    sys.exit(1)

# Import required SSH library
try:
    import paramiko
except ImportError:
    print("Error: Missing required library 'paramiko'.\n"
          "Please install it (e.g., 'pip install paramiko') and try again.", 
          file=sys.stderr)
    sys.exit(1)

# Import local modules
from .config import SSHConfiguration
from .exceptions import SSHCommandError, NetworkError, format_exception_for_user
from .console_helper import console, Panel, Table, RICH_AVAILABLE


class SSHManager:
    """
    Advanced SSH connection and command execution management system.
    
    Provides secure, reliable SSH operations with comprehensive error handling,
    connection pooling, and detailed output formatting for remote Linux
    system administration tasks.
    """
    
    def __init__(self, default_timeout: int = SSHConfiguration.COMMAND_TIMEOUT_SECONDS):
        """
        Initialize SSH manager with security validation and logging setup.
        
        Args:
            default_timeout: Default command execution timeout in seconds
        """
        self._setup_logging()
        self.default_timeout = default_timeout
        self.active_connections = {}
        self.logger = logging.getLogger(__name__)
        
        # Configure paramiko logging to reduce noise
        paramiko.util.log_to_file('/dev/null')
        logging.getLogger("paramiko").setLevel(logging.WARNING)
    
    def _setup_logging(self) -> None:
        """Configure comprehensive logging infrastructure for SSH operations."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('ssh_manager.log')
            ]
        )
    
    def validate_ssh_key_security(self, key_path: Path) -> bool:
        """
        Validate SSH private key file permissions for security compliance.
        
        Args:
            key_path: Path to SSH private key file
            
        Returns:
            bool: True if key permissions are secure, False otherwise
        """
        try:
            if not key_path.exists():
                self.logger.error(f"SSH key file does not exist: {key_path}")
                return False
            
            # Check file permissions - should be readable only by owner
            file_stat = key_path.stat()
            file_mode = file_stat.st_mode
            permissions = stat.filemode(file_mode)
            
            # Check for group/other read permissions (security risk)
            if file_mode & SSHConfiguration.KEY_PERMISSIONS_MASK:
                self.logger.warning(
                    f"SSH key {key_path} has insecure permissions: {permissions}. "
                    "Key should be readable only by owner (600 or 400)."
                )
                return False
            
            self.logger.debug(f"SSH key {key_path} has secure permissions: {permissions}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating SSH key permissions: {e}")
            return False
    
    def test_connection(self, host: str, username: str, key_path: Path, 
                       port: int = 22, timeout: int = SSHConfiguration.CONNECT_TIMEOUT_SECONDS) -> bool:
        """
        Test SSH connectivity without establishing persistent connection.
        
        Args:
            host: Target hostname or IP address
            username: SSH username for authentication
            key_path: Path to SSH private key
            port: SSH port number (default: 22)
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if connection test succeeds, False otherwise
        """
        try:
            self.logger.debug(f"Testing SSH connection to {username}@{host}:{port}")
            
            # Validate key file security
            if not self.validate_ssh_key_security(key_path):
                return False
            
            # Create temporary SSH client for testing
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddHostKeyPolicy())
            
            try:
                # Attempt connection
                ssh_client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    key_filename=str(key_path),
                    timeout=timeout,
                    banner_timeout=timeout,
                    auth_timeout=timeout
                )
                
                # Quick command test to verify full functionality
                _, stdout, stderr = ssh_client.exec_command('echo "connection_test"', timeout=5)
                output = stdout.read().decode('utf-8').strip()
                
                if output == "connection_test":
                    self.logger.debug(f"SSH connection test successful to {host}")
                    return True
                else:
                    self.logger.warning(f"SSH connection established but command test failed to {host}")
                    return False
                    
            finally:
                ssh_client.close()
                
        except paramiko.AuthenticationException:
            self.logger.debug(f"SSH authentication failed to {host}")
            return False
        except paramiko.SSHException as e:
            self.logger.debug(f"SSH connection error to {host}: {e}")
            return False
        except socket.timeout:
            self.logger.debug(f"SSH connection timeout to {host}")
            return False
        except Exception as e:
            self.logger.debug(f"Unexpected error testing SSH connection to {host}: {e}")
            return False
    
    def run_ssh_command(self, host: str, username: str, key_path: Path, command: str,
                       timeout: Optional[int] = None, verbose: bool = False) -> Dict[str, Any]:
        """
        Execute command via SSH with comprehensive error handling and output capture.
        
        Args:
            host: Target hostname or IP address
            username: SSH username for authentication
            key_path: Path to SSH private key
            command: Command to execute on remote system
            timeout: Command execution timeout (uses default if None)
            verbose: Enable verbose output logging
            
        Returns:
            Dict containing execution results with keys:
            - 'success': bool indicating overall success
            - 'exit_status': int command exit code
            - 'stdout': str standard output
            - 'stderr': str standard error output
            - 'error': Optional[str] error description if command failed
            - 'execution_time': float command execution time in seconds
            
        Raises:
            SSHCommandError: If SSH connection or command execution fails
        """
        effective_timeout = timeout or self.default_timeout
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing SSH command on {host}: {command}")
            
            # Validate SSH key security
            if not self.validate_ssh_key_security(key_path):
                raise SSHCommandError(
                    command=command,
                    ssh_error="SSH key file has insecure permissions or is inaccessible",
                    host=host
                )
            
            # Establish SSH connection
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddHostKeyPolicy())
            
            try:
                # Connect with comprehensive timeout handling
                ssh_client.connect(
                    hostname=host,
                    username=username,
                    key_filename=str(key_path),
                    timeout=SSHConfiguration.CONNECT_TIMEOUT_SECONDS,
                    banner_timeout=SSHConfiguration.CONNECT_TIMEOUT_SECONDS,
                    auth_timeout=SSHConfiguration.CONNECT_TIMEOUT_SECONDS
                )
                
                # Execute command with timeout
                stdin, stdout, stderr = ssh_client.exec_command(command, timeout=effective_timeout)
                
                # Collect output and exit status
                stdout_data = stdout.read().decode('utf-8', errors='replace')
                stderr_data = stderr.read().decode('utf-8', errors='replace')
                exit_status = stdout.channel.recv_exit_status()
                
                execution_time = time.time() - start_time
                
                # Prepare result dictionary
                result = {
                    'success': exit_status == 0,
                    'exit_status': exit_status,
                    'stdout': stdout_data,
                    'stderr': stderr_data,
                    'error': None if exit_status == 0 else f"Command exited with status {exit_status}",
                    'execution_time': execution_time
                }
                
                if verbose:
                    self.logger.info(f"Command completed in {execution_time:.2f}s with exit status {exit_status}")
                    if stdout_data:
                        self.logger.debug(f"STDOUT: {stdout_data[:200]}...")
                    if stderr_data:
                        self.logger.debug(f"STDERR: {stderr_data[:200]}...")
                
                return result
                
            finally:
                ssh_client.close()
                
        except paramiko.AuthenticationException as e:
            execution_time = time.time() - start_time
            error_msg = f"SSH authentication failed for {username}@{host}"
            self.logger.error(error_msg)
            raise SSHCommandError(
                command=command,
                ssh_error=error_msg,
                host=host
            ) from e
            
        except paramiko.SSHException as e:
            execution_time = time.time() - start_time
            error_msg = f"SSH connection error: {e}"
            self.logger.error(error_msg)
            raise SSHCommandError(
                command=command,
                ssh_error=error_msg,
                host=host
            ) from e
            
        except socket.timeout as e:
            execution_time = time.time() - start_time
            error_msg = f"SSH command timeout after {effective_timeout}s"
            self.logger.error(error_msg)
            raise SSHCommandError(
                command=command,
                ssh_error=error_msg,
                host=host
            ) from e
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected SSH error: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise SSHCommandError(
                command=command,
                ssh_error=error_msg,
                host=host
            ) from e
    
    def format_ssh_output(self, result: Dict[str, Any], command: str, 
                         show_command: bool = True) -> str:
        """
        Format SSH command execution results for user-friendly display.
        
        Args:
            result: SSH command execution result dictionary
            command: Original command that was executed
            show_command: Whether to include the command in output
            
        Returns:
            str: Formatted output string for console display
        """
        try:
            # Prepare formatted output sections
            output_sections = []
            
            if show_command:
                if RICH_AVAILABLE:
                    output_sections.append(f"[bold cyan]Command:[/] [dim]{command}[/]")
                else:
                    output_sections.append(f"Command: {command}")
            
            # Format execution status
            exit_status = result.get('exit_status', -1)
            execution_time = result.get('execution_time', 0)
            success = result.get('success', False)
            
            if RICH_AVAILABLE:
                status_color = "green" if success else "red"
                status_text = "SUCCESS" if success else "FAILED"
                status_line = f"[bold {status_color}]Status:[/] {status_text} (exit: {exit_status}, time: {execution_time:.2f}s)"
            else:
                status_text = "SUCCESS" if success else "FAILED"
                status_line = f"Status: {status_text} (exit: {exit_status}, time: {execution_time:.2f}s)"
            
            output_sections.append(status_line)
            
            # Format stdout if present
            stdout = result.get('stdout', '').strip()
            if stdout:
                if RICH_AVAILABLE:
                    output_sections.append(f"[bold green]Output:[/]\n{stdout}")
                else:
                    output_sections.append(f"Output:\n{stdout}")
            
            # Format stderr if present
            stderr = result.get('stderr', '').strip()
            if stderr:
                if RICH_AVAILABLE:
                    output_sections.append(f"[bold red]Error Output:[/]\n{stderr}")
                else:
                    output_sections.append(f"Error Output:\n{stderr}")
            
            # Format SSH-specific errors
            ssh_error = result.get('error')
            if ssh_error and not success:
                if RICH_AVAILABLE:
                    output_sections.append(f"[bold red]Error:[/] {ssh_error}")
                else:
                    output_sections.append(f"Error: {ssh_error}")
            
            return '\n'.join(output_sections)
            
        except Exception as e:
            self.logger.error(f"Error formatting SSH output: {e}")
            return f"Error formatting command output: {e}"
    
    def run_multiple_commands(self, host: str, username: str, key_path: Path,
                            commands: List[str], stop_on_failure: bool = True,
                            verbose: bool = False) -> List[Dict[str, Any]]:
        """
        Execute multiple SSH commands in sequence with failure handling options.
        
        Args:
            host: Target hostname or IP address
            username: SSH username for authentication
            key_path: Path to SSH private key
            commands: List of commands to execute in order
            stop_on_failure: Stop execution if any command fails
            verbose: Enable verbose output logging
            
        Returns:
            List[Dict]: Results for each command execution
            
        Raises:
            SSHCommandError: If any command fails and stop_on_failure is True
        """
        results = []
        
        for i, command in enumerate(commands, 1):
            try:
                if verbose:
                    console.print(f"[cyan]Executing command {i}/{len(commands)}:[/] {command}")
                
                result = self.run_ssh_command(host, username, key_path, command, verbose=verbose)
                results.append(result)
                
                # Check for failure and stop_on_failure setting
                if not result['success'] and stop_on_failure:
                    error_msg = f"Command {i} failed, stopping execution: {command}"
                    self.logger.error(error_msg)
                    raise SSHCommandError(
                        command=command,
                        exit_status=result['exit_status'],
                        stderr=result.get('stderr'),
                        host=host
                    )
                    
            except SSHCommandError:
                if stop_on_failure:
                    raise
                # Add error result and continue
                error_result = {
                    'success': False,
                    'exit_status': -1,
                    'stdout': '',
                    'stderr': f"Command execution failed: {command}",
                    'error': f"SSH execution error for command: {command}",
                    'execution_time': 0.0
                }
                results.append(error_result)
        
        return results


# Convenience functions for backward compatibility with ww.py
def run_ssh_command(host: str, username: str, key_path: Path, command: str,
                   timeout: Optional[int] = None, verbose: bool = False) -> Dict[str, Any]:
    """Backward compatibility function for SSH command execution."""
    manager = SSHManager()
    return manager.run_ssh_command(host, username, key_path, command, timeout, verbose)

def format_ssh_output(result: Dict[str, Any], command: str, show_command: bool = True) -> str:
    """Backward compatibility function for SSH output formatting."""
    manager = SSHManager()
    return manager.format_ssh_output(result, command, show_command)

def wait_for_vm_ready(vm_ip: str, ssh_user: str, ssh_key_path: Path, 
                     timeout: int = SSHConfiguration.CONNECT_TIMEOUT_SECONDS) -> None:
    """
    Backward compatibility function for VM readiness checking.
    
    Note: This function has been moved to vm_manager.py for better organization.
    This is provided for compatibility but should use vm_manager.wait_for_vm_ready().
    """
    manager = SSHManager()
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        if manager.test_connection(vm_ip, ssh_user, ssh_key_path):
            return
        time.sleep(5)
    
    raise NetworkError(f"VM at {vm_ip} did not become ready within {timeout} seconds", host=vm_ip, timeout=timeout)


# Export all public components
__all__ = [
    'SSHManager',
    'run_ssh_command', 'format_ssh_output', 'wait_for_vm_ready'
]