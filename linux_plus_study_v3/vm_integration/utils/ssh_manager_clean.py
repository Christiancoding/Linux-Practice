#!/usr/bin/env python3
"""
SSH Management Utility

Comprehensive SSH connection and command execution management for VM operations.
Provides secure SSH connectivity with key-based authentication and robust error handling.
"""

import sys
import time
import socket
import logging
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import stat

# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("SSH Manager requires Python 3.8+. Please upgrade.")
    sys.exit(1)

try:
    import paramiko  # type: ignore
except ImportError:
    print("Error: Missing required library 'paramiko'.",
          "Please install it (e.g., 'pip install paramiko') and try again.",
          file=sys.stderr)
    sys.exit(1)

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

from .exceptions import SSHCommandError, NetworkError

class SSHManager:
    """
    SSH connection and command execution manager.
    
    Provides secure SSH connectivity with comprehensive error handling,
    key validation, and command execution capabilities.
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize SSH Manager.
        
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

    def run_ssh_command(self, host: str, username: str, key_path: Path, 
                       command: str, timeout: int = 30, verbose: bool = False,
                       stdin_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a command via SSH and return comprehensive results.
        
        Args:
            host: Target hostname or IP address
            username: SSH username
            key_path: Path to SSH private key
            command: Command to execute
            timeout: Command timeout in seconds
            verbose: Enable verbose output
            stdin_data: Optional data to send to stdin
            
        Returns:
            Dictionary containing:
            - stdout: Command output
            - stderr: Error output  
            - exit_status: Exit code
            - error: Error message if connection/execution failed
            
        Raises:
            SSHCommandError: If SSH operations fail
        """
        if not host:
            raise SSHCommandError("No host provided")
        
        if not command:
            raise SSHCommandError("No command provided")

        # Validate SSH key
        key_path = self._validate_ssh_key(key_path)
        
        result: Dict[str, Any] = {'stdout': '', 'stderr': '', 'exit_status': None, 'error': None}
        ssh_client = None

        try:
            if verbose and _rich_available:
                console.print(f"🛰️ Connecting to {username}@{host}...")

            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to the host
            ssh_client.connect(
                hostname=host,
                username=username,
                key_filename=str(key_path),
                timeout=10,  # Connection timeout
                banner_timeout=30,
                auth_timeout=10
            )

            if verbose and _rich_available:
                console.print(f"🚀 Executing command: {command}")

            # Execute command
            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
            
            # Send stdin data if provided
            if stdin_data:
                stdin.write(stdin_data)
                stdin.flush()
            
            # Read outputs
            result['stdout'] = stdout.read().decode('utf-8', errors='replace')
            result['stderr'] = stderr.read().decode('utf-8', errors='replace')
            result['exit_status'] = stdout.channel.recv_exit_status()

            if verbose:
                if result['exit_status'] == 0:
                    if _rich_available:
                        console.print("✅ Command executed successfully")
                    else:
                        print("✅ Command executed successfully")
                else:
                    msg = f"❌ Command failed with exit code {result['exit_status']}"
                    if _rich_available:
                        console.print(msg)
                    else:
                        print(msg)

        except paramiko.AuthenticationException as e:
            error_msg = f"SSH authentication failed for {username}@{host}: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            if verbose:
                msg = f"❌ {error_msg}"
                if _rich_available:
                    console.print(msg)
                else:
                    print(msg)
            
        except (paramiko.SSHException, socket.timeout, ConnectionRefusedError, OSError) as e:
            error_msg = f"SSH connection error to {host}: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            if verbose:
                msg = f"❌ {error_msg}"
                if _rich_available:
                    console.print(msg)
                else:
                    print(msg)
            
        except Exception as e:
            error_msg = f"Unexpected SSH error: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            if verbose:
                msg = f"❌ {error_msg}"
                if _rich_available:
                    console.print(msg)
                else:
                    print(msg)
            
        finally:
            if ssh_client:
                try:
                    ssh_client.close()
                except Exception as e:
                    self.logger.warning(f"Error closing SSH connection: {e}")

        return result

    def test_ssh_connectivity(self, host: str, username: str, key_path: Path, 
                             timeout: int = 10) -> bool:
        """
        Test SSH connectivity to a host.
        
        Args:
            host: Target hostname or IP address
            username: SSH username
            key_path: Path to SSH private key
            timeout: Connection timeout in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = self.run_ssh_command(host, username, key_path, "echo 'test'", timeout)
            return result.get('exit_status') == 0 and result.get('error') is None
        except Exception as e:
            self.logger.debug(f"SSH connectivity test failed: {e}")
            return False

    def wait_for_ssh_ready(self, host: str, username: str, key_path: Path,
                          timeout: int = 120, poll_interval: int = 5) -> bool:
        """
        Wait for SSH to become available on a host.
        
        Args:
            host: Target hostname or IP address
            username: SSH username
            key_path: Path to SSH private key
            timeout: Total timeout in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            True if SSH becomes ready, False if timeout reached
        """
        msg = f"⏳ Waiting for SSH connectivity to {host}..."
        if _rich_available:
            console.print(msg)
        else:
            print(msg)

        start_time = time.time()
        last_error = "Timeout"

        while (time.time() - start_time) < timeout:
            try:
                if self.test_ssh_connectivity(host, username, key_path, timeout=5):
                    msg = f"✅ SSH ready at {host}"
                    if _rich_available:
                        console.print(msg)
                    else:
                        print(msg)
                    return True
                    
            except Exception as e:
                last_error = str(e)
                self.logger.debug(f"SSH readiness check failed: {e}")
            
            time.sleep(poll_interval)

        msg = f"❌ SSH did not become ready at {host} within {timeout} seconds"
        if _rich_available:
            console.print(msg)
            console.print(f"Last error: {last_error}")
        else:
            print(msg)
            print(f"Last error: {last_error}")
        
        return False

    def copy_file_to_remote(self, host: str, username: str, key_path: Path,
                           local_path: Path, remote_path: str,
                           create_dirs: bool = True) -> bool:
        """
        Copy a file to a remote host via SFTP.
        
        Args:
            host: Target hostname or IP address
            username: SSH username
            key_path: Path to SSH private key
            local_path: Local file path
            remote_path: Remote file path
            create_dirs: Create remote directories if they don't exist
            
        Returns:
            True if copy successful, False otherwise
        """
        key_path = self._validate_ssh_key(key_path)
        
        if not local_path.exists():
            raise SSHCommandError(f"Local file does not exist: {local_path}")

        ssh_client = None
        sftp_client = None
        
        try:
            msg = f"📁 Copying {local_path} to {username}@{host}:{remote_path}"
            if _rich_available:
                console.print(msg)
            else:
                print(msg)

            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh_client.connect(
                hostname=host,
                username=username,
                key_filename=str(key_path),
                timeout=10
            )

            sftp_client = ssh_client.open_sftp()
            
            # Create remote directories if requested
            if create_dirs:
                remote_dir = str(Path(remote_path).parent)
                try:
                    self._create_remote_directories(sftp_client, remote_dir)
                except Exception as e:
                    self.logger.warning(f"Could not create remote directories: {e}")

            # Copy the file
            sftp_client.put(str(local_path), remote_path)
            
            msg = "✅ File copied successfully"
            if _rich_available:
                console.print(msg)
            else:
                print(msg)
            
            return True

        except Exception as e:
            error_msg = f"Failed to copy file: {e}"
            self.logger.error(error_msg)
            msg = f"❌ {error_msg}"
            if _rich_available:
                console.print(msg)
            else:
                print(msg)
            return False
            
        finally:
            if sftp_client:
                sftp_client.close()
            if ssh_client:
                ssh_client.close()

    def _validate_ssh_key(self, key_path: Path) -> Path:
        """Validate SSH private key existence and permissions."""
        resolved_path = key_path.expanduser().resolve()
        
        if not resolved_path.is_file():
            raise SSHCommandError(f"SSH key not found: {resolved_path}")

        # Check permissions (basic check: should not be world/group readable/writable)
        try:
            stat_info = resolved_path.stat()
            # Check if permissions are too open (readable by group/others)
            if stat_info.st_mode & 0o077:
                self.logger.warning(f"SSH key {resolved_path} has overly permissive permissions")
                # Optionally fix permissions
                try:
                    resolved_path.chmod(0o600)
                    self.logger.info(f"Fixed SSH key permissions for {resolved_path}")
                except OSError as e:
                    self.logger.warning(f"Could not fix SSH key permissions: {e}")
        except OSError as e:
            raise SSHCommandError(f"Cannot check SSH key permissions: {e}")

        return resolved_path

    def _create_remote_directories(self, sftp_client: Any, remote_path: str) -> None:
        """Recursively create remote directories."""
        dirs_to_create: List[str] = []
        current_path = remote_path
        
        # Walk up the path to find which directories need to be created
        while current_path and current_path != '/':
            try:
                sftp_client.stat(current_path)
                break  # Directory exists
            except FileNotFoundError:
                dirs_to_create.append(current_path)
                current_path = str(Path(current_path).parent)
        
        # Create directories from top to bottom
        for dir_path in reversed(dirs_to_create):
            try:
                sftp_client.mkdir(dir_path)
                self.logger.debug(f"Created remote directory: {dir_path}")
            except Exception as e:
                self.logger.warning(f"Could not create remote directory {dir_path}: {e}")

# Legacy function wrapper for backward compatibility
def run_ssh_command(host: str, username: str, key_path: Path, command: str, 
                   timeout: int = 30, verbose: bool = False) -> Dict[str, Any]:
    """Legacy function - use SSHManager instead."""
    manager = SSHManager()
    return manager.run_ssh_command(host, username, key_path, command, timeout, verbose)
