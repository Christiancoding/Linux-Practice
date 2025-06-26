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
# -- Part 17:--- Main Execution Guard ---

if __name__ == "__main__":
    # Dependency checks already performed by imports at the top

    # Check default SSH key validity before Typer parsing (only checks default)
    try:
        _validate_ssh_key(Config.DEFAULT_SSH_KEY_PATH)
    except PracticeToolError as key_err:
        # Non-fatal warning if default key is bad, user might specify --key
        console.print(f"[yellow]Warning:[/yellow] Default SSH key issue: {key_err}", style="yellow")
        console.print("[yellow]         Specify a valid key using --key if needed.[/]", style="yellow")
    except Exception as key_check_err:
        # Catch potential errors during path resolution/check itself
        console.print(f"[yellow]Warning:[/yellow] Could not check default SSH key '{Config.DEFAULT_SSH_KEY_PATH}': {key_check_err}", style="yellow")

    # Check if default challenges directory exists
    if not Config.DEFAULT_CHALLENGES_DIR.exists():
         console.print(f"[yellow]Warning:[/yellow] Default challenges directory '{Config.DEFAULT_CHALLENGES_DIR}' not found.", style="yellow")
         console.print("[yellow]         Create it or specify a directory using --challenges-dir.", style="yellow")

    # Run the Typer app
    app()
    