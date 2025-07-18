"""Styled console output for autowt using rich."""

from rich.console import Console
from rich.theme import Theme

from autowt.global_config import options

# Theme for consistent styling across autowt
AUTOWT_THEME = Theme(
    {
        "command": "dim grey50",  # Command strings
        "output": "dim grey50",  # Raw command output
        "prompt": "bold cyan",  # User prompts
        "section": "bold white",  # Section headers
        "success": "green",  # Success messages
        "warning": "yellow",  # Warnings
        "error": "bold red",  # Errors
        "info": "dim cyan",  # General info
    }
)

# Single console instance for the entire application
console = Console(theme=AUTOWT_THEME)


def print_command(cmd_str: str) -> None:
    """Print a command string in gray styling."""
    if not options.suppress_rich_output:
        console.print(f"> {cmd_str}", style="command")


def print_section(text: str) -> None:
    """Print a section header in bold."""
    if not options.suppress_rich_output:
        console.print(text, style="section")


def print_prompt(text: str) -> None:
    """Print a prompt in bold cyan."""
    if not options.suppress_rich_output:
        console.print(text, style="prompt")


def print_success(text: str) -> None:
    """Print a success message in green."""
    if not options.suppress_rich_output:
        console.print(text, style="success")


def print_warning(text: str) -> None:
    """Print a warning message in yellow."""
    if not options.suppress_rich_output:
        console.print(text, style="warning")


def print_error(text: str) -> None:
    """Print an error message in bold red."""
    if not options.suppress_rich_output:
        console.print(text, style="error")


def print_info(text: str) -> None:
    """Print an info message in dim cyan."""
    if not options.suppress_rich_output:
        console.print(text, style="info")


def print_output(text: str) -> None:
    """Print raw command output in gray."""
    if not options.suppress_rich_output:
        console.print(text, style="output")


def print_plain(text: str) -> None:
    """Print plain text without styling."""
    if not options.suppress_rich_output:
        console.print(text)
