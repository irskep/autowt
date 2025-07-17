"""List worktrees command."""

import logging
from pathlib import Path

from autowt.console import print_error, print_plain, print_section
from autowt.models import Services

logger = logging.getLogger(__name__)


def list_worktrees(services: Services) -> None:
    """List all worktrees and their status."""
    logger.debug("Listing worktrees")

    # Find git repository
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print_error("Error: Not in a git repository")
        return

    # Get current directory to determine which worktree we're in
    current_path = Path.cwd()

    # Load state and get worktrees from git
    services.state.load_state(repo_path)  # Ensure state file exists
    git_worktrees = services.git.list_worktrees(repo_path)

    # Load session IDs
    session_ids = services.state.load_session_ids()

    # Find the primary clone path
    primary_clone_path = repo_path
    for worktree in git_worktrees:
        if worktree.is_primary:
            primary_clone_path = worktree.path
            break

    print_plain(f"  Primary clone: {primary_clone_path}")

    # Determine current location
    current_location = "main clone"
    for worktree in git_worktrees:
        try:
            if current_path.is_relative_to(worktree.path):
                # If we're in the primary worktree, it's the main clone
                if worktree.is_primary:
                    current_location = "main clone"
                else:
                    current_location = worktree.branch
                break
        except ValueError:
            # is_relative_to raises ValueError if not relative
            continue

    print_plain(f"  You are in: {current_location}")
    print_plain("")

    if not git_worktrees:
        print_plain("  No worktrees found.")
        return

    print_section("  Branches:")

    # Sort worktrees by branch name for consistent output
    sorted_worktrees = sorted(git_worktrees, key=lambda w: w.branch)

    for worktree in sorted_worktrees:
        # Skip the main worktree (primary clone)
        if worktree.path == repo_path:
            continue

        branch = worktree.branch
        path = worktree.path

        # Shorten path for display
        try:
            # Try to make it relative to home directory
            relative_path = path.relative_to(Path.home())
            display_path = f"~/{relative_path}"
        except ValueError:
            display_path = str(path)

        # Check if this branch has a session ID
        session_indicator = ""
        if branch in session_ids:
            session_indicator = " 💻"  # Laptop icon to indicate active session

        print_plain(f"  {branch:<20} {display_path}{session_indicator}")

    print_plain("")
    print_plain("Use 'autowt <branch>' to switch to a worktree or create a new one.")
