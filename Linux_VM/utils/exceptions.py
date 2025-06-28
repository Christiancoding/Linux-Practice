#!/usr/bin/env python3
"""
Custom Exception Definitions for Linux+ Practice Environment Manager

Comprehensive exception hierarchy providing specific error handling
for VM operations, SSH connections, snapshots, and challenge management.
"""

import sys
from typing import List, Optional, Any, Dict

# Ensure Python 3.8+ compatibility
if sys.version_info < (3, 8):
    print("Linux+ Practice Environment Manager requires Python 3.8+")
    sys.exit(1)


class PracticeToolError(Exception):
    """
    Base exception for all Linux+ Practice Environment Manager errors.
    
    Provides a common foundation for all tool-specific exceptions
    with enhanced error context and user-friendly messaging.
    """
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize base practice tool exception.
        
        Args:
            message: Human-readable error description
            error_code: Optional error code for programmatic handling
            context: Optional context dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        """Return formatted error message with context if available."""
        base_msg = self.message
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        
        if self.context:
            context_info = ", ".join([f"{k}={v}" for k, v in self.context.items()])
            base_msg += f" (Context: {context_info})"
        
        return base_msg
class LibvirtConnectionError(PracticeToolError):
    """
    Raised when libvirt connection establishment fails.
    
    This exception indicates connection issues with the libvirt daemon,
    permission problems, or service unavailability.
    """
    
    def __init__(self, libvirt_uri: str, original_error: Optional[str] = None):
        """
        Initialize libvirt connection exception.
        
        Args:
            libvirt_uri: The libvirt URI that failed to connect
            original_error: Optional original error message from libvirt
        """
        context = {"libvirt_uri": libvirt_uri}
        if original_error:
            context["original_error"] = original_error
        
        message = f"Failed to connect to libvirt at '{libvirt_uri}'"
        if original_error:
            message += f": {original_error}"
        
        super().__init__(message, error_code="LIBVIRT_CONNECTION_FAILED", context=context)
        self.libvirt_uri = libvirt_uri
        self.original_error = original_error


class NetworkError(PracticeToolError):
    """
    Raised when network-related operations fail.
    
    Covers IP address discovery, connectivity testing, and network
    interface operations that encounter errors during execution.
    """
    
    def __init__(self, message: str, host: Optional[str] = None, 
                 timeout: Optional[int] = None, port: Optional[int] = None):
        """
        Initialize network error exception.
        
        Args:
            message: Human-readable error description
            host: Optional hostname or IP address involved
            timeout: Optional timeout value that was exceeded
            port: Optional port number involved
        """
        context: Dict[str, Any] = {}
        if host:
            context["host"] = host
        if timeout:
            context["timeout"] = timeout
        if port:
            context["port"] = port
        
        super().__init__(message, error_code="NETWORK_ERROR", context=context)
        self.host = host
        self.timeout = timeout
        self.port = port


class SSHCommandError(PracticeToolError):
    """
    Raised when SSH command execution fails.
    
    Provides detailed information about command execution failures
    including exit status, stderr output, and connection details.
    """
    
    def __init__(self, command: str, msg: Optional[str] = None, exit_status: Optional[int] = None,
                 stderr: Optional[str] = None, host: Optional[str] = None):
        """
        Initialize SSH command error exception.
        
        Args:
            command: The command that failed to execute
            msg: Optional custom error message
            exit_status: Optional exit status code from command
            stderr: Optional stderr output from command
            host: Optional hostname where command was executed
        """
        context = {"command": command}
        if exit_status is not None:
            context["exit_status"] = str(exit_status)
        if stderr:
            context["stderr"] = stderr
        if host:
            context["host"] = host
        
        if msg:
            message = msg
        else:
            message = f"SSH command failed: {command}"
            if exit_status is not None:
                message += f" (exit code: {exit_status})"
        
        super().__init__(message, error_code="SSH_COMMAND_FAILED", context=context)
        self.command = command
        self.exit_status = exit_status
        self.stderr = stderr
        self.host = host


class AgentCommandError(PracticeToolError):
    """
    Raised when QEMU Guest Agent command execution fails.
    
    This exception indicates communication failures with the QEMU Guest Agent
    or command execution errors within the guest system.
    """
    
    def __init__(self, command: str, vm_name: Optional[str] = None, 
                 agent_error: Optional[str] = None):
        """
        Initialize agent command error exception.
        
        Args:
            command: The agent command that failed
            vm_name: Optional VM name for context
            agent_error: Optional error message from agent
        """
        context = {"command": command}
        if vm_name:
            context["vm_name"] = vm_name
        if agent_error:
            context["agent_error"] = agent_error
        
        message = f"QEMU Guest Agent command failed: {command}"
        if vm_name:
            message += f" on VM '{vm_name}'"
        
        super().__init__(message, error_code="AGENT_COMMAND_FAILED", context=context)
        self.command = command
        self.vm_name = vm_name
        self.agent_error = agent_error

class VMNotFoundError(PracticeToolError):
    """
    Raised when a specified virtual machine cannot be found in libvirt.
    
    This exception indicates that the requested VM name does not exist
    in the current libvirt connection or the user lacks permissions.
    """
    
    def __init__(self, vm_name: str, libvirt_uri: Optional[str] = None):
        """
        Initialize VM not found exception.
        
        Args:
            vm_name: Name of the VM that could not be found
            libvirt_uri: Optional libvirt connection URI for context
        """
        context = {"vm_name": vm_name}
        if libvirt_uri:
            context["libvirt_uri"] = libvirt_uri
        
        message = f"Virtual machine '{vm_name}' not found"
        super().__init__(message, error_code="VM_NOT_FOUND", context=context)
        self.vm_name = vm_name
        self.libvirt_uri = libvirt_uri


class SnapshotOperationError(PracticeToolError):
    """
    Raised when VM snapshot operations fail.
    
    Covers snapshot creation, deletion, restoration, and listing operations
    that encounter errors during execution.
    """
    
    def __init__(self, operation: str, snapshot_name: Optional[str] = None, 
                 vm_name: Optional[str] = None, underlying_error: Optional[Exception] = None):
        """
        Initialize snapshot operation exception.
        
        Args:
            operation: Type of snapshot operation that failed
            snapshot_name: Name of the snapshot involved in the operation
            vm_name: Name of the VM associated with the snapshot
            underlying_error: Optional underlying exception that caused the failure
        """
        context = {"operation": operation}
        if snapshot_name:
            context["snapshot_name"] = snapshot_name
        if vm_name:
            context["vm_name"] = vm_name
        if underlying_error:
            context["underlying_error"] = str(underlying_error)
        
        message = f"Snapshot operation '{operation}' failed"
        if snapshot_name and vm_name:
            message += f" for snapshot '{snapshot_name}' on VM '{vm_name}'"
        
        super().__init__(message, error_code="SNAPSHOT_OPERATION_FAILED", context=context)
        self.operation = operation
        self.snapshot_name = snapshot_name
        self.vm_name = vm_name
        self.underlying_error = underlying_error


class ChallengeLoadError(PracticeToolError):
    """
    Raised when challenge files cannot be loaded or parsed.
    
    Covers YAML parsing errors, file access issues, and structural
    problems with challenge definition files.
    """
    
    def __init__(self, message: str, file_path: Optional[str] = None,
                 yaml_error: Optional[Exception] = None):
        """
        Initialize challenge loading exception.
        
        Args:
            message: Error description
            file_path: Path to the challenge file that failed to load
            yaml_error: Optional underlying YAML parsing error
        """
        context: Dict[str, Any] = {}
        if file_path:
            context["file_path"] = file_path
        if yaml_error:
            context["yaml_error"] = str(yaml_error)
        
        super().__init__(message, error_code="CHALLENGE_LOAD_FAILED", context=context)
        self.file_path = file_path
        self.yaml_error = yaml_error


class ChallengeValidationError(Exception):
    """
    Raised when challenge validation steps fail during execution.
    
    This exception specifically handles validation failures and provides
    detailed reasons for why the challenge validation did not pass.
    
    Note: Inherits from Exception directly (not PracticeToolError) to maintain
          compatibility with existing validation logic in ww.py.
    """
    
    def __init__(self, reasons: List[str], challenge_id: Optional[str] = None,
                 step_number: Optional[int] = None):
        """
        Initialize challenge validation exception.
        
        Args:
            reasons: List of specific validation failure reasons
            challenge_id: Optional challenge identifier for context
            step_number: Optional validation step number that failed
        """
        self.reasons = reasons
        self.challenge_id = challenge_id
        self.step_number = step_number
        
        # Create user-friendly message
        reason_text = '; '.join(reasons)
        message = f"Validation failed: {reason_text}"
        
        if challenge_id:
            message = f"Challenge '{challenge_id}' validation failed: {reason_text}"
        
        if step_number is not None:
            message = f"Step {step_number} - {message}"
        
        super().__init__(message)
    
    def add_reason(self, reason: str) -> None:
        """
        Add an additional validation failure reason.
        
        Args:
            reason: Additional reason for validation failure
        """
        self.reasons.append(reason)
    
    def get_detailed_report(self) -> str:
        """
        Generate a detailed validation failure report.
        
        Returns:
            str: Formatted report of all validation failures
        """
        report = ["Challenge Validation Failed:"]
        for i, reason in enumerate(self.reasons, 1):
            report.append(f"  {i}. {reason}")
        
        if self.challenge_id:
            report.insert(1, f"Challenge ID: {self.challenge_id}")
        
        if self.step_number is not None:
            report.insert(-len(self.reasons), f"Failed at Step: {self.step_number}")
        
        return '\n'.join(report)


class ConfigurationError(PracticeToolError):
    """
    Raised when configuration validation or loading fails.
    
    Indicates problems with application configuration, missing
    required settings, or invalid configuration values.
    """
    
    def __init__(self, setting: str, value: Optional[Any] = None, 
                 expected: Optional[str] = None):
        """
        Initialize configuration validation exception.
        
        Args:
            setting: Name of the configuration setting that failed
            value: The invalid value (if applicable)
            expected: Description of expected value format
        """
        context = {"setting": setting}
        if value is not None:
            context["value"] = str(value)
        if expected:
            context["expected"] = expected
        
        message = f"Configuration error for setting '{setting}'"
        if expected:
            message += f" (expected: {expected})"
        
        super().__init__(message, error_code="CONFIG_ERROR", context=context)
        self.setting = setting
        self.value = value
        self.expected = expected


# Convenience function for error reporting
def format_exception_for_user(exception: Exception) -> str:
    """
    Format any exception for user-friendly display.
    
    Args:
        exception: Exception instance to format
        
    Returns:
        str: User-friendly error message
    """
    if isinstance(exception, PracticeToolError):
        return str(exception)
    elif isinstance(exception, ChallengeValidationError):
        return exception.get_detailed_report()
    else:
        return f"Unexpected error: {exception}"


# Export all exception classes
__all__ = [
    'PracticeToolError',
    'VMNotFoundError',
    'SnapshotOperationError', 
    'NetworkError',
    'SSHCommandError',
    'ChallengeLoadError',
    'ChallengeValidationError',
    'ConfigurationError',
    'format_exception_for_user'
]