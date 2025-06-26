#!/usr/bin/env python3
"""
Linux+ Practice Environment Manager (LPEM) - Main Entry Point
"""
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
# Add to main.py imports
from controllers.vm_controller import app as vm_app

# Add to main.py
@app.command()
def vm():
    """VM management and practice challenges"""
    vm_app()

# Or integrate VM commands directly:
@app.command()
def vm_start():
    """Start VM session"""
    from utils.vm_manager import VMManager
    vm_manager = VMManager()
    vm_manager.start_session()

if __name__ == "__main__":
    from controllers.vm_controller import app
    app()