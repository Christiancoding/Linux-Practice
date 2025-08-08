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

import sys
import time
import socket
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import stat

# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("SSH Manager requires Python 3.8+. Please upgrade.")
    sys.exit(1)

try:
    import paramiko  # type: ignore
except ImportError:
    print("Error: Missing required library 'paramiko'.
"
          "Please install it (e.g., 'pip install paramiko') and try again.", 
          file=sys.stderr)
    sys.exit(1)

# Rich console support
try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    class Console:
        def print(self, *args, **kwargs): print(*args)

console = Console()

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
        
        result = {'stdout': '', 'stderr': '', 'exit_status': None, 'error': None}
        ssh_client = None

        try:
            if verbose and RICH_AVAILABLE:
                console.print(f":satellite: Connecting to {username}@{host}...")

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

            if verbose and RICH_AVAILABLE:
                console.print(f":rocket: Executing command: [cyan]{command}[/]")

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

            if verbose and RICH_AVAILABLE:
                if result['exit_status'] == 0:
                    console.print(":white_check_mark: Command executed successfully", style="green")
                else:
                    console.print(f":x: Command failed with exit code {result['exit_status']}", style="red")

        except paramiko.AuthenticationException as e:
            error_msg = f"SSH authentication failed for {username}@{host}: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            if verbose and RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
            
        except (paramiko.SSHException, socket.timeout, ConnectionRefusedError, OSError) as e:
            error_msg = f"SSH connection error to {host}: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            if verbose and RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
            
        except Exception as e:
            error_msg = f"Unexpected SSH error: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
            if verbose and RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
            
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
        if RICH_AVAILABLE:
            console.print(f":hourglass_flowing_sand: Waiting for SSH connectivity to {host}...")

        start_time = time.time()
        last_error = "Timeout"

        while (time.time() - start_time) < timeout:
            try:
                if self.test_ssh_connectivity(host, username, key_path, timeout=5):
                    if RICH_AVAILABLE:
                        console.print(f":white_check_mark: SSH ready at {host}", style="green")
                    return True
                    
            except Exception as e:
                last_error = str(e)
                self.logger.debug(f"SSH readiness check failed: {e}")
            
            time.sleep(poll_interval)

        if RICH_AVAILABLE:
            console.print(f":x: SSH did not become ready at {host} within {timeout} seconds", style="red")
            console.print(f"Last error: {last_error}", style="dim")
        
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
            if RICH_AVAILABLE:
                console.print(f":file_folder: Copying {local_path} to {username}@{host}:{remote_path}")

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
            
            if RICH_AVAILABLE:
                console.print(":white_check_mark: File copied successfully", style="green")
            
            return True

        except Exception as e:
            error_msg = f"Failed to copy file: {e}"
            self.logger.error(error_msg)
            if RICH_AVAILABLE:
                console.print(f":x: {error_msg}", style="red")
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

    def _create_remote_directories(self, sftp_client, remote_path: str):
        """Recursively create remote directories."""
        dirs_to_create = []
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

import sys
import time
import logging
import socket
import stat
from pathlib import Path
from typing import Dict, Optional, Any, List

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
from .exceptions import SSHCommandError, NetworkError
from .console_helper import console, RICH_AVAILABLE

from rich.console import Console  # type: ignore

console: Console  # type: ignore


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
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
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
                _, stdout, _ = ssh_client.exec_command('echo "connection_test"', timeout=5)
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
            Dict[str, Any]: Dictionary containing execution results with keys:
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
                    msg="SSH key file has insecure permissions or is inaccessible",
                    host=host
                )
            
            # Establish SSH connection
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
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
                _, stdout, stderr = ssh_client.exec_command(command, timeout=effective_timeout)
                
                # Collect output and exit status
                stdout_data = stdout.read().decode('utf-8', errors='replace')
                stderr_data = stderr.read().decode('utf-8', errors='replace')
                exit_status = stdout.channel.recv_exit_status()
                
                execution_time = time.time() - start_time
                
                # Prepare result dictionary
                result: Dict[str, Any] = {
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
                msg=error_msg,
                host=host
            ) from e
            
        except paramiko.SSHException as e:
            execution_time = time.time() - start_time
            error_msg = f"SSH connection error: {e}"
            self.logger.error(error_msg)
            raise SSHCommandError(
                command=command,
                msg=error_msg,
                host=host
            ) from e
            
        except socket.timeout as e:
            execution_time = time.time() - start_time
            error_msg = f"SSH command timeout after {effective_timeout}s"
            self.logger.error(error_msg)
            raise SSHCommandError(
                command=command,
                msg=error_msg,
                host=host
            ) from e
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected SSH error: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise SSHCommandError(
                command=command,
                msg=error_msg,
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
            output_sections: List[str] = []
            
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
        results: List[Dict[str, Any]] = []
        
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
                error_result: Dict[str, Any] = {
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