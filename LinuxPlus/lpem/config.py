"""Configuration constants for the LPEM tool."""

import libvirt
from pathlib import Path

class Config:
    # VM Defaults
    DEFAULT_VM_NAME: str = "ubuntu24.04-2"
    DEFAULT_SNAPSHOT_NAME: str = "practice_external_snapshot"
    VM_READINESS_TIMEOUT_SECONDS: int = 120
    VM_READINESS_POLL_INTERVAL_SECONDS: int = 5
    VM_SHUTDOWN_TIMEOUT_SECONDS: int = 120

    # SSH Defaults
    DEFAULT_SSH_USER: str = "roo" # !! IMPORTANT: Update if needed !!
    DEFAULT_SSH_KEY_PATH: Path = Path("~/.ssh/id_ed25519").expanduser() # !! IMPORTANT: Update if needed !!
    SSH_CONNECT_TIMEOUT_SECONDS: int = 10
    SSH_COMMAND_TIMEOUT_SECONDS: int = 30
    SSH_KEY_PERMISSIONS_MASK: int = 0o077 # Permissions check: only owner should have access

    # Challenge Defaults
    DEFAULT_CHALLENGES_DIR: Path = Path("./challenges")
    DEFAULT_CHALLENGE_SCORE: int = 100

    # Libvirt Connection URI
    LIBVIRT_URI: str = 'qemu:///system'

    # Exit Codes for systemctl status checks
    EXIT_CODE_ACTIVE: int = 0
    EXIT_CODE_INACTIVE: int = 3
    EXIT_CODE_FAILED_BASE: int = 1 # Any non-zero, non-inactive usually means failure/not-found etc.
    EXIT_CODE_ENABLED: int = 0
    EXIT_CODE_DISABLED: int = 1

# Use getattr for safe access to libvirt error codes if they might be missing
VIR_ERR_NO_DOMAIN = getattr(libvirt, 'VIR_ERR_NO_DOMAIN', -1)
VIR_ERR_NO_DOMAIN_SNAPSHOT = getattr(libvirt, 'VIR_ERR_NO_DOMAIN_SNAPSHOT', -1)
VIR_ERR_OPERATION_INVALID = getattr(libvirt, 'VIR_ERR_OPERATION_INVALID', -1)
VIR_ERR_AGENT_UNRESPONSIVE = getattr(libvirt, 'VIR_ERR_AGENT_UNRESPONSIVE', -1)
VIR_ERR_OPERATION_TIMEOUT = getattr(libvirt, 'VIR_ERR_OPERATION_TIMEOUT', -1)
VIR_ERR_ARGUMENT_UNSUPPORTED = getattr(libvirt, 'VIR_ERR_ARGUMENT_UNSUPPORTED', -1)
VIR_ERR_CONFIG_EXIST = getattr(libvirt, 'VIR_ERR_CONFIG_EXIST', -1)
VIR_ERR_INVALID_DOMAIN = getattr(libvirt, 'VIR_ERR_INVALID_DOMAIN', -1)
