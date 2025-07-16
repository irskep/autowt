"""List worktrees command."""

import logging
from pathlib import Path

from autowt.services.git import GitService
from autowt.services.process import ProcessService
from autowt.services.state import StateService
from autowt.services.terminal import TerminalService

logger = logging.getLogger(__name__)


def list_worktrees(
    state_service: StateService,
    git_service: GitService,
    terminal_service: TerminalService,
    process_service: ProcessService,
) -> None:
    """List all worktrees and their status."""
    logger.debug("Listing worktrees")

    # Find git repository
    repo_path = git_service.find_repo_root()
    if not repo_path:
        print("Error: Not in a git repository")
        return

    # Get current directory to determine which worktree we're in
    current_path = Path.cwd()

    # Load state and get worktrees from git
    state_service.load_state(repo_path)  # Ensure state file exists
    git_worktrees = git_service.list_worktrees(repo_path)

    # Load session IDs
    session_ids = state_service.load_session_ids()

    print(f"  Primary clone: {repo_path}")

    # Determine current location
    current_location = "main clone"
    for worktree in git_worktrees:
        try:
            if current_path.is_relative_to(worktree.path):
                # If we're in the main repo path, keep it as "main clone"
                if worktree.path == repo_path:
                    current_location = "main clone"
                else:
                    current_location = worktree.branch
                break
        except ValueError:
            # is_relative_to raises ValueError if not relative
            continue

    print(f"  You are in: {current_location}")
    print()

    if not git_worktrees:
        print("  No worktrees found.")
        return

    print("  Branches:")

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

        print(f"  {branch:<20} {display_path}{session_indicator}")

    print()
    print("Use 'autowt <branch>' to switch to a worktree or create a new one.")
