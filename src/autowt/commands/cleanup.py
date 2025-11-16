"""Cleanup worktrees command."""

import logging
from pathlib import Path

try:
    from autowt.tui.cleanup import run_cleanup_tui

    HAS_CLEANUP_TUI = True
except ImportError:
    HAS_CLEANUP_TUI = False

from autowt.console import print_error, print_info, print_success
from autowt.hooks import HookType, extract_hook_scripts
from autowt.models import BranchStatus, CleanupCommand, CleanupMode, Services
from autowt.prompts import confirm_default_no, confirm_default_yes
from autowt.utils import (
    get_canonical_branch_name,
    is_interactive_terminal,
    resolve_worktree_argument,
)

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
        print_error("Not in a git repository")
        return

    # Load config (still needed for other settings)
    config = services.state.load_config(project_dir=repo_path)

    # For GitHub mode, check gh availability early
    if cleanup_cmd.mode == CleanupMode.GITHUB:
        try:
            # This will raise RuntimeError if gh is not available
            services.github.analyze_branches_for_cleanup(repo_path, [], services.git)
        except RuntimeError as e:
            print_error(str(e))
            return

    print_info("Fetching branches...")
    if not services.git.fetch_branches(repo_path):
        print_info("Warning: Failed to fetch latest branches")

    print_info("Checking branch status...")

    # Get worktrees and analyze them
    worktrees = services.git.list_worktrees(repo_path)
    if not worktrees:
        print_info("No worktrees found.")
        return

    # Filter out primary clone and any primary worktrees
    worktrees = [wt for wt in worktrees if wt.path != repo_path and not wt.is_primary]
    if not worktrees:
        print_info("No secondary worktrees found.")
        return

    # If specific worktrees were provided, handle them directly
    if cleanup_cmd.worktrees:
        # Resolve each worktree arg to a branch name
        resolved_branches = []
        for wt_arg in cleanup_cmd.worktrees:
            try:
                branch = resolve_worktree_argument(wt_arg, services)
                canonical_branch = get_canonical_branch_name(
                    branch,
                    config.worktree.branch_prefix,
                    worktrees,
                    repo_path,
                    services,
                    apply_to_new_branches=False,
                )
                resolved_branches.append(canonical_branch)
            except ValueError as e:
                print_error(str(e))
                return

        # Filter worktrees to only the ones specified
        worktrees = [wt for wt in worktrees if wt.branch in resolved_branches]
        if not worktrees:
            print_error("None of the specified worktrees were found.")
            return

        # Get branch statuses for the specified worktrees
        branch_statuses = services.git.analyze_branches_for_cleanup(
            repo_path, worktrees
        )

        # Show confirmation and proceed
        if not _confirm_cleanup(
            branch_statuses,
            cleanup_cmd.mode,
            cleanup_cmd.dry_run,
            cleanup_cmd.auto_confirm,
        ):
            print_info("Cleanup cancelled.")
            return

        # Run pre_cleanup hooks for each worktree
        _run_pre_cleanup_hooks(
            services, branch_statuses, repo_path, config, cleanup_cmd.dry_run
        )

        # Remove worktrees and update state
        _remove_worktrees_and_update_state(
            branch_statuses,
            repo_path,
            services,
            cleanup_cmd.auto_confirm,
            cleanup_cmd.force,
            cleanup_cmd.dry_run,
        )

        # Run post_cleanup hooks for each worktree
        _run_post_cleanup_hooks(
            services, branch_statuses, repo_path, config, cleanup_cmd.dry_run
        )

        return

    # Analyze branches
    if cleanup_cmd.mode == CleanupMode.GITHUB:
        branch_statuses = services.github.analyze_branches_for_cleanup(
            repo_path, worktrees, services.git
        )
    else:
        branch_statuses = services.git.analyze_branches_for_cleanup(
            repo_path, worktrees
        )

    # Categorize branches
    if cleanup_cmd.mode == CleanupMode.GITHUB:
        # For GitHub mode, categorize based on PR status
        github_merged_branches = [bs for bs in branch_statuses if bs.is_merged]
        github_open_branches = [bs for bs in branch_statuses if not bs.is_merged]

        # Display GitHub-specific status
        if github_merged_branches:
            print_info("Branches with merged or closed PRs:")
            for branch_status in github_merged_branches:
                print(f"- {branch_status.branch}")
            print()

        if github_open_branches:
            print_info("Branches with open or no PRs (will be kept):")
            for branch_status in github_open_branches:
                print(f"- {branch_status.branch}")
            print()

        remoteless_branches = []
        identical_branches = []
        merged_branches = github_merged_branches
    else:
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
        # If not in interactive mode, in a TTY, and not auto-confirming,
        # offer to enter interactive mode
        if (
            cleanup_cmd.mode != CleanupMode.INTERACTIVE
            and is_interactive_terminal()
            and not cleanup_cmd.auto_confirm
        ):
            if confirm_default_no(
                "No branches found for cleanup. Enter interactive mode?"
            ):
                # Enter interactive mode with all branch statuses
                to_cleanup = _interactive_selection(branch_statuses)
                if not to_cleanup:
                    print_info("No worktrees selected for cleanup.")
                    return
            else:
                print_info("No worktrees selected for cleanup.")
                return
        else:
            print_info("No worktrees selected for cleanup.")
            return

    # Show what will be cleaned up and confirm
    if not _confirm_cleanup(
        to_cleanup, cleanup_cmd.mode, cleanup_cmd.dry_run, cleanup_cmd.auto_confirm
    ):
        print_info("Cleanup cancelled.")
        return

    # Run pre_cleanup hooks for each worktree
    _run_pre_cleanup_hooks(services, to_cleanup, repo_path, config, cleanup_cmd.dry_run)

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
    _run_post_cleanup_hooks(
        services, to_cleanup, repo_path, config, cleanup_cmd.dry_run
    )


def _display_branch_status(
    remoteless_branches: list[BranchStatus],
    identical_branches: list[BranchStatus],
    merged_branches: list[BranchStatus],
) -> None:
    """Display the status of branches for cleanup."""
    if remoteless_branches:
        print_info("Branches without remotes:")
        for branch_status in remoteless_branches:
            print(f"- {branch_status.branch}")
        print()

    if identical_branches:
        print_info("Branches identical to main:")
        for branch_status in identical_branches:
            print(f"- {branch_status.branch}")
        print()

    if merged_branches:
        print_info("Branches that were merged:")
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
            print_info(f"Skipping {dirty_count} worktree(s) with uncommitted changes")
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
    elif mode == CleanupMode.GITHUB:
        # For GitHub mode, use branches marked as merged (which are those with merged/closed PRs)
        return _filter_clean_worktrees(merged_branches)
    elif mode == CleanupMode.INTERACTIVE:
        # Interactive mode shows all worktrees including those with uncommitted changes
        # Users can make informed decisions about what to clean up
        return _interactive_selection(all_statuses)
    else:
        print_error(f"Unknown cleanup mode: {mode}")
        return []


def _confirm_cleanup(
    to_cleanup: list[BranchStatus],
    mode: CleanupMode,
    dry_run: bool = False,
    auto_confirm: bool = False,
) -> bool:
    """Show what will be cleaned up and get user confirmation."""
    dry_run_prefix = "[DRY RUN] " if dry_run else ""

    print_info(f"\n{dry_run_prefix}Worktrees to be removed:")
    for branch_status in to_cleanup:
        display_path = _format_path_for_display(branch_status.path)
        print(f"- {branch_status.branch} ({display_path})")
    print()

    # Interactive mode already confirmed during selection
    if mode == CleanupMode.INTERACTIVE:
        return True

    # Skip confirmation if auto_confirm is set (from -y flag)
    if auto_confirm:
        return True

    prompt = f"Proceed with {'dry run' if dry_run else 'cleanup'}?"
    return confirm_default_yes(prompt)


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
    print_info(f"{dry_run_prefix}Removing worktrees...")
    removed_count = 0
    successfully_removed_branches = []

    for branch_status in to_cleanup:
        if dry_run:
            # Simulate successful removal in dry-run mode
            print_info(f"{dry_run_prefix}✓ Would remove {branch_status.branch}")
            removed_count += 1
            successfully_removed_branches.append(branch_status.branch)
        else:
            # Real execution
            if services.git.remove_worktree(
                repo_path, branch_status.path, force=force, interactive=not auto_confirm
            ):
                print_success(f"✓ Removed {branch_status.branch}")
                removed_count += 1
                successfully_removed_branches.append(branch_status.branch)
            else:
                print_error(f"✗ Failed to remove {branch_status.branch}")

    # Delete local branches for successfully removed worktrees
    deleted_branches = 0
    if successfully_removed_branches:
        should_delete_branches = auto_confirm

        if not auto_confirm:
            print_info(
                f"\n{dry_run_prefix}The following local branches will be deleted:"
            )
            for branch in successfully_removed_branches:
                print(f"  - {branch}")

            prompt = (
                f"{'Simulate deleting' if dry_run else 'Delete'} these local branches?"
            )
            should_delete_branches = confirm_default_yes(prompt)

        if should_delete_branches:
            print_info(f"{dry_run_prefix}Deleting local branches...")
            for branch in successfully_removed_branches:
                if dry_run:
                    # Simulate successful branch deletion in dry-run mode
                    print_info(f"{dry_run_prefix}✓ Would delete branch {branch}")
                    deleted_branches += 1
                else:
                    # Real execution
                    if services.git.delete_branch(repo_path, branch, force=True):
                        print_success(f"✓ Deleted branch {branch}")
                        deleted_branches += 1
                    else:
                        print_error(f"✗ Failed to delete branch {branch}")
        else:
            print_info(f"{dry_run_prefix}Skipped branch deletion.")

    # Update state if we removed any worktrees
    if removed_count == 0:
        print_info(f"\n{dry_run_prefix}Cleanup complete. No worktrees were removed.")
        return

    summary = f"\n{dry_run_prefix}Cleanup complete. {'Would remove' if dry_run else 'Removed'} {removed_count} worktrees"
    if deleted_branches > 0:
        summary += f" and {'would delete' if dry_run else 'deleted'} {deleted_branches} local branches"
    summary += "."
    print_success(summary)


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
    print_info("\nInteractive cleanup mode")
    print_info("Select worktrees to remove:")
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
        print_info(f"\nSelected {len(selected)} worktrees for removal.")

    return selected


def _run_pre_cleanup_hooks(
    services: Services,
    to_cleanup: list[BranchStatus],
    repo_path: Path,
    config,
    dry_run: bool = False,
) -> None:
    """Run pre_cleanup hooks for worktrees being cleaned up."""
    if dry_run:
        print_info("[DRY RUN] Would run pre_cleanup hooks")
        return

    global_config = services.config_loader.load_config(project_dir=None)
    global_scripts, project_scripts = extract_hook_scripts(
        global_config, config, HookType.PRE_CLEANUP
    )

    if not global_scripts and not project_scripts:
        return

    for branch_status in to_cleanup:
        print_info(f"Running pre_cleanup hooks for {branch_status.branch}")
        services.hooks.run_hooks(
            global_scripts,
            project_scripts,
            HookType.PRE_CLEANUP,
            branch_status.path,
            repo_path,
            branch_status.branch,
        )


def _run_post_cleanup_hooks(
    services: Services,
    to_cleanup: list[BranchStatus],
    repo_path: Path,
    config,
    dry_run: bool = False,
) -> None:
    """Run post_cleanup hooks for worktrees that were cleaned up."""
    if dry_run:
        print_info("[DRY RUN] Would run post_cleanup hooks")
        return

    global_config = services.config_loader.load_config(project_dir=None)
    global_scripts, project_scripts = extract_hook_scripts(
        global_config, config, HookType.POST_CLEANUP
    )

    if not global_scripts and not project_scripts:
        return

    for branch_status in to_cleanup:
        print_info(f"Running post_cleanup hooks for {branch_status.branch}")
        # Note: For post_cleanup hooks, the worktree_dir might no longer exist
        # But we still pass it as hooks may need the path information
        services.hooks.run_hooks(
            global_scripts,
            project_scripts,
            HookType.POST_CLEANUP,
            branch_status.path,
            repo_path,
            branch_status.branch,
        )
