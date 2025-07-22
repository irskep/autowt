"""Cleanup worktrees command."""

import logging
from pathlib import Path

try:
    from autowt.tui.cleanup import run_cleanup_tui

    HAS_CLEANUP_TUI = True
except ImportError:
    HAS_CLEANUP_TUI = False

from autowt.config import get_config_loader
from autowt.hooks import HookRunner, HookType, extract_hook_scripts
from autowt.models import BranchStatus, CleanupCommand, CleanupMode, Services
from autowt.prompts import confirm_default_no, confirm_default_yes

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


def cleanup_worktrees(cleanup_cmd: CleanupCommand, services: Services) -> None:
    """Clean up worktrees based on the specified mode."""
    logger.debug(f"Cleaning up worktrees with mode: {cleanup_cmd.mode}")

    # Find git repository
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print("Error: Not in a git repository")
        return

    # Load config (still needed for other settings)
    config = services.state.load_config(project_dir=repo_path)

    print("Fetching branches...")
    if not services.git.fetch_branches(repo_path):
        print("Warning: Failed to fetch latest branches")

    print("Checking branch status...")

    # Get worktrees and analyze them
    worktrees = services.git.list_worktrees(repo_path)
    if not worktrees:
        print("No worktrees found.")
        return

    # Filter out primary clone and any primary worktrees
    worktrees = [wt for wt in worktrees if wt.path != repo_path and not wt.is_primary]
    if not worktrees:
        print("No secondary worktrees found.")
        return

    # Analyze branches
    branch_statuses = services.git.analyze_branches_for_cleanup(repo_path, worktrees)

    # Categorize branches
    remoteless_branches = [bs for bs in branch_statuses if not bs.has_remote]
    identical_branches = [bs for bs in branch_statuses if bs.is_identical]
    merged_branches = [bs for bs in branch_statuses if bs.is_merged]

    # Display status
    _display_branch_status(remoteless_branches, identical_branches, merged_branches)

    # Determine what to clean up based on mode
    to_cleanup = _select_branches_for_cleanup(
        cleanup_cmd.mode,
        branch_statuses,
        remoteless_branches,
        identical_branches,
        merged_branches,
    )
    if not to_cleanup:
        print("No worktrees selected for cleanup.")
        return

    # Show what will be cleaned up and confirm
    if not _confirm_cleanup(to_cleanup, cleanup_cmd.mode, cleanup_cmd.dry_run):
        print("Cleanup cancelled.")
        return

    # Run pre_cleanup hooks for each worktree
    _run_pre_cleanup_hooks(to_cleanup, repo_path, config, cleanup_cmd.dry_run)

    # Check for running processes in all worktrees to be removed
    all_processes = []
    for branch_status in to_cleanup:
        processes = services.process.find_processes_in_directory(branch_status.path)
        all_processes.extend(processes)

    # Handle running processes if any are found
    if all_processes:
        # Run pre_process_kill hooks for each worktree
        _run_pre_process_kill_hooks(to_cleanup, repo_path, config, cleanup_cmd.dry_run)

        # Determine auto_kill value based on CLI flags and config
        if cleanup_cmd.kill_processes is not None:
            # CLI flag specified: --kill (True) or --no-kill (False)
            auto_kill = cleanup_cmd.kill_processes
        else:
            # No CLI flag specified: use config default, but still prompt if config says kill
            # If config says don't kill processes, auto-decline (like --no-kill)
            # If config says kill processes, prompt user (None)
            auto_kill = None if config.cleanup.kill_processes else False

        if not _handle_running_processes(
            to_cleanup, services.process, cleanup_cmd.dry_run, auto_kill
        ):
            print("Cleanup cancelled.")
            return

    # Remove worktrees and update state
    _remove_worktrees_and_update_state(
        to_cleanup,
        repo_path,
        services,
        cleanup_cmd.auto_confirm,
        cleanup_cmd.force,
        cleanup_cmd.dry_run,
    )

    # Run post_cleanup hooks for each worktree
    _run_post_cleanup_hooks(to_cleanup, repo_path, config, cleanup_cmd.dry_run)


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

    def _filter_clean_worktrees(branches: list[BranchStatus]) -> list[BranchStatus]:
        """Filter out worktrees with uncommitted changes."""
        clean_branches = [b for b in branches if not b.has_uncommitted_changes]
        dirty_count = len(branches) - len(clean_branches)
        if dirty_count > 0:
            print(f"Skipping {dirty_count} worktree(s) with uncommitted changes")
        return clean_branches

    if mode == CleanupMode.ALL:
        # Combine and deduplicate by branch name
        all_branches = remoteless_branches + identical_branches + merged_branches
        seen_branches = set()
        to_cleanup = []
        for branch_status in all_branches:
            if branch_status.branch not in seen_branches:
                to_cleanup.append(branch_status)
                seen_branches.add(branch_status.branch)
        return _filter_clean_worktrees(to_cleanup)
    elif mode == CleanupMode.REMOTELESS:
        return _filter_clean_worktrees(remoteless_branches)
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
        return _filter_clean_worktrees(to_cleanup)
    elif mode == CleanupMode.INTERACTIVE:
        # Interactive mode shows all worktrees including those with uncommitted changes
        # Users can make informed decisions about what to clean up
        return _interactive_selection(all_statuses)
    else:
        print(f"Unknown cleanup mode: {mode}")
        return []


def _confirm_cleanup(
    to_cleanup: list[BranchStatus], mode: CleanupMode, dry_run: bool = False
) -> bool:
    """Show what will be cleaned up and get user confirmation."""
    dry_run_prefix = "[DRY RUN] " if dry_run else ""

    print(f"\n{dry_run_prefix}Worktrees to be removed:")
    for branch_status in to_cleanup:
        display_path = _format_path_for_display(branch_status.path)
        print(f"- {branch_status.branch} ({display_path})")
    print()

    # Interactive mode already confirmed during selection
    if mode == CleanupMode.INTERACTIVE:
        return True

    prompt = f"Proceed with {'dry run' if dry_run else 'cleanup'}?"
    return confirm_default_yes(prompt)


def _handle_running_processes(
    to_cleanup: list[BranchStatus],
    process_service,
    dry_run: bool = False,
    auto_kill: bool | None = None,
) -> bool:
    """Handle processes running in worktrees to be removed."""
    all_processes = []
    for branch_status in to_cleanup:
        processes = process_service.find_processes_in_directory(branch_status.path)
        all_processes.extend(processes)

    if not all_processes:
        return True

    dry_run_prefix = "[DRY RUN] " if dry_run else ""

    # Show list of processes that will be terminated
    print(
        f"\n{dry_run_prefix}Found {len(all_processes)} running processes in worktrees to be removed:"
    )
    for process in all_processes:
        # Truncate long command lines for display
        command = process.command
        if len(command) > 80:
            command = command[:77] + "..."
        print(f"  PID {process.pid}: {command}")
        print(f"    Working directory: {process.working_dir}")

    # Determine whether to terminate processes based on auto_kill parameter
    if auto_kill is True:
        # --kill flag: automatically proceed with termination
        proceed_with_termination = True
        print(f"\n{dry_run_prefix}Terminating processes (--kill flag specified)...")
    elif auto_kill is False:
        # --no-kill flag: automatically skip termination
        proceed_with_termination = False
        print(
            f"{dry_run_prefix}Skipping process termination (--no-kill flag specified)."
        )
    else:
        # No flag: ask user for confirmation before killing processes (even in dry-run)
        proceed_with_termination = confirm_default_yes(
            f"\nTerminate these {len(all_processes)} processes?"
        )
        if not proceed_with_termination:
            print(f"{dry_run_prefix}Process termination cancelled.")

    if not proceed_with_termination:
        # For --no-kill case or user declining termination, ask if they want to continue anyway
        if auto_kill is False:
            print("Warning: Processes are still running in worktrees to be removed")
            return confirm_default_no("Continue with cleanup anyway?")
        else:
            return False

    if dry_run:
        # In dry-run mode, simulate the termination
        print(f"{dry_run_prefix}Would terminate these {len(all_processes)} processes")
        return True
    else:
        # Real execution - actually terminate processes
        if process_service.terminate_processes(all_processes):
            return True

        print("Warning: Some processes could not be terminated")
        return confirm_default_no("Continue with cleanup anyway?")


def _remove_worktrees_and_update_state(
    to_cleanup: list[BranchStatus],
    repo_path: Path,
    services: Services,
    auto_confirm: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Remove worktrees and update application state."""
    dry_run_prefix = "[DRY RUN] " if dry_run else ""
    print(f"{dry_run_prefix}Removing worktrees...")
    removed_count = 0
    successfully_removed_branches = []

    for branch_status in to_cleanup:
        if dry_run:
            # Simulate successful removal in dry-run mode
            print(f"{dry_run_prefix}✓ Would remove {branch_status.branch}")
            removed_count += 1
            successfully_removed_branches.append(branch_status.branch)
        else:
            # Real execution
            if services.git.remove_worktree(
                repo_path, branch_status.path, force=force, interactive=not auto_confirm
            ):
                print(f"✓ Removed {branch_status.branch}")
                removed_count += 1
                successfully_removed_branches.append(branch_status.branch)
            else:
                print(f"✗ Failed to remove {branch_status.branch}")

    # Delete local branches for successfully removed worktrees
    deleted_branches = 0
    if successfully_removed_branches:
        should_delete_branches = auto_confirm

        if not auto_confirm:
            print(f"\n{dry_run_prefix}The following local branches will be deleted:")
            for branch in successfully_removed_branches:
                print(f"  - {branch}")

            prompt = (
                f"{'Simulate deleting' if dry_run else 'Delete'} these local branches?"
            )
            should_delete_branches = confirm_default_yes(prompt)

        if should_delete_branches:
            print(f"{dry_run_prefix}Deleting local branches...")
            for branch in successfully_removed_branches:
                if dry_run:
                    # Simulate successful branch deletion in dry-run mode
                    print(f"{dry_run_prefix}✓ Would delete branch {branch}")
                    deleted_branches += 1
                else:
                    # Real execution
                    if services.git.delete_branch(repo_path, branch, force=True):
                        print(f"✓ Deleted branch {branch}")
                        deleted_branches += 1
                    else:
                        print(f"✗ Failed to delete branch {branch}")
        else:
            print(f"{dry_run_prefix}Skipped branch deletion.")

    # Update state if we removed any worktrees
    if removed_count == 0:
        print(f"\n{dry_run_prefix}Cleanup complete. No worktrees were removed.")
        return

    if dry_run:
        # In dry-run mode, simulate state updates but don't actually modify files
        print(
            f"\n{dry_run_prefix}Would update state.toml to remove {removed_count} worktrees"
        )
        removed_branches = {bs.branch for bs in to_cleanup}
        if any(
            bs.branch == "current_worktree_name" for bs in to_cleanup
        ):  # This is just for simulation
            print(f"{dry_run_prefix}Would clear current worktree setting")
        print(f"{dry_run_prefix}Would update session IDs for removed branches")
    else:
        # Real execution - update session IDs
        removed_branches = {bs.branch for bs in to_cleanup}
        for branch in removed_branches:
            services.state.remove_session_id(repo_path, branch)

        print("Session IDs updated")

    summary = f"\n{dry_run_prefix}Cleanup complete. {'Would remove' if dry_run else 'Removed'} {removed_count} worktrees"
    if deleted_branches > 0:
        summary += f" and {'would delete' if dry_run else 'deleted'} {deleted_branches} local branches"
    summary += "."
    print(summary)


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


def _run_pre_cleanup_hooks(
    to_cleanup: list[BranchStatus],
    repo_path: Path,
    config,
    dry_run: bool = False,
) -> None:
    """Run pre_cleanup hooks for worktrees being cleaned up."""
    if dry_run:
        print("[DRY RUN] Would run pre_cleanup hooks")
        return

    # Load both global and project configurations to run both sets of hooks
    hook_runner = HookRunner()

    # Get global config by loading without project dir

    loader = get_config_loader()
    global_config = loader.load_config(project_dir=None)

    for branch_status in to_cleanup:
        global_scripts, project_scripts = extract_hook_scripts(
            global_config, config, HookType.PRE_CLEANUP
        )

        if global_scripts or project_scripts:
            print(f"Running pre_cleanup hooks for {branch_status.branch}")
            hook_runner.run_hooks(
                global_scripts,
                project_scripts,
                HookType.PRE_CLEANUP,
                branch_status.path,
                repo_path,
                branch_status.branch,
            )


def _run_pre_process_kill_hooks(
    to_cleanup: list[BranchStatus],
    repo_path: Path,
    config,
    dry_run: bool = False,
) -> None:
    """Run pre_process_kill hooks for worktrees being cleaned up."""
    if dry_run:
        print("[DRY RUN] Would run pre_process_kill hooks")
        return

    # Load both global and project configurations to run both sets of hooks
    hook_runner = HookRunner()

    # Get global config by loading without project dir

    loader = get_config_loader()
    global_config = loader.load_config(project_dir=None)

    for branch_status in to_cleanup:
        global_scripts, project_scripts = extract_hook_scripts(
            global_config, config, HookType.PRE_PROCESS_KILL
        )

        if global_scripts or project_scripts:
            print(f"Running pre_process_kill hooks for {branch_status.branch}")
            hook_runner.run_hooks(
                global_scripts,
                project_scripts,
                HookType.PRE_PROCESS_KILL,
                branch_status.path,
                repo_path,
                branch_status.branch,
            )


def _run_post_cleanup_hooks(
    to_cleanup: list[BranchStatus],
    repo_path: Path,
    config,
    dry_run: bool = False,
) -> None:
    """Run post_cleanup hooks for worktrees that were cleaned up."""
    if dry_run:
        print("[DRY RUN] Would run post_cleanup hooks")
        return

    # Load both global and project configurations to run both sets of hooks
    hook_runner = HookRunner()

    # Get global config by loading without project dir

    loader = get_config_loader()
    global_config = loader.load_config(project_dir=None)

    for branch_status in to_cleanup:
        global_scripts, project_scripts = extract_hook_scripts(
            global_config, config, HookType.POST_CLEANUP
        )

        if global_scripts or project_scripts:
            print(f"Running post_cleanup hooks for {branch_status.branch}")
            # Note: For post_cleanup hooks, the worktree_dir might no longer exist
            # But we still pass it as hooks may need the path information
            hook_runner.run_hooks(
                global_scripts,
                project_scripts,
                HookType.POST_CLEANUP,
                branch_status.path,
                repo_path,
                branch_status.branch,
            )
