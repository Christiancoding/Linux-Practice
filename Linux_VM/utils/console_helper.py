#!/usr/bin/env python3
"""
Console Helper Utility

Provides Rich console integration with graceful fallbacks for enhanced
terminal output formatting and user interface elements.
"""

import sys
import traceback
from typing import Any, Optional, List

# Third-party imports with graceful fallback handling
try:
    import typer
except ImportError:
    print("Error: Missing required library 'typer'.\n"
          "Please install it (e.g., 'pip install typer[all]') and try again.", file=sys.stderr)
    sys.exit(1)

# Rich library integration with comprehensive fallback support
_rich_available = False
try:
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.prompt import Prompt, Confirm
    _rich_available = True
except ImportError:
    _rich_available = False

RICH_AVAILABLE = _rich_available


from typing import Any

class ConsoleManager:
    """
    Centralized console management with Rich integration and fallback support.
    
    Provides a unified interface for terminal output that gracefully degrades
    when Rich is not available, ensuring consistent user experience across
    different environments.
    """

    console: Any  # Add type annotation for console attribute
    
    def __init__(self):
        """Initialize console manager with appropriate backend."""
        self._setup_console()
        self._setup_rich_components()
    
    def _setup_console(self) -> None:
        """Configure the primary console interface."""
        if RICH_AVAILABLE:
            # Import RichConsole here to ensure it's available
            from rich.console import Console as RichConsole
            self.console = RichConsole()
        else:
            self.console = FallbackConsole()
    
    def _setup_rich_components(self) -> None:
        """Initialize Rich component classes with fallback implementations."""
        if RICH_AVAILABLE:
            from rich.panel import Panel
            from rich.table import Table
            from rich.progress import Progress
            from rich.progress import SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
            from rich.syntax import Syntax
            from rich.markdown import Markdown
            from rich.text import Text  # Removed unused import
            from rich.prompt import Prompt, Confirm
            self.Panel = Panel
            self.Table = Table
            self.Progress = Progress
            self.SpinnerColumn = SpinnerColumn
            self.TextColumn = TextColumn
            self.BarColumn = BarColumn
            self.TimeElapsedColumn = TimeElapsedColumn
            self.Syntax = Syntax
            self.Markdown = Markdown
            self.Text = Text
            self.Prompt = Prompt
            self.Confirm = Confirm
        else:
            self.Panel = FallbackPanel
            self.Table = FallbackTable
            self.Progress = FallbackProgress
            self.SpinnerColumn = FallbackSpinnerColumn
            self.TextColumn = FallbackTextColumn
            self.BarColumn = FallbackBarColumn
            self.TimeElapsedColumn = FallbackTimeElapsedColumn
            self.Syntax = FallbackSyntax
            self.Markdown = FallbackMarkdown
            self.Text = FallbackText
            self.Prompt = FallbackPrompt
            self.Confirm = FallbackConfirm
    
    def print(self, *args: Any, **kwargs: Any) -> None:
        """Enhanced print with Rich formatting support."""
        self.console.print(*args, **kwargs)
    
    def rule(self, title: str = "", style: str = "") -> None:
        """Print a horizontal rule with optional title."""
        self.console.rule(title, style=style)
    
    def print_exception(self, *args: Any, **kwargs: Any) -> None:
        """Print exception with enhanced formatting."""
        self.console.print_exception(*args, **kwargs)


class FallbackConsole:
    """
    Fallback console implementation when Rich is unavailable.
    
    Provides basic terminal output functionality that mirrors
    Rich's interface for seamless degradation.
    """
    
    def print(self, *args: Any, **kwargs: Any) -> None:
        """Basic print functionality with Rich markup removal."""
        # Remove Rich markup tags for clean fallback output
        clean_args: List[str] = []
        for arg in args:
            if isinstance(arg, str):
                # Simple Rich markup removal (basic patterns)
                import re
                clean_arg = re.sub(r'\[/?[^\]]*\]', '', str(arg))
                clean_args.append(clean_arg)
            else:
                # Ensure arg is a valid object for str()
                try:
                    clean_args.append(str(arg))
                except Exception:
                    clean_args.append(repr(arg))
        # Forward only supported kwargs to typer.echo, with type validation
        echo_kwargs = {}
        if "file" in kwargs:
            file_obj = kwargs["file"]
            # typer.echo expects file to be a file-like object or None
            if file_obj is None or hasattr(file_obj, "write"):
                echo_kwargs["file"] = file_obj
        if "nl" in kwargs:
            # typer.echo expects nl to be a bool
            if isinstance(kwargs["nl"], bool):
                echo_kwargs["nl"] = kwargs["nl"]
        if "err" in kwargs:
            # typer.echo expects err to be a bool
            if isinstance(kwargs["err"], bool):
                echo_kwargs["err"] = kwargs["err"]
        if "color" in kwargs:
            # typer.echo expects color to be a bool
            if isinstance(kwargs["color"], bool):
                echo_kwargs["color"] = kwargs["color"]
        typer.echo(" ".join(str(arg) for arg in clean_args))
    
    def rule(self, title: str = "", style: str = "") -> None:
        """Print a simple text rule."""
        typer.echo(f"--- {title} ---")
    
    def print_exception(self, *args: Any, **kwargs: Any) -> None:
        """Print exception using standard traceback."""
        traceback.print_exc()


class FallbackPanel:
    """Fallback panel implementation for non-Rich environments."""
    
    def __init__(self, content: Any, title: str = "", border_style: str = "dim", 
                 expand: bool = True, **kwargs: Any):
        self.content = content
        self.title = title
        self.border_style = border_style
        self.expand = expand
    
    def __rich_console__(self, console: Any, options: Any):
        """Rich console compatibility method."""
        yield f"--- {self.title} ---"
        yield str(self.content)
        yield f"--- End {self.title} ---"
    
    def __str__(self) -> str:
        """String representation for fallback display."""
        return f"--- {self.title} ---\n{self.content}\n--- End {self.title} ---"


class FallbackTable:
    """Fallback table implementation for structured data display."""
    
    def __init__(self, title: str = "", show_header: bool = True, 
                 header_style: str = "", **kwargs: Any):
        self.title = title
        self.show_header = show_header
        self.header_style = header_style
        self.columns: List[dict[str, str]] = []
        self.rows: List[tuple[Any, ...]] = []
        self._is_grid = False  # Ensure attribute always exists
    
    def add_column(self, header: str = "", style: str = "", **kwargs: Any) -> None:
        """Add a column to the table."""
        self.columns.append({"header": header, "style": style})
    
    def add_row(self, *values: Any) -> None:
        """Add a row to the table."""
        self.rows.append(values)
    
    @classmethod
    def grid(cls, padding: tuple[int, int] = (0, 1), **kwargs: Any):
        """Create a grid-style table."""
        instance = cls(**kwargs)
        instance._is_grid = True
        return instance
    
    def __str__(self) -> str:
        """String representation for fallback display."""
        output: List[str] = []
        if self.title:
            output.append(f"--- {self.title} ---")
        
        if self.show_header and self.columns:
            headers = [col["header"] for col in self.columns]
            output.append(" | ".join(headers))
            output.append("-" * len(" | ".join(headers)))
        
        for row in self.rows:
            output.append(" | ".join(str(val) for val in row))
        
        return "\n".join(output)


class FallbackProgress:
    """Fallback progress implementation for operation tracking."""
    
    def __init__(self, *columns: Any, **kwargs: Any):
        self.columns: tuple[Any, ...] = columns
        self.tasks: dict[int, dict[str, Any]] = {}
        self.task_counter = 0
    
    def add_task(self, description: str, total: Optional[float] = None, **kwargs: Any):
        """Add a progress task."""
        task_id = self.task_counter
        self.tasks[task_id] = {
            "description": description,
            "total": total,
            "completed": 0
        }
        self.task_counter += 1
        typer.echo(f"Starting: {description}")
        return task_id
    
    def update(self, task_id: int, completed: Optional[float] = None, 
               advance: Optional[float] = None, **kwargs: Any):
        """Update task progress."""
        if task_id in self.tasks:
            if advance:
                self.tasks[task_id]["completed"] += advance
            elif completed is not None:
                self.tasks[task_id]["completed"] = completed
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        for task in self.tasks.values():
            typer.echo(f"Completed: {task['description']}")


# Fallback implementations for other Rich components
class FallbackSpinnerColumn:
    def __init__(self, *args: Any, **kwargs: Any):
        pass

class FallbackTextColumn:
    def __init__(self, *args: Any, **kwargs: Any):
        pass

class FallbackBarColumn:
    def __init__(self, *args: Any, **kwargs: Any):
        pass

class FallbackTimeElapsedColumn:
    def __init__(self, *args: Any, **kwargs: Any):
        pass

class FallbackSyntax:
    """Fallback syntax highlighting implementation."""
    
    def __init__(self, code: str, lexer: str, theme: str = "default", 
                line_numbers: bool = False, word_wrap: bool = False, **kwargs: Any):
        self.code = code
        self.lexer = lexer
        self.theme = theme
        self.line_numbers = line_numbers
        self.word_wrap = word_wrap
    
    def __str__(self) -> str:
        """Return code without syntax highlighting."""
        if self.line_numbers:
            lines = self.code.split('\n')
            numbered_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            return '\n'.join(numbered_lines)
        return self.code
    
    def __rich_console__(self, console: Any, options: Any):
        """Rich console compatibility method for FallbackSyntax."""
        yield self.__str__()

class FallbackMarkdown:
    """Fallback markdown implementation."""
    
    def __init__(self, content: str, **kwargs: Any):
        self.content = content
    
    def __str__(self) -> str:
        """Return plain text without markdown formatting."""
        # Basic markdown removal for fallback
        import re
        text = self.content
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'`(.*?)`', r'\1', text)        # Code
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)  # Headers
        return text

class FallbackText:
    """Fallback text implementation."""
    
    def __init__(self, text: str = "", style: str = "", **kwargs: Any):
        self.text = text
        self.style = style
    
    def __str__(self) -> str:
        return self.text

class FallbackPrompt:
    """Fallback prompt implementation."""
    
    @staticmethod
    def ask(question: str, default: Any = None, **kwargs: Any) -> str:
        """Ask user for input with fallback prompt."""
        if default:
            return typer.prompt(f"{question} [{default}]", default=default)
        return typer.prompt(question)

class FallbackConfirm:
    """Fallback confirmation implementation."""
    
    @staticmethod
    def ask(question: str, default: bool = False, **kwargs: Any) -> bool:
        """Ask user for confirmation with fallback prompt."""
        return typer.confirm(question, default=default)


# Global console instance for easy importing
console_manager = ConsoleManager()
console = console_manager.console

# Export commonly used components
Panel = console_manager.Panel
Table = console_manager.Table
Progress = console_manager.Progress
Syntax = console_manager.Syntax
Markdown = console_manager.Markdown
Prompt = console_manager.Prompt
Confirm = console_manager.Confirm

# Export Rich availability flag
__all__ = [
    'RICH_AVAILABLE',
    'console',
    'console_manager',
    'Panel',
    'Table', 
    'Progress',
    'Syntax',
    'Markdown',
    'Prompt',
    'Confirm',
    'SpinnerColumn',
    'TextColumn',
    'BarColumn',
    'TimeElapsedColumn'
]