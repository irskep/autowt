"""List worktrees command."""

import logging
import shutil
from pathlib import Path

from autowt.console import console, print_error, print_plain, print_section
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

    # Determine which worktree we're currently in
    current_worktree_path = None
    for worktree in git_worktrees:
        try:
            if current_path.is_relative_to(worktree.path):
                current_worktree_path = worktree.path
                break
        except ValueError:
            # is_relative_to raises ValueError if not relative
            continue

    if not git_worktrees:
        print_plain("  No worktrees found.")
        return

    print_section("  Worktrees:")

    # Sort worktrees: primary first, then by branch name
    sorted_worktrees = sorted(git_worktrees, key=lambda w: (not w.is_primary, w.branch))

    # Calculate the maximum terminal width to align branch names
    terminal_width = 80  # Default fallback
    try:
        terminal_width = shutil.get_terminal_size().columns
    except OSError:
        pass

    for worktree in sorted_worktrees:
        branch = worktree.branch
        path = worktree.path

        # Shorten path for display
        try:
            # Try to make it relative to home directory
            relative_path = path.relative_to(Path.home())
            display_path = f"~/{relative_path}"
        except ValueError:
            display_path = str(path)

        # Check if this is the current worktree
        current_indicator = "→ " if current_worktree_path == worktree.path else "  "
        branch_indicator = " ←" if current_worktree_path == worktree.path else "  "

        # Check if this branch has a session ID
        session_indicator = ""
        if branch in session_ids:
            session_indicator = " 💻"  # Laptop icon to indicate active session

        # Calculate base left part without main worktree indicator
        base_left_part = f"{current_indicator}{display_path}{session_indicator}"

        # Calculate length including main worktree indicator for alignment
        main_indicator_text = " (main worktree)" if worktree.is_primary else ""
        total_left_length = len(base_left_part) + len(main_indicator_text)

        # Calculate space needed for right alignment
        branch_with_indicator = f"{branch}{branch_indicator}"
        if total_left_length + len(branch_with_indicator) + 2 < terminal_width:
            spaces_needed = (
                terminal_width - total_left_length - len(branch_with_indicator)
            )
            # Print with styled main worktree indicator
            if worktree.is_primary:
                console.print(
                    f"{base_left_part}[dim grey50] (main worktree)[/dim grey50]{' ' * spaces_needed}{branch_with_indicator}"
                )
            else:
                print_plain(
                    f"{base_left_part}{' ' * spaces_needed}{branch_with_indicator}"
                )
        else:
            # If line would be too long, just put branch on same line with minimal spacing
            if worktree.is_primary:
                console.print(
                    f"{base_left_part}[dim grey50] (main worktree)[/dim grey50]  {branch_with_indicator}"
                )
            else:
                print_plain(f"{base_left_part}  {branch_with_indicator}")

    print_plain("")
    print_plain("Use 'autowt <branch>' to switch to a worktree or create a new one.")
