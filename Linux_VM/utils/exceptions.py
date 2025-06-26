# --- Part 1: Standard Library Imports ---
import json
import os
import re
import shlex
import socket
import stat  # For checking file permissions
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
# --- Part 4: Console Initialization & Custom Exceptions ---
# --- Initialize Rich Console ---
# Set highlight=False to avoid potential conflicts with typer coloring/markup
# Use stderr=True if you want logs/errors to go to stderr separately
console = Console(stderr=False)

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
        super().__init__(f"Validation failed: {'; '.join(reasons)}")