"""Custom exceptions for the LPEM tool."""

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
        super().__init__(f"Validation failed: {'; '.join(reasons)}")
