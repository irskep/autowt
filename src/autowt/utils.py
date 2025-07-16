"""Utility functions for autowt."""

import logging
import shlex
import subprocess
from pathlib import Path

# Special logger for command execution
command_logger = logging.getLogger("autowt.commands")


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

        # Log result at debug level
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
    command_logger.info(f"> {cmd_str}")

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
    level = logging.INFO if not debug else logging.DEBUG

    # Create handler for command logger
    handler = logging.StreamHandler()
    handler.setLevel(level)

    # Format just the message for command output
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    # Configure command logger
    command_logger.setLevel(level)
    command_logger.addHandler(handler)
    command_logger.propagate = False  # Don't propagate to root logger
