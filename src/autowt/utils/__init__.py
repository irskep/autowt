"""Utility functions for autowt."""

import logging
import os
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


def apply_branch_prefix(
    branch: str, prefix_template: str | None, template_context: dict[str, str]
) -> str:
    """Apply prefix template to branch name with variable substitution.

    Args:
        branch: The branch name to prefix
        prefix_template: Template string for the prefix (e.g., "feature/", "{github_username}/")
        template_context: Dictionary of template variables (e.g., {"github_username": "alice"})

    Returns:
        The branch name with prefix applied, or unchanged if no prefix configured

    Examples:
        >>> apply_branch_prefix("my-branch", "feature/", {})
        "feature/my-branch"
        >>> apply_branch_prefix("my-branch", "{github_username}/", {"github_username": "alice"})
        "alice/my-branch"
        >>> apply_branch_prefix("feature/my-branch", "feature/", {})
        "feature/my-branch"  # No double-prefix
    """
    if not prefix_template:
        return branch

    # Replace template variables
    try:
        prefix = prefix_template.format(**template_context)
    except KeyError as e:
        # If a template variable is missing, log and return branch unchanged
        logging.getLogger(__name__).warning(
            f"Template variable {e} not found in context, skipping prefix"
        )
        return branch

    # Expand environment variables
    prefix = os.path.expandvars(prefix)

    # Avoid double-prefixing
    if branch.startswith(prefix):
        return branch

    return f"{prefix}{branch}"


def build_branch_template_context(
    repo_path: Path, services: "Services"
) -> dict[str, str]:
    """Build template context for branch prefix expansion.

    Returns dictionary with available template variables:
    - repo_name: Repository directory name
    - github_username: GitHub username if gh CLI is available and authenticated
    """
    repo_name = repo_path.name
    context = {"repo_name": repo_name}

    github_username = services.github.get_github_username()
    if github_username:
        context["github_username"] = github_username

    return context


def get_canonical_branch_name(
    branch: str,
    branch_prefix: str | None,
    worktrees: list,
    repo_path: Path,
    services: "Services",
    apply_to_new_branches: bool = True,
) -> str:
    """Get the canonical branch name, applying configured prefix if appropriate.

    Args:
        apply_to_new_branches: If True, apply prefix even for new branches.
                               If False, only use prefix if that branch already exists.

    Returns the prefixed branch name if:
    - The exact branch doesn't exist, AND
    - Either the prefixed branch exists, OR apply_to_new_branches is True
    """
    if not branch_prefix:
        return branch

    exact_match_exists = any(wt.branch == branch for wt in worktrees)
    if exact_match_exists:
        return branch

    template_context = build_branch_template_context(repo_path, services)
    prefixed_branch = apply_branch_prefix(branch, branch_prefix, template_context)

    prefixed_match_exists = any(wt.branch == prefixed_branch for wt in worktrees)

    if prefixed_match_exists or (apply_to_new_branches and prefixed_branch != branch):
        logging.getLogger(__name__).debug(
            f"Applied branch prefix: {branch} -> {prefixed_branch}"
        )
        return prefixed_branch

    return branch


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


def resolve_worktree_argument(input_str: str, services: "Services") -> str:
    """Resolve worktree argument as either a branch name or a worktree path.

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
