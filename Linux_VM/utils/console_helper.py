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

# --- Part 2: Third-Party Library Imports & Checks ---
try:
    import libvirt
except ImportError:
    print("Error: Missing required library 'libvirt-python'.\n"
          "Please install it (e.g., 'pip install libvirt-python' or via system package manager) and try again.", file=sys.stderr)
    sys.exit(1)

try:
    import paramiko
except ImportError:
    print("Error: Missing required library 'paramiko'.\n"
          "Please install it (e.g., 'pip install paramiko') and try again.", file=sys.stderr)
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("Error: Missing required library 'PyYAML'.\n"
          "Please install it (e.g., 'pip install pyyaml') and try again.", file=sys.stderr)
    sys.exit(1)

try:
    import typer
    from typing_extensions import Annotated
except ImportError:
    print("Error: Missing required library 'typer'.\n"
          "Please install it (e.g., 'pip install typer[all]') and try again.", file=sys.stderr)
    sys.exit(1)

# --- Part 3: Rich Library Integration (Optional UI Enhancements) ---
try:
    from rich.console import Console as RichConsole
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Provide dummy classes/functions if rich is not available
    class Console:
        def print(self, *args, **kwargs): typer.echo(*args)
        def rule(self, title="", style=""): typer.echo(f"--- {title} ---")
        def print_exception(self, *args, **kwargs): traceback.print_exc()
    class Panel:
        def __init__(self, content, title="", border_style="dim", expand=True, **kwargs):
            self.content = content
            self.title = title
        def __rich_console__(self, console, options):
             yield f"--- {self.title} ---"
             yield str(self.content)
             yield f"--- End {self.title} ---"
    class Table:
        def __init__(self, title="", **kwargs): self.title=title; self._rows = []; self._columns = []
        def add_column(self, header, **kwargs): self._columns.append(header)
        def add_row(self, *items): self._rows.append(items)
        def __rich_console__(self, console, options):
             if self.title: yield f"--- {self.title} ---"
             if self._columns: yield " | ".join(self._columns)
             yield "-" * (sum(len(str(c)) for c in self._columns) + (len(self._columns) * 3 - 1)) # Separator
             for row in self._rows: yield " | ".join(map(str, row))
             if self.title: yield f"--- End {self.title} ---"
    class Syntax:
         def __init__(self, code, lexer, theme="default", line_numbers=False, word_wrap=False): self.code = code
         def __rich_console__(self, console, options): yield self.code
    class Markdown:
         def __init__(self, markup): self.markup = markup
         def __rich_console__(self, console, options): yield self.markup
    class Text:
         def __init__(self, text, style=""): self.text = text; self.style = style
         def __rich_console__(self, console, options): yield self.text
         @staticmethod
         def assemble(*args): return "".join(str(item[0]) if isinstance(item, tuple) else str(item) for item in args)
    class Confirm:
        @staticmethod
        def ask(prompt, default=False):
            response = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
            if not response: return default
            return response == 'y'
    class Prompt:
        @staticmethod
        def ask(prompt, default=""):
            return input(f"{prompt}: ")
    class Progress: # Dummy Progress
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def add_task(self, description, total=None): return 0 # Return dummy task ID
        def update(self, task_id, **kwargs): pass
        @property
        def finished(self): return True # Always finished for dummy