"""Utility functions for autowt."""

import logging
import shlex
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from autowt.console import print_command, print_info
from autowt.prompts import confirm_default_yes

if TYPE_CHECKING:
    from autowt.models import Services

# Special logger for command execution
command_logger = logging.getLogger("autowt.commands")


def is_interactive_terminal() -> bool:
    """Check if running in an interactive terminal.

    Uses the same approach as Click's internal TTY detection.
    This function can be easily mocked in tests for consistent behavior.
    """
    return sys.stdin.isatty()


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    timeout: int | None = None,
    description: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess command with debug logging only."""
    cmd_str = shlex.join(cmd)

    # Only log at debug level - this is for read-only operations
    if description:
        command_logger.debug(f"{description}: {cmd_str}")
    else:
        command_logger.debug(f"Running: {cmd_str}")

    if cwd:
        command_logger.debug(f"Working directory: {cwd}")

    # Run the command
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=capture_output, text=text, timeout=timeout
        )

        # Log result - failures are only warnings if they have stderr output
        if result.returncode == 0:
            command_logger.debug(f"Command succeeded (exit code: {result.returncode})")
        else:
            # Many commands are expected to fail (checking for existence, etc.)
            # Only warn if there's actual error output, otherwise just debug
            if result.stderr and result.stderr.strip():
                command_logger.warning(
                    f"Command failed (exit code: {result.returncode})"
                )
                command_logger.warning(f"Error output: {result.stderr.strip()}")
            else:
                command_logger.debug(
                    f"Command completed (exit code: {result.returncode})"
                )

        return result

    except subprocess.TimeoutExpired:
        command_logger.error(f"Command timed out after {timeout}s: {cmd_str}")
        raise
    except Exception as e:
        command_logger.error(f"Command failed with exception: {e}")
        raise


def run_command_visible(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess command that should be visible to the user.

    Use this for state-changing operations like create, delete, fetch, etc.
    """
    cmd_str = shlex.join(cmd)

    # Show the command with a clear prefix
    print_command(cmd_str)

    if cwd:
        command_logger.debug(f"Working directory: {cwd}")

    # Run the command
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=capture_output, text=text, timeout=timeout
        )

        # Log result
        if result.returncode == 0:
            command_logger.debug(f"Command succeeded (exit code: {result.returncode})")
        else:
            command_logger.warning(f"Command failed (exit code: {result.returncode})")
            if result.stderr:
                command_logger.warning(f"Error output: {result.stderr.strip()}")

        return result

    except subprocess.TimeoutExpired:
        command_logger.error(f"Command timed out after {timeout}s: {cmd_str}")
        raise
    except Exception as e:
        command_logger.error(f"Command failed with exception: {e}")
        raise


def run_command_quiet_on_failure(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    timeout: int | None = None,
    description: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a command that's expected to sometimes fail without stderr warnings."""
    cmd_str = shlex.join(cmd)

    # Log the command at debug level
    if description:
        command_logger.debug(f"{description}: {cmd_str}")
    else:
        command_logger.debug(f"Running: {cmd_str}")

    if cwd:
        command_logger.debug(f"Working directory: {cwd}")

    # Run the command
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=capture_output, text=text, timeout=timeout
        )

        # Log result at debug level only
        if result.returncode == 0:
            command_logger.debug(f"Command succeeded (exit code: {result.returncode})")
        else:
            command_logger.debug(f"Command completed (exit code: {result.returncode})")
            if result.stderr:
                command_logger.debug(f"Error output: {result.stderr.strip()}")

        return result

    except subprocess.TimeoutExpired:
        command_logger.error(f"Command timed out after {timeout}s: {cmd_str}")
        raise
    except Exception as e:
        command_logger.error(f"Command failed with exception: {e}")
        raise


def sanitize_branch_name(branch: str) -> str:
    """Sanitize branch name for use in filesystem paths."""
    # Replace problematic characters with hyphens
    sanitized = branch.replace("/", "-").replace(" ", "-").replace("\\", "-")

    # Remove other problematic characters
    sanitized = "".join(c for c in sanitized if c.isalnum() or c in "-_.")

    # Ensure it doesn't start or end with dots or hyphens
    sanitized = sanitized.strip(".-")

    # Ensure it's not empty
    if not sanitized:
        sanitized = "branch"

    return sanitized


def setup_command_logging(debug: bool = False) -> None:
    """Setup command logging to show subprocess execution."""
    # In debug mode, show all commands (DEBUG level)
    # In normal mode, only show visible commands (INFO level)
    level = logging.DEBUG if debug else logging.INFO

    # Only add handler if none exists yet
    if not command_logger.handlers:
        # Create handler for command logger
        handler = logging.StreamHandler()
        handler.setLevel(level)

        # Format just the message for command output
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)

        # Configure command logger
        command_logger.addHandler(handler)
        command_logger.propagate = False  # Don't propagate to root logger

    # Always update the level in case debug setting changed
    command_logger.setLevel(level)

    # Also update handler level if it exists
    if command_logger.handlers:
        command_logger.handlers[0].setLevel(level)


def resolve_branch_or_path(input_str: str, services: "Services") -> str:
    """Resolve input as either a branch name or a worktree path.

    Args:
        input_str: The user input (could be branch name or path)
        services: Services container for git operations

    Returns:
        The resolved branch name
    """
    # Check if the input exists as a path
    input_path = Path(input_str).expanduser()

    if not input_path.exists():
        # Doesn't exist as a path, treat as branch name
        return input_str

    # Path exists - check if it contains path separators
    has_path_separator = any(char in input_str for char in ["/", "\\", ".", "~"])

    if not has_path_separator:
        # Ambiguous case: exists as a directory but no path separators
        # Prompt user to clarify
        print_info(f"Directory '{input_str}' exists locally.")
        response = confirm_default_yes(
            f"Did you mean to switch to branch '{input_str}'? (no = use directory './{input_str}')"
        )
        if response:
            return input_str
        input_path = Path(f"./{input_str}")

    # Resolve to absolute path (let it raise if it fails)
    abs_path = input_path.resolve()

    # Check if it's a git worktree (has .git file, not directory)
    git_path = abs_path / ".git"
    if not git_path.exists():
        raise ValueError(f"Not a git worktree: {abs_path}")

    # Get the branch name directly using existing method
    branch = services.git.get_current_branch(abs_path)
    if not branch:
        raise ValueError(f"Could not determine branch for worktree: {abs_path}")

    return branch
