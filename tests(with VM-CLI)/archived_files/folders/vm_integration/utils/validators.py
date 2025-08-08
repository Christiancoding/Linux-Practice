#!/usr/bin/env python3
"""
Challenge Validation System

Comprehensive validation framework for Linux+ practice challenges
with modular validation steps, robust error handling, and detailed
progress reporting for educational assessment.
"""

import sys
import re
import logging
from pathlib import Path
from typing import Dict, List, Any

# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("Challenge Validator requires Python 3.8+. Please upgrade.")
    sys.exit(1)

# Import required dependencies
try:
    import yaml
except ImportError:
    print("Error: Missing required library 'PyYAML'.\n"
          "Please install it (e.g., 'pip install pyyaml') and try again.", 
          file=sys.stderr)
    sys.exit(1)

# Import local modules
from .config import ChallengeConfiguration
from .exceptions import ChallengeValidationError, SSHCommandError
from .ssh_manager import SSHManager
from .console_helper import console, Panel, Syntax, RICH_AVAILABLE

from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    console: Any


class ChallengeValidator:
    """
    Advanced challenge validation system with modular validation steps.
    
    Provides comprehensive validation capabilities for Linux+ practice challenges
    including command execution, service status checking, file validation,
    and network connectivity testing with detailed progress reporting.
    """
    
    def __init__(self):
        """Initialize challenge validation system with logging and SSH management."""
        self._setup_logging()
        self.ssh_manager = SSHManager()
        self.logger = logging.getLogger(__name__)
        
        # Registry of available validation step types
        self.validation_registry: Dict[str, Any] = {
            "run_command": self._validate_run_command,
            "check_service_status": self._validate_check_service_status,
            "check_port_listening": self._validate_check_port_listening,
            "check_file_exists": self._validate_check_file_exists,
            "check_file_contains": self._validate_check_file_contains,
            # Add these new validation types:
            "check_user_group": self._validate_check_user_group,
            "check_command": self._validate_check_command,
            "check_history": self._validate_check_history,
            "ensure_group_exists": self._validate_ensure_group_exists,
            "ensure_user_exists": self._validate_ensure_user_exists,
        }
    
    def _setup_logging(self) -> None:
        """Configure comprehensive logging infrastructure for validation operations."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('challenge_validator.log')
            ]
        )
    
    def validate_challenge_structure(self, challenge_data: Dict[str, Any], 
                                   filename: str = "challenge") -> List[str]:
        """
        Perform comprehensive structural validation of challenge data against expected schema.
        
        Args:
            challenge_data: Loaded challenge data dictionary
            filename: Source filename for error reporting context
            
        Returns:
            List[str]: List of validation error messages (empty if valid)
        """
        errors: List[str] = []
        self.logger.debug(f"Validating challenge structure for: {filename}")
        
        # Validate top-level keys
        required_keys = ChallengeConfiguration.REQUIRED_CHALLENGE_KEYS
        allowed_keys = ChallengeConfiguration.ALLOWED_CHALLENGE_KEYS
        
        # Check for unknown keys
        for key in challenge_data:
            if key not in allowed_keys:
                errors.append(f"'{filename}': Unknown top-level key: '{key}'")
        
        # Check for missing required keys
        for key in required_keys:
            if key not in challenge_data:
                errors.append(f"'{filename}': Missing required top-level key: '{key}'")
        
        # Validate data types for key fields
        type_validations = {
            'id': str,
            'name': str,
            'description': str,
            'category': str,
            'difficulty': str,
            'user_action_simulation': str,
            'flag': str
        }
        
        for field, expected_type in type_validations.items():
            if field in challenge_data and not isinstance(challenge_data[field], expected_type):
                errors.append(f"'{filename}': '{field}' must be a {expected_type.__name__}.")
        
        # Validate list fields
        if 'concepts' in challenge_data:
            if not isinstance(challenge_data['concepts'], list):
                errors.append(f"'{filename}': 'concepts' must be a list of strings.")
            else:
                if not all(isinstance(c, str) for c in challenge_data['concepts']):
                    errors.append(f"'{filename}': All items in 'concepts' must be strings.")
        
        # Validate score field (should be convertible to integer)
        if 'score' in challenge_data:
            try:
                int(challenge_data['score'])
            except (ValueError, TypeError):
                errors.append(f"'{filename}': 'score' ('{challenge_data['score']}') must be an integer.")
        
        # Validate challenge ID format
        challenge_id = challenge_data.get('id')
        if challenge_id and isinstance(challenge_id, str):
            if not re.match(r'^[a-zA-Z0-9._-]+$', challenge_id):
                errors.append(
                    f"'{filename}': 'id' field '{challenge_id}' contains invalid characters. "
                    "Use only letters, numbers, hyphens, underscores, periods."
                )
        
        # Validate validation steps structure
        if 'validation' in challenge_data:
            validation_errors = self._validate_validation_steps_structure(
                challenge_data['validation'], filename
            )
            errors.extend(validation_errors)
        
        self.logger.debug(f"Structure validation completed for {filename}: {len(errors)} errors found")
        return errors
    
    def _validate_validation_steps_structure(self, validation_steps: Any, 
                                           filename: str) -> List[str]:
        """
        Validate the structure of validation steps within a challenge.
        
        Args:
            validation_steps: Validation steps data from challenge
            filename: Source filename for error context
            
        Returns:
            List[str]: List of validation errors
        """
        errors: List[str] = []
        
        if not isinstance(validation_steps, list):
            errors.append(f"'{filename}': 'validation' must be a list of validation steps.")
            return errors
        
        from typing import Dict, List, Any
        validation_steps_typed: List[Dict[str, Any]] = validation_steps

        for i, step in enumerate(validation_steps_typed, 1):
            step: Dict[str, Any]
            # Check for required 'type' field
            if 'type' not in step:
                errors.append(f"'{filename}': Validation step {i} missing required 'type' field.")
                continue
            
            step_type: str = step['type']
            if step_type not in self.validation_registry:
                supported_types = ', '.join(self.validation_registry.keys())
                errors.append(
                    f"'{filename}': Validation step {i} has unsupported type: '{step_type}'. "
                    f"Supported types: {supported_types}"
                )
        
        return errors
    
    def execute_validation_step(self, step_num: int, step_data: Dict[str, Any],
                              vm_ip: str, ssh_user: str, ssh_key: Path, 
                              verbose: bool = False) -> None:
        """
        Execute a single validation step with comprehensive error handling.
        
        Args:
            step_num: Step number for progress reporting
            step_data: Validation step configuration dictionary
            vm_ip: Target VM IP address
            ssh_user: SSH username for VM access
            ssh_key: Path to SSH private key
            verbose: Enable detailed logging and output
            
        Raises:
            ChallengeValidationError: If validation step fails
        """
        step_type = step_data.get("type")
        step_title = f"Step {step_num}: [bold cyan]{step_type}[/]"

        self.logger.info(f"Executing validation step {step_num}: {step_type}")

        # Ensure step_type is a string before using as dict key
        if not isinstance(step_type, str):
            error_msg = f"Validation step {step_num} missing or invalid 'type' field."
            self.logger.error(error_msg)
            raise ChallengeValidationError([error_msg])

        # Get the appropriate validation function
        validator_func = self.validation_registry.get(step_type)
        if not validator_func:
            error_msg = f"Unsupported validation step type: '{step_type}'"
            self.logger.error(error_msg)
            raise ChallengeValidationError([error_msg])
        
        try:
            # Execute the validation step
            validator_func(step_data, vm_ip, ssh_user, ssh_key, verbose)
            
            # Display success message
            success_content = "[green]:heavy_check_mark: Passed[/]"
            if RICH_AVAILABLE:
                console.print(Panel(success_content, title=step_title, border_style="green", expand=False))
            else:
                console.print(f"--- {step_title}: Passed ---")
            
            self.logger.info(f"Validation step {step_num} passed successfully")
            
        except ChallengeValidationError as e:
            # Format and display validation failure
            reason_text = "\n".join([f"- {r}" for r in e.reasons])
            failure_content = f"[bold red]:x: Failed[/]\n{reason_text}"
            
            if RICH_AVAILABLE:
                console.print(Panel(failure_content, title=step_title, border_style="red", expand=False))
            else:
                console.print(f"--- {step_title}: FAILED ---")
                console.print(reason_text)
                console.print("--- End Failure ---")
            
            self.logger.error(f"Validation step {step_num} failed: {'; '.join(e.reasons)}")
            raise e
            
        except Exception as ex:
            # Handle unexpected errors during validation
            reason = f"Unexpected error during validation logic: {ex}"
            failure_content = f"[bold red]:x: Failed[/]\n{reason}"
            
            if RICH_AVAILABLE:
                console.print(Panel(failure_content, title=step_title, border_style="red", expand=False))
                console.print_exception(show_locals=False)
            else:
                console.print(f"--- {step_title}: FAILED ---")
                console.print(reason)
                console.print("--- End Failure ---")
            
            self.logger.error(f"Unexpected error in validation step {step_num}: {ex}", exc_info=True)
            raise ChallengeValidationError([reason]) from ex
    
    def _validate_run_command(self, step_data: Dict[str, Any], vm_ip: str, 
                            ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate by executing a command and checking its success.
        
        Args:
            step_data: Step configuration with 'command' and optional 'expected_exit_code'
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If command execution fails validation
        """
        command = step_data.get("command")
        expected_exit_code = step_data.get("expected_exit_code", 0)
        
        if not command:
            raise ChallengeValidationError(["'run_command' step missing required 'command' field."])
        
        try:
            result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
            
            actual_exit_code = result.get('exit_status', -1)
            if actual_exit_code != expected_exit_code:
                stderr_output = result.get('stderr', '').strip()
                error_details = [
                    f"Command '{command}' exited with code {actual_exit_code}, expected {expected_exit_code}."
                ]
                if stderr_output:
                    error_details.append(f"Error output: {stderr_output}")
                
                raise ChallengeValidationError(error_details)
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"SSH command execution failed: {e}"]) from e
    
    def _validate_check_service_status(self, step_data: Dict[str, Any], vm_ip: str,
                                     ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate system service status using systemctl.
        
        Args:
            step_data: Step configuration with 'service' and 'expected_status'
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If service status doesn't match expectation
        """
        service_name = step_data.get("service")
        expected_status = step_data.get("expected_status", "active")
        
        if not service_name:
            raise ChallengeValidationError(["'check_service_status' step missing required 'service' field."])
        
        command = f"systemctl is-active {service_name}"
        
        try:
            result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
            
            actual_status = result.get('stdout', '').strip().lower()
            expected_status_lower = expected_status.lower()
            
            if actual_status != expected_status_lower:
                raise ChallengeValidationError([
                    f"Service '{service_name}' status is '{actual_status}', expected '{expected_status_lower}'."
                ])
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"Failed to check service status: {e}"]) from e
    
    def _validate_check_port_listening(self, step_data: Dict[str, Any], vm_ip: str,
                                     ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate that a specific port is listening on the target system.
        
        Args:
            step_data: Step configuration with 'port' and optional 'protocol'
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If port is not listening
        """
        port = step_data.get("port")
        protocol = step_data.get("protocol", "tcp").lower()
        
        if not port:
            raise ChallengeValidationError(["'check_port_listening' step missing required 'port' field."])
        
        try:
            port_num = int(port)
        except (ValueError, TypeError):
            raise ChallengeValidationError([f"Invalid port number: '{port}'. Must be an integer."])
        
        # Use netstat or ss command to check port status
        if protocol == "tcp":
            command = f"ss -tlnp | grep ':{port_num} ' || netstat -tlnp | grep ':{port_num} '"
        elif protocol == "udp":
            command = f"ss -ulnp | grep ':{port_num} ' || netstat -ulnp | grep ':{port_num} '"
        else:
            raise ChallengeValidationError([f"Unsupported protocol: '{protocol}'. Use 'tcp' or 'udp'."])
        
        try:
            result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
            
            if result.get('exit_status', -1) != 0:
                raise ChallengeValidationError([
                    f"Port {port_num}/{protocol} is not listening on the system."
                ])
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"Failed to check port status: {e}"]) from e
    
    def _validate_check_file_exists(self, step_data: Dict[str, Any], vm_ip: str,
                                  ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate that a file or directory exists on the target system.
        
        Args:
            step_data: Step configuration with 'path' and optional 'should_exist'
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If file existence doesn't match expectation
        """
        file_path = step_data.get("path")
        should_exist = step_data.get("should_exist", True)
        
        if not file_path:
            raise ChallengeValidationError(["'check_file_exists' step missing required 'path' field."])
        
        command = f"test -e '{file_path}'"
        
        try:
            result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
            
            file_exists = result.get('exit_status', -1) == 0
            
            if file_exists != should_exist:
                existence_state = "exists" if file_exists else "does not exist"
                expected_state = "exist" if should_exist else "not exist"
                raise ChallengeValidationError([
                    f"File '{file_path}' {existence_state}, but it should {expected_state}."
                ])
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"Failed to check file existence: {e}"]) from e
    
    def _validate_check_file_contains(self, step_data: Dict[str, Any], vm_ip: str,
                                    ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate that a file contains (or doesn't contain) specific content.
        
        Args:
            step_data: Step configuration with 'path', 'content', and optional 'should_contain'
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If file content doesn't match expectation
        """
        file_path = step_data.get("path")
        search_content = step_data.get("text")
        should_contain = step_data.get("should_contain", True)
        
        if not file_path:
            raise ChallengeValidationError(["'check_file_contains' step missing required 'path' field."])
        
        if not search_content and not step_data.get("matches_regex"):
            raise ChallengeValidationError(["'check_file_contains' step missing required 'text' or 'matches_regex' field."])
        
        # Use grep to search for content in the file
        command = f"grep -F '{search_content}' '{file_path}'"
        
        try:
            result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
            
            content_found = result.get('exit_status', -1) == 0
            
            if content_found != should_contain:
                found_state = "found" if content_found else "not found"
                expected_state = "be found" if should_contain else "not be found"
                search_desc = f"content '{search_content}'"
                
                raise ChallengeValidationError([
                    f"Expected {search_desc} to {expected_state} in '{file_path}', but it was {found_state}."
                ])
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"Failed to search file content: {e}"]) from e

    def _validate_check_user_group(self, step_data: Dict[str, Any], vm_ip: str,
                                ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate user and group management operations.
        
        Args:
            step_data: Step configuration with check_type and related parameters
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If user/group validation fails
        """
        check_type = step_data.get("check_type")
        username = step_data.get("username")
        
        if not check_type:
            raise ChallengeValidationError(["'check_user_group' step missing required 'check_type' field."])
        
        try:
            if check_type == "user_exists":
                if not username:
                    raise ChallengeValidationError(["'user_exists' check missing required 'username' field."])
                
                command = f"id {username}"
                result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
                
                if not result.get('success', False):
                    raise ChallengeValidationError([f"User '{username}' does not exist on the system."])
                    
            elif check_type == "user_primary_group":
                if not username:
                    raise ChallengeValidationError(["'user_primary_group' check missing required 'username' field."])
                
                expected_group = step_data.get("group")
                if not expected_group:
                    raise ChallengeValidationError(["'user_primary_group' check missing required 'group' field."])
                
                command = f"id -gn {username}"
                result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
                
                if not result.get('success', False):
                    raise ChallengeValidationError([f"Could not determine primary group for user '{username}'."])
                
                actual_group = result.get('stdout', '').strip()
                if actual_group != expected_group:
                    raise ChallengeValidationError([
                        f"User '{username}' primary group is '{actual_group}', expected '{expected_group}'."
                    ])
                    
            elif check_type == "user_in_group":
                if not username:
                    raise ChallengeValidationError(["'user_in_group' check missing required 'username' field."])
                
                expected_group = step_data.get("group")
                if not expected_group:
                    raise ChallengeValidationError(["'user_in_group' check missing required 'group' field."])
                
                command = f"groups {username}"
                result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
                
                if not result.get('success', False):
                    raise ChallengeValidationError([f"Could not determine groups for user '{username}'."])
                
                user_groups = result.get('stdout', '').strip()
                if expected_group not in user_groups.split():
                    raise ChallengeValidationError([
                        f"User '{username}' is not in group '{expected_group}'. Current groups: {user_groups}"
                    ])
                    
            elif check_type == "user_shell":
                if not username:
                    raise ChallengeValidationError(["'user_shell' check missing required 'username' field."])
                
                expected_shell = step_data.get("shell")
                if not expected_shell:
                    raise ChallengeValidationError(["'user_shell' check missing required 'shell' field."])
                
                command = f"getent passwd {username} | cut -d: -f7"
                result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
                
                if not result.get('success', False):
                    raise ChallengeValidationError([f"Could not determine shell for user '{username}'."])
                
                actual_shell = result.get('stdout', '').strip()
                if actual_shell != expected_shell:
                    raise ChallengeValidationError([
                        f"User '{username}' shell is '{actual_shell}', expected '{expected_shell}'."
                    ])
            else:
                raise ChallengeValidationError([f"Unsupported check_type for user_group validation: '{check_type}'"])
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"SSH command execution failed: {e}"]) from e

    def _validate_check_command(self, step_data: Dict[str, Any], vm_ip: str,
                            ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate by executing a general command with flexible success criteria.
        
        Args:
            step_data: Step configuration with 'command' and optional success criteria
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If command validation fails
        """
        command = step_data.get("command")
        expected_exit_status = step_data.get("expected_exit_status", 0)
        
        if not command:
            raise ChallengeValidationError(["'check_command' step missing required 'command' field."])
        
        try:
            result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
            
            actual_exit_status = result.get('exit_status', -1)
            if actual_exit_status != expected_exit_status:
                stderr_output = result.get('stderr', '').strip()
                error_details = [
                    f"Command '{command}' exited with code {actual_exit_status}, expected {expected_exit_status}."
                ]
                if stderr_output:
                    error_details.append(f"Error output: {stderr_output}")
                
                raise ChallengeValidationError(error_details)
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"SSH command execution failed: {e}"]) from e

    def _validate_check_history(self, step_data: Dict[str, Any], vm_ip: str,
                            ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate command history for specific patterns or commands.
        
        Args:
            step_data: Step configuration with command_pattern and expected_count
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If history validation fails
        """
        command_pattern = step_data.get("command_pattern")
        expected_count = step_data.get("expected_count", ">0")
        user_context = step_data.get("user_context", ssh_user)
        
        if not command_pattern:
            raise ChallengeValidationError(["'check_history' step missing required 'command_pattern' field."])
        
        try:
            # Check history for the specified user context
            if user_context == "root":
                history_command = f"sudo bash -c 'history | grep -E \"{command_pattern}\" | wc -l'"
            else:
                history_command = f"history | grep -E '{command_pattern}' | wc -l"
            
            result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, history_command, verbose=verbose)
            
            if not result.get('success', False):
                raise ChallengeValidationError([f"Failed to check command history: {result.get('stderr', 'Unknown error')}"])
            
            try:
                actual_count = int(result.get('stdout', '0').strip())
            except ValueError:
                raise ChallengeValidationError([f"Could not parse history count from output: {result.get('stdout', '')}"])
            
            # Parse expected count (supports ">0", ">=1", "==2", etc.)
            if expected_count.startswith(">"):
                threshold = int(expected_count[1:]) if expected_count[1:] else 0
                if actual_count <= threshold:
                    raise ChallengeValidationError([
                        f"Expected more than {threshold} occurrences of pattern '{command_pattern}' in history, found {actual_count}."
                    ])
            elif expected_count.startswith(">="):
                threshold = int(expected_count[2:])
                if actual_count < threshold:
                    raise ChallengeValidationError([
                        f"Expected at least {threshold} occurrences of pattern '{command_pattern}' in history, found {actual_count}."
                    ])
            elif expected_count.startswith("==") or expected_count.isdigit():
                threshold = int(expected_count[2:] if expected_count.startswith("==") else expected_count)
                if actual_count != threshold:
                    raise ChallengeValidationError([
                        f"Expected exactly {threshold} occurrences of pattern '{command_pattern}' in history, found {actual_count}."
                    ])
            else:
                raise ChallengeValidationError([f"Unsupported expected_count format: '{expected_count}'"])
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"SSH command execution failed: {e}"]) from e

    def _validate_ensure_group_exists(self, step_data: Dict[str, Any], vm_ip: str,
                                    ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate that a group exists on the system (typically used in setup).
        
        Args:
            step_data: Step configuration with 'group' name
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If group validation fails
        """
        group_name = step_data.get("group")
        user_context = step_data.get("user_context", ssh_user)
        
        if not group_name:
            raise ChallengeValidationError(["'ensure_group_exists' step missing required 'group' field."])
        
        try:
            command = f"getent group {group_name}"
            result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
            
            if not result.get('success', False):
                raise ChallengeValidationError([f"Group '{group_name}' does not exist on the system."])
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"SSH command execution failed: {e}"]) from e

    def _validate_ensure_user_exists(self, step_data: Dict[str, Any], vm_ip: str,
                                    ssh_user: str, ssh_key: Path, verbose: bool) -> None:
        """
        Validate that a user exists on the system (typically used in setup).
        
        Args:
            step_data: Step configuration with 'user' name
            vm_ip: Target VM IP address
            ssh_user: SSH username
            ssh_key: SSH private key path
            verbose: Enable verbose output
            
        Raises:
            ChallengeValidationError: If user validation fails
        """
        username = step_data.get("user")
        user_context = step_data.get("user_context", ssh_user)
        
        if not username:
            raise ChallengeValidationError(["'ensure_user_exists' step missing required 'user' field."])
        
        try:
            command = f"id {username}"
            result = self.ssh_manager.run_ssh_command(vm_ip, ssh_user, ssh_key, command, verbose=verbose)
            
            if not result.get('success', False):
                raise ChallengeValidationError([f"User '{username}' does not exist on the system."])
                
        except SSHCommandError as e:
            raise ChallengeValidationError([f"SSH command execution failed: {e}"]) from e
def validate_challenge_file(file_path: Path) -> None:
    """
    Comprehensive validation and display of a challenge YAML file.
    
    Args:
        file_path: Path to the challenge file to validate
        
    Raises:
        SystemExit: If validation fails (for CLI usage)
    """
    validator = ChallengeValidator()
    
    console.print(f":magnifying_glass_right: Validating challenge file: [blue underline]{file_path}[/]")
    
    try:
        # Read and parse the YAML file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            challenge_data = yaml.safe_load(content)
            # Explicitly annotate type for static type checkers
            challenge_data: Dict[str, Any] = challenge_data
        
        # Display file content with syntax highlighting
        if RICH_AVAILABLE:
            syntax = Syntax(content, "yaml", theme="default", line_numbers=True, word_wrap=False)
            # Only pass Syntax (not FallbackSyntax) to Panel
            if type(syntax).__name__ == "Syntax" and hasattr(syntax, "__rich_console__"):
                console.print(Panel(syntax, title=f"Content of '{file_path.name}'", border_style="dim"))
            else:
                # Fallback: print as plain text
                console.print(Panel(str(content), title=f"Content of '{file_path.name}'", border_style="dim"))
        else:
            console.print(f"\n--- Content of '{file_path.name}' ---\n{content}\n------------------------------")
        
        # Validate YAML structure
        # The type of challenge_data is already Dict[str, Any], so no need to check isinstance.
        
        # Perform detailed structure validation
        errors = validator.validate_challenge_structure(challenge_data, file_path.name)
        
        if errors:
            error_text = "\n".join([f"- {error}" for error in errors])
            if RICH_AVAILABLE:
                console.print(Panel(f"[bold red]Validation Failed:[/]\n{error_text}", 
                                  title="Validation Results", border_style="red"))
            else:
                console.print(f"\n--- Validation Failed ---\n{error_text}\n------")
            raise SystemExit(1)
        else:
            success_msg = "[bold green]:heavy_check_mark: Validation Succeeded![/]"
            if RICH_AVAILABLE:
                console.print(Panel(success_msg, title="Validation Results", border_style="green"))
            else:
                console.print("\n--- Validation Succeeded! ---")
            
    except yaml.YAMLError as e:
        error_msg = f"YAML parsing error: {e}"
        console.print(f"[red]:x: {error_msg}[/]")
        raise SystemExit(1)
    except FileNotFoundError:
        error_msg = f"Challenge file not found: {file_path}"
        console.print(f"[red]:x: {error_msg}[/]")
        raise SystemExit(1)
    except Exception as e:
        error_msg = f"Unexpected error during validation: {e}"
        console.print(f"[red]:x: {error_msg}[/]")
        logging.error(error_msg, exc_info=True)
        raise SystemExit(1)


# Convenience functions for backward compatibility with ww.py
def validate_challenge_structure(challenge_data: Dict[str, Any], filename: str = "challenge") -> List[str]:
    """Backward compatibility function for challenge structure validation."""
    validator = ChallengeValidator()
    return validator.validate_challenge_structure(challenge_data, filename)

def execute_validation_step(step_num: int, step_data: Dict[str, Any], vm_ip: str, 
                          ssh_user: str, ssh_key: Path, verbose: bool = False) -> None:
    """Backward compatibility function for validation step execution."""
    validator = ChallengeValidator()
    validator.execute_validation_step(step_num, step_data, vm_ip, ssh_user, ssh_key, verbose)


# Export all public components
__all__ = [
    'ChallengeValidator',
    'validate_challenge_file',
    'validate_challenge_structure',
    'execute_validation_step'
]