"""Cleanup worktrees command."""

import logging
from pathlib import Path

try:
    from autowt.tui.cleanup import run_cleanup_tui

    HAS_CLEANUP_TUI = True
except ImportError:
    HAS_CLEANUP_TUI = False

from autowt.models import BranchStatus, CleanupMode
from autowt.prompts import confirm_default_no, confirm_default_yes
from autowt.services.git import GitService
from autowt.services.process import ProcessService
from autowt.services.state import StateService
from autowt.services.terminal import TerminalService

logger = logging.getLogger(__name__)


def _format_path_for_display(path: Path) -> str:
    """Format a path for display, making it relative to current directory if possible."""
    try:
        # Try to make it relative to current working directory
        current_dir = Path.cwd()
        relative_path = path.relative_to(current_dir)
        return str(relative_path)
    except ValueError:
        # If not relative to cwd, try to make it relative to home directory
        try:
            home_dir = Path.home()
            relative_path = path.relative_to(home_dir)
            return f"~/{relative_path}"
        except ValueError:
            # Fall back to absolute path
            return str(path)


def cleanup_worktrees(
    mode: CleanupMode,
    state_service: StateService,
    git_service: GitService,
    terminal_service: TerminalService,
    process_service: ProcessService,
    dry_run: bool = False,
) -> None:
    """Clean up worktrees based on the specified mode."""
    logger.debug(f"Cleaning up worktrees with mode: {mode}")

    # Find git repository
    repo_path = git_service.find_repo_root()
    if not repo_path:
        print("Error: Not in a git repository")
        return

    print("Checking branch status...")

    # Get worktrees and analyze them
    worktrees = git_service.list_worktrees(repo_path)
    if not worktrees:
        print("No worktrees found.")
        return

    # Filter out primary clone and any primary worktrees
    worktrees = [wt for wt in worktrees if wt.path != repo_path and not wt.is_primary]
    if not worktrees:
        print("No secondary worktrees found.")
        return

    # Analyze branches
    branch_statuses = git_service.analyze_branches_for_cleanup(repo_path, worktrees)

    # Categorize branches
    remoteless_branches = [bs for bs in branch_statuses if not bs.has_remote]
    identical_branches = [bs for bs in branch_statuses if bs.is_identical]
    merged_branches = [bs for bs in branch_statuses if bs.is_merged]

    # Display status
    _display_branch_status(remoteless_branches, identical_branches, merged_branches)

    # Determine what to clean up based on mode
    to_cleanup = _select_branches_for_cleanup(
        mode, branch_statuses, remoteless_branches, identical_branches, merged_branches
    )
    if not to_cleanup:
        print("No worktrees selected for cleanup.")
        return

    # Handle dry-run mode
    if dry_run:
        _show_dry_run_results(to_cleanup, process_service)
        return

    # Show what will be cleaned up and confirm
    if not _confirm_cleanup(to_cleanup, mode):
        print("Cleanup cancelled.")
        return

    # Handle running processes
    if not _handle_running_processes(to_cleanup, process_service):
        print("Cleanup cancelled.")
        return

    # Remove worktrees and update state
    _remove_worktrees_and_update_state(
        to_cleanup, repo_path, git_service, state_service
    )


def _display_branch_status(
    remoteless_branches: list[BranchStatus],
    identical_branches: list[BranchStatus],
    merged_branches: list[BranchStatus],
) -> None:
    """Display the status of branches for cleanup."""
    if remoteless_branches:
        print("Branches without remotes:")
        for branch_status in remoteless_branches:
            print(f"- {branch_status.branch}")
        print()

    if identical_branches:
        print("Branches identical to main:")
        for branch_status in identical_branches:
            print(f"- {branch_status.branch}")
        print()

    if merged_branches:
        print("Branches that were merged:")
        for branch_status in merged_branches:
            print(f"- {branch_status.branch}")
        print()


def _select_branches_for_cleanup(
    mode: CleanupMode,
    all_statuses: list[BranchStatus],
    remoteless_branches: list[BranchStatus],
    identical_branches: list[BranchStatus],
    merged_branches: list[BranchStatus],
) -> list[BranchStatus]:
    """Select which branches to clean up based on mode."""
    if mode == CleanupMode.ALL:
        # Combine and deduplicate by branch name
        all_branches = remoteless_branches + identical_branches + merged_branches
        seen_branches = set()
        to_cleanup = []
        for branch_status in all_branches:
            if branch_status.branch not in seen_branches:
                to_cleanup.append(branch_status)
                seen_branches.add(branch_status.branch)
        return to_cleanup
    elif mode == CleanupMode.REMOTELESS:
        return remoteless_branches
    elif mode == CleanupMode.MERGED:
        # Include both identical and merged branches for "merged" mode
        # since both are safe to remove
        combined = identical_branches + merged_branches
        seen_branches = set()
        to_cleanup = []
        for branch_status in combined:
            if branch_status.branch not in seen_branches:
                to_cleanup.append(branch_status)
                seen_branches.add(branch_status.branch)
        return to_cleanup
    elif mode == CleanupMode.INTERACTIVE:
        return _interactive_selection(all_statuses)
    else:
        print(f"Unknown cleanup mode: {mode}")
        return []


def _confirm_cleanup(to_cleanup: list[BranchStatus], mode: CleanupMode) -> bool:
    """Show what will be cleaned up and get user confirmation."""
    print("\nWorktrees to be removed:")
    for branch_status in to_cleanup:
        display_path = _format_path_for_display(branch_status.path)
        print(f"- {branch_status.branch} ({display_path})")

    # Interactive mode already confirmed during selection
    if mode == CleanupMode.INTERACTIVE:
        return True

    return confirm_default_yes("Proceed with cleanup?")


def _show_dry_run_results(
    to_cleanup: list[BranchStatus], process_service: ProcessService
) -> None:
    """Show what would be removed in dry-run mode."""
    print("\n[DRY RUN] Worktrees that would be removed:")
    for branch_status in to_cleanup:
        display_path = _format_path_for_display(branch_status.path)
        print(f"- {branch_status.branch} ({display_path})")

    print("\n[DRY RUN] Processes that would be terminated:")
    all_processes = []
    for branch_status in to_cleanup:
        processes = process_service.find_processes_in_directory(branch_status.path)
        all_processes.extend(processes)

    if all_processes:
        for process in all_processes:
            print(f"- PID {process.pid}: {process.command} (in {process.working_dir})")
    else:
        print("- No running processes found")

    print(
        f"\n[DRY RUN] Would remove {len(to_cleanup)} worktrees and terminate {len(all_processes)} processes"
    )


def _handle_running_processes(
    to_cleanup: list[BranchStatus], process_service: ProcessService
) -> bool:
    """Handle processes running in worktrees to be removed."""
    all_processes = []
    for branch_status in to_cleanup:
        processes = process_service.find_processes_in_directory(branch_status.path)
        all_processes.extend(processes)

    if not all_processes:
        return True

    process_service.print_process_summary(all_processes)
    if process_service.terminate_processes(all_processes):
        return True

    print("Warning: Some processes could not be terminated")
    return confirm_default_no("Continue with cleanup anyway?")


def _remove_worktrees_and_update_state(
    to_cleanup: list[BranchStatus],
    repo_path: Path,
    git_service: GitService,
    state_service: StateService,
) -> None:
    """Remove worktrees and update application state."""
    print("Removing worktrees...")
    removed_count = 0

    for branch_status in to_cleanup:
        if git_service.remove_worktree(repo_path, branch_status.path):
            print(f"✓ Removed {branch_status.branch}")
            removed_count += 1
        else:
            print(f"✗ Failed to remove {branch_status.branch}")

    # Update state if we removed any worktrees
    if removed_count == 0:
        print("\nCleanup complete. No worktrees were removed.")
        return

    state = state_service.load_state(repo_path)
    removed_branches = {bs.branch for bs in to_cleanup}
    state.worktrees = [
        wt for wt in state.worktrees if wt.branch not in removed_branches
    ]

    # Clear current worktree if it was removed
    if state.current_worktree in removed_branches:
        state.current_worktree = None

    state_service.save_state(state)

    # Update session IDs
    session_ids = state_service.load_session_ids()
    for branch in removed_branches:
        session_ids.pop(branch, None)
    state_service.save_session_ids(session_ids)

    print("state.toml updated")
    print(f"\nCleanup complete. Removed {removed_count} worktrees.")


def _interactive_selection(branch_statuses: list[BranchStatus]) -> list[BranchStatus]:
    """Let user interactively select which worktrees to clean up."""
    if not branch_statuses:
        return []

    # Try to use Textual TUI if available
    if HAS_CLEANUP_TUI:
        return run_cleanup_tui(branch_statuses)
    else:
        # Fall back to simple text interface
        return _simple_interactive_selection(branch_statuses)


def _simple_interactive_selection(
    branch_statuses: list[BranchStatus],
) -> list[BranchStatus]:
    """Simple text-based interactive selection."""
    print("\nInteractive cleanup mode")
    print("Select worktrees to remove:")
    print()

    selected = []

    for i, branch_status in enumerate(branch_statuses, 1):
        status_info = []
        if not branch_status.has_remote:
            status_info.append("no remote")
        if branch_status.is_merged:
            status_info.append("merged")

        status_str = f" ({', '.join(status_info)})" if status_info else ""

        if confirm_default_no(f"{i}. Remove {branch_status.branch}{status_str}?"):
            selected.append(branch_status)

    if selected:
        print(f"\nSelected {len(selected)} worktrees for removal.")

    return selected
