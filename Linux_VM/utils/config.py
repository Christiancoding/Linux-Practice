#!/usr/bin/env python3
"""
Configuration Management for Linux+ Practice Environment Manager

Centralized configuration constants and settings for VM management,
SSH connections, challenge loading, and system operation parameters.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Ensure minimum Python version compatibility
if sys.version_info < (3, 8):
    print("Linux+ Practice Environment Manager requires Python 3.8+")
    sys.exit(1)

# Import libvirt for error code constants (with graceful fallback)
try:
    import libvirt
except ImportError:
    print("Error: Missing required library 'libvirt-python'.\n"
          "Please install it (e.g., 'pip install libvirt-python' or via system package manager) and try again.", 
          file=sys.stderr)
    sys.exit(1)


class VMConfiguration:
    """Virtual Machine management configuration settings."""
    
    # Default VM Settings
    DEFAULT_VM_NAME: str = "ubuntu24.04-2"
    DEFAULT_SNAPSHOT_NAME: str = "practice_external_snapshot"
    
    # VM Operation Timeouts (in seconds)
    READINESS_TIMEOUT_SECONDS: int = 120
    READINESS_POLL_INTERVAL_SECONDS: int = 5
    SHUTDOWN_TIMEOUT_SECONDS: int = 120
    
    # Libvirt Connection Configuration
    LIBVIRT_URI: str = 'qemu:///system'


class SSHConfiguration:
    """SSH connection and authentication configuration settings."""
    
    # Default SSH Connection Parameters
    DEFAULT_SSH_USER: str = "roo"  # Update this for your environment
    DEFAULT_SSH_KEY_PATH: Path = Path("~/.ssh/id_ed25519").expanduser()
    
    # SSH Operation Timeouts (in seconds)
    CONNECT_TIMEOUT_SECONDS: int = 10
    COMMAND_TIMEOUT_SECONDS: int = 30
    
    # SSH Security Settings
    KEY_PERMISSIONS_MASK: int = 0o077  # Only owner should have access
    
    @classmethod
    def validate_ssh_key_path(cls, key_path: Path) -> bool:
        """
        Validate SSH key file permissions and existence.
        
        Args:
            key_path: Path to SSH private key file
            
        Returns:
            bool: True if key is valid and secure, False otherwise
        """
        if not key_path.exists():
            return False
        
        # Check file permissions for security
        key_perms = key_path.stat().st_mode & 0o777
        if key_perms & cls.KEY_PERMISSIONS_MASK:
            return False
        
        return True


class ChallengeConfiguration:
    """Challenge system configuration and default settings."""
    
    # Default Challenge Settings
    DEFAULT_CHALLENGES_DIR: Path = Path("./challenges")
    DEFAULT_CHALLENGE_SCORE: int = 100
    
    # Challenge Validation Settings
    REQUIRED_CHALLENGE_KEYS = ['id', 'name', 'description', 'validation']
    ALLOWED_CHALLENGE_KEYS = [
        'id', 'name', 'description', 'category', 'difficulty', 'score',
        'concepts', 'setup', 'user_action_simulation', 'validation', 'hints', 'flag'
    ]
    
    # Challenge File Processing
    CHALLENGE_FILE_EXTENSIONS = ['.yaml', '.yml']
    
    @classmethod
    def get_challenge_files(cls, directory: Path) -> list:
        """
        Get all valid challenge files from a directory.
        
        Args:
            directory: Directory to scan for challenge files
            
        Returns:
            list: List of Path objects for valid challenge files
        """
        if not directory.exists() or not directory.is_dir():
            return []
        
        challenge_files = []
        for ext in cls.CHALLENGE_FILE_EXTENSIONS:
            challenge_files.extend(directory.glob(f"*{ext}"))
        
        return sorted(challenge_files)


class SystemConfiguration:
    """System-wide configuration and service management settings."""
    
    # Systemctl Status Exit Codes
    EXIT_CODE_ACTIVE: int = 0
    EXIT_CODE_INACTIVE: int = 3
    EXIT_CODE_FAILED_BASE: int = 1  # Any non-zero, non-inactive usually means failure
    EXIT_CODE_ENABLED: int = 0
    EXIT_CODE_DISABLED: int = 1
    
    # Network and Service Validation
    DEFAULT_PING_COUNT: int = 3
    DEFAULT_PORT_TIMEOUT: int = 5
    
    # File System Settings
    DEFAULT_FILE_MODE: str = "0644"
    DEFAULT_DIR_MODE: str = "0755"


class LibvirtErrorCodes:
    """Libvirt error code constants with safe fallback handling."""
    
    # Use getattr for safe access to libvirt error codes
    VIR_ERR_NO_DOMAIN = getattr(libvirt, 'VIR_ERR_NO_DOMAIN', -1)
    VIR_ERR_NO_DOMAIN_SNAPSHOT = getattr(libvirt, 'VIR_ERR_NO_DOMAIN_SNAPSHOT', -1)
    VIR_ERR_OPERATION_INVALID = getattr(libvirt, 'VIR_ERR_OPERATION_INVALID', -1)
    VIR_ERR_AGENT_UNRESPONSIVE = getattr(libvirt, 'VIR_ERR_AGENT_UNRESPONSIVE', -1)
    VIR_ERR_OPERATION_TIMEOUT = getattr(libvirt, 'VIR_ERR_OPERATION_TIMEOUT', -1)
    VIR_ERR_ARGUMENT_UNSUPPORTED = getattr(libvirt, 'VIR_ERR_ARGUMENT_UNSUPPORTED', -1)
    VIR_ERR_CONFIG_EXIST = getattr(libvirt, 'VIR_ERR_CONFIG_EXIST', -1)
    VIR_ERR_INVALID_DOMAIN = getattr(libvirt, 'VIR_ERR_INVALID_DOMAIN', -1)


class ApplicationConfiguration:
    """Main application configuration combining all subsystem settings."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize application configuration with optional config file override.
        
        Args:
            config_file: Optional path to configuration file for overrides
        """
        self.vm = VMConfiguration()
        self.ssh = SSHConfiguration()
        self.challenge = ChallengeConfiguration()
        self.system = SystemConfiguration()
        self.libvirt_errors = LibvirtErrorCodes()
        
        if config_file:
            self._load_config_file(config_file)
    
    def _load_config_file(self, config_file: Path) -> None:
        """
        Load configuration overrides from file.
        
        Args:
            config_file: Path to configuration file
            
        Note:
            This method can be extended to support YAML/JSON config files
            for environment-specific overrides.
        """
        # Future implementation for config file loading
        # Could support YAML/JSON configuration files for different environments
        pass
    
    def validate_configuration(self) -> bool:
        """
        Validate current configuration settings.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Validate SSH key if specified
        if hasattr(self.ssh, 'DEFAULT_SSH_KEY_PATH'):
            if not self.ssh.validate_ssh_key_path(self.ssh.DEFAULT_SSH_KEY_PATH):
                return False
        
        # Validate challenges directory
        if not self.challenge.DEFAULT_CHALLENGES_DIR.parent.exists():
            return False
        
        return True


# Backward compatibility - maintain the original Config class interface
class Config(VMConfiguration, SSHConfiguration, ChallengeConfiguration, SystemConfiguration):
    """
    Legacy configuration class for backward compatibility.
    
    This class combines all configuration sections into a single namespace
    to maintain compatibility with existing code that expects the original
    Config class from ww.py.
    """
    pass


# Global configuration instance for easy importing
config = ApplicationConfiguration()

# Export commonly used configuration classes
__all__ = [
    'VMConfiguration',
    'SSHConfiguration', 
    'ChallengeConfiguration',
    'SystemConfiguration',
    'LibvirtErrorCodes',
    'ApplicationConfiguration',
    'Config',  # Backward compatibility
    'config'   # Global instance
]