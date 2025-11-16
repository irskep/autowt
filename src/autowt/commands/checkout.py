"""Checkout/create worktree command."""

import logging
from dataclasses import replace
from pathlib import Path

from autowt.cli_config import resolve_custom_script_with_interpolation
from autowt.console import print_error, print_info, print_success
from autowt.global_config import options
from autowt.hooks import HookType, extract_hook_scripts
from autowt.models import Services, SwitchCommand, TerminalMode
from autowt.prompts import confirm_default_yes
from autowt.utils import (
    get_canonical_branch_name,
    resolve_worktree_argument,
    sanitize_branch_name,
)

logger = logging.getLogger(__name__)


def _combine_after_init_and_custom_script(
    after_init: str | None, custom_script: str | None
) -> str | None:
    """Combine after_init command with custom script."""
    scripts = []
    if after_init:
        scripts.append(after_init)
    if custom_script:
        scripts.append(custom_script)
    return "; ".join(scripts) if scripts else None


def _generate_alternative_worktree_path(base_path: Path, git_worktrees: list) -> Path:
    """Generate an alternative worktree path with suffix when base path conflicts."""
    # Extract the base name without any existing suffix
    base_name = base_path.name
    parent_dir = base_path.parent

    # Try suffixes -2, -3, -4, etc.
    suffix = 2
    while suffix <= 100:  # Reasonable upper limit
        alternative_name = f"{base_name}-{suffix}"
        alternative_path = parent_dir / alternative_name

        # Check if this alternative path conflicts with any existing worktree
        conflicts = False
        for worktree in git_worktrees:
            if worktree.path == alternative_path:
                conflicts = True
                break

        if not conflicts:
            return alternative_path

        suffix += 1

    # If we somehow can't find an alternative, return original (shouldn't happen)
    return base_path


def _prompt_for_alternative_worktree(
    original_path: Path, alternative_path: Path, conflicting_branch: str
) -> bool:
    """Prompt user to confirm using an alternative worktree path."""
    print_info(
        f"That branch's original worktree is now on a different branch ('{conflicting_branch}')"
    )
    return confirm_default_yes(f"Create a new worktree at {alternative_path}?")


def checkout_branch(switch_cmd: SwitchCommand, services: Services) -> None:
    """Switch to or create a worktree for the specified branch."""
    logger.debug(f"Checking out branch or path: {switch_cmd.branch}")

    # Resolve branch or path to a branch name
    try:
        resolved_branch = resolve_worktree_argument(switch_cmd.branch, services)
        logger.debug(f"Resolved to branch: {resolved_branch}")
    except ValueError:
        # Error already printed by resolve_worktree_argument
        return

    # Update the switch command with the resolved branch name
    # Create a new SwitchCommand with the resolved branch
    switch_cmd = replace(switch_cmd, branch=resolved_branch)

    # Find git repository
    try:
        repo_path = services.git.find_repo_root()
        if not repo_path:
            print_error("Error: Not in a git repository")
            return
    except ValueError as e:
        print_error(f"Error: {e}")
        return

    # Load configuration
    config = services.state.load_config(project_dir=repo_path)
    project_config = services.state.load_project_config(repo_path)

    # Get current worktrees before applying prefix (we need to check if branches exist)
    git_worktrees = services.git.list_worktrees(repo_path)

    # Apply branch prefix if configured
    canonical_branch = get_canonical_branch_name(
        switch_cmd.branch,
        config.worktree.branch_prefix,
        git_worktrees,
        repo_path,
        services,
        apply_to_new_branches=True,
    )
    if canonical_branch != switch_cmd.branch:
        switch_cmd = replace(switch_cmd, branch=canonical_branch)

    # Use project config session_init as default if no init_script provided
    session_init_script = switch_cmd.init_script
    if session_init_script is None:
        session_init_script = project_config.session_init

    # Resolve custom script if provided
    custom_script_resolved = None
    if switch_cmd.custom_script:
        custom_script_resolved = resolve_custom_script_with_interpolation(
            switch_cmd.custom_script
        )
        if custom_script_resolved:
            logger.debug(f"Resolved custom script: {custom_script_resolved}")

    # Use provided terminal mode or fall back to config
    terminal_mode = switch_cmd.terminal_mode
    if terminal_mode is None:
        terminal_mode = config.terminal

    # Enable output suppression for echo mode
    original_suppress = options.suppress_rich_output
    if terminal_mode == TerminalMode.ECHO:
        options.suppress_rich_output = True

    # Check if worktree already exists
    existing_worktree = None
    for worktree in git_worktrees:
        if worktree.branch == switch_cmd.branch:
            existing_worktree = worktree
            break

    if existing_worktree:
        # Check if we're already in this worktree
        current_path = Path.cwd()
        try:
            if current_path.is_relative_to(existing_worktree.path):
                print_info(f"Already in {switch_cmd.branch} worktree")
                return
        except ValueError:
            # is_relative_to raises ValueError if not relative
            pass

        # Switch to existing worktree - no init script needed (worktree already set up)
        # Combine after_init and custom script for existing worktrees too
        combined_after_init = _combine_after_init_and_custom_script(
            switch_cmd.after_init, custom_script_resolved
        )
        try:
            # Run pre_switch hooks
            _run_hook_set(
                services,
                HookType.PRE_SWITCH,
                existing_worktree.path,
                repo_path,
                config,
                switch_cmd.branch,
                abort_on_failure=False,
            )

            success = services.terminal.switch_to_worktree(
                existing_worktree.path,
                terminal_mode,
                None,  # No session_init script for existing worktrees
                combined_after_init,
                branch_name=switch_cmd.branch,
                auto_confirm=options.auto_confirm,
                ignore_same_session=switch_cmd.ignore_same_session,
            )

            if not success:
                print_error(f"Failed to switch to {switch_cmd.branch} worktree")
                return

            # Run post_switch hooks
            _run_hook_set(
                services,
                HookType.POST_SWITCH,
                existing_worktree.path,
                repo_path,
                config,
                switch_cmd.branch,
                abort_on_failure=False,
            )

            # Session ID will be registered by the new tab itself
            return
        finally:
            # Restore original suppression setting
            options.suppress_rich_output = original_suppress

    # Create new worktree
    try:
        # If this is a dynamic command (not explicit 'switch'), prompt for confirmation
        if switch_cmd.from_dynamic_command and not switch_cmd.auto_confirm:
            if not confirm_default_yes(
                f"Create a branch '{switch_cmd.branch}' and worktree?"
            ):
                print_info("Worktree creation cancelled.")
                return

        _create_new_worktree(
            services,
            switch_cmd,
            repo_path,
            terminal_mode,
            session_init_script,
            custom_script_resolved,
        )
    finally:
        # Restore original suppression setting
        options.suppress_rich_output = original_suppress


def _create_new_worktree(
    services: Services,
    switch_cmd: SwitchCommand,
    repo_path: Path,
    terminal_mode,
    session_init_script: str | None = None,
    custom_script_resolved: str | None = None,
) -> None:
    """Create a new worktree for the branch."""
    print_info("Fetching branches...")
    if not services.git.fetch_branches(repo_path):
        print_error("Warning: Failed to fetch latest branches")

    # Check if branch exists on remote and prompt user if needed
    if not switch_cmd.from_branch:  # Only check remote if no explicit source branch
        remote_exists, remote_name = (
            services.git.branch_resolver.check_remote_branch_availability(
                repo_path, switch_cmd.branch
            )
        )

        if remote_exists and not switch_cmd.auto_confirm:
            if not confirm_default_yes(
                f"Branch '{switch_cmd.branch}' exists on remote '{remote_name}'. "
                f"Create a local worktree tracking the remote branch?"
            ):
                print_info("Worktree creation cancelled.")
                return

    # Generate worktree path with sanitized branch name
    worktree_path = _generate_worktree_path(
        services, repo_path, switch_cmd.branch, switch_cmd.dir
    )

    # Check if the target path already exists with a different branch
    git_worktrees = services.git.list_worktrees(repo_path)
    conflicting_worktree = None
    for worktree in git_worktrees:
        if worktree.path == worktree_path and worktree.branch != switch_cmd.branch:
            conflicting_worktree = worktree
            break

    if conflicting_worktree:
        # Generate alternative path and prompt user
        alternative_path = _generate_alternative_worktree_path(
            worktree_path, git_worktrees
        )

        if alternative_path == worktree_path:
            # Fallback to original error if we can't find an alternative
            print_error(
                f"✗ Directory {worktree_path} already exists with branch '{conflicting_worktree.branch}'"
            )
            print_error(
                f"  Try 'autowt {conflicting_worktree.branch}' to switch to existing worktree"
            )
            print_error("  Or 'autowt cleanup' to remove unused worktrees")
            return

        # Prompt user to confirm using alternative path
        if not _prompt_for_alternative_worktree(
            worktree_path, alternative_path, conflicting_worktree.branch
        ):
            print_info("Worktree creation cancelled.")
            return

        # Use the alternative path
        worktree_path = alternative_path

    print_info(f"Creating worktree for {switch_cmd.branch}...")

    # Load configuration for hooks
    config = services.state.load_config(project_dir=repo_path)

    # Run pre_create hooks before creating the worktree
    if not _run_hook_set(
        services,
        HookType.PRE_CREATE,
        worktree_path,
        repo_path,
        config,
        switch_cmd.branch,
        abort_on_failure=True,
    ):
        print_error("pre_create hooks failed, aborting worktree creation")
        return

    # Create the worktree
    if not services.git.create_worktree(
        repo_path, switch_cmd.branch, worktree_path, switch_cmd.from_branch
    ):
        print_error(f"✗ Failed to create worktree for {switch_cmd.branch}")
        return

    print_success(f"✓ Worktree created at {worktree_path}")

    # Run post_create hooks after worktree creation
    if not _run_hook_set(
        services,
        HookType.POST_CREATE,
        worktree_path,
        repo_path,
        config,
        switch_cmd.branch,
        abort_on_failure=True,
    ):
        print_error("post_create hooks failed, aborting worktree creation")
        return

    # Run pre_switch hooks for new worktree
    _run_hook_set(
        services,
        HookType.PRE_SWITCH,
        worktree_path,
        repo_path,
        config,
        switch_cmd.branch,
        abort_on_failure=False,
    )

    # Determine if terminal mode performs an actual switch
    # ECHO/INPLACE modes don't actually switch terminals
    runs_async_before_switch = terminal_mode in (
        TerminalMode.ECHO,
        TerminalMode.INPLACE,
    )

    # For ECHO/INPLACE modes, run async hooks before switching (since no actual switch happens)
    if runs_async_before_switch:
        _run_hook_set(
            services,
            HookType.POST_CREATE_ASYNC,
            worktree_path,
            repo_path,
            config,
            switch_cmd.branch,
            abort_on_failure=False,
        )

    # Switch to the new worktree
    # Combine after_init and custom script
    combined_after_init = _combine_after_init_and_custom_script(
        switch_cmd.after_init, custom_script_resolved
    )
    success = services.terminal.switch_to_worktree(
        worktree_path,
        terminal_mode,
        session_init_script,
        combined_after_init,
        branch_name=switch_cmd.branch,
        ignore_same_session=switch_cmd.ignore_same_session,
    )

    if not success:
        print_error("Worktree created but failed to switch terminals")
        return

    # Run post_switch hooks for new worktree
    _run_hook_set(
        services,
        HookType.POST_SWITCH,
        worktree_path,
        repo_path,
        config,
        switch_cmd.branch,
        abort_on_failure=False,
    )

    # For modes that actually switch terminals, run async hooks after switching
    # (user is already in new terminal, this runs in original terminal)
    if not runs_async_before_switch:
        _run_hook_set(
            services,
            HookType.POST_CREATE_ASYNC,
            worktree_path,
            repo_path,
            config,
            switch_cmd.branch,
            abort_on_failure=False,
        )

    # Session ID will be registered by the new tab itself

    print_success(f"Switched to new {switch_cmd.branch} worktree")


def _generate_worktree_path(
    services, repo_path: Path, branch: str, custom_dir: str | None = None
) -> Path:
    """Generate a path for the new worktree using configuration or custom directory."""
    import os  # noqa: PLC0415

    # If custom directory is provided, use it directly
    if custom_dir:
        # Handle both absolute and relative paths
        if os.path.isabs(custom_dir):
            custom_path = Path(custom_dir)
        else:
            # Relative paths are relative to the current working directory
            custom_path = Path(os.getcwd()) / custom_dir

        # Ensure parent directory exists
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        return custom_path

    # Load configuration
    config = services.state.load_config(project_dir=repo_path)

    # Find the main repository path (not a worktree)
    worktrees = services.git.list_worktrees(repo_path)

    # Find the primary (main) repository
    main_repo_path = None
    for worktree in worktrees:
        if worktree.is_primary:
            main_repo_path = worktree.path
            break

    # Fallback to current repo_path if no primary found
    if not main_repo_path:
        main_repo_path = repo_path

    repo_name = main_repo_path.name
    # For bare repositories ending in .git, remove the suffix for cleaner directory names
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    repo_dir = str(main_repo_path)
    repo_parent_dir = str(main_repo_path.parent)

    # Sanitize branch name for filesystem
    safe_branch = sanitize_branch_name(branch)

    # Get directory pattern from configuration
    directory_pattern = config.worktree.directory_pattern
    logger.debug(f"Using directory pattern: {directory_pattern}")

    # Replace template variables
    pattern_with_vars = directory_pattern.format(
        repo_dir=repo_dir,
        repo_name=repo_name,
        repo_parent_dir=repo_parent_dir,
        branch=safe_branch,
    )

    # Expand environment variables
    expanded_pattern = os.path.expandvars(pattern_with_vars)
    logger.debug(f"Pattern after variable substitution: {expanded_pattern}")

    # Create path - handle both absolute and relative paths
    if os.path.isabs(expanded_pattern):
        worktree_path = Path(expanded_pattern)
    else:
        # Relative paths are relative to the main repo directory
        combined_path = main_repo_path / expanded_pattern
        # Normalize path without resolving symlinks
        worktree_path = Path(os.path.normpath(str(combined_path)))

    # Ensure parent directory exists
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Final worktree path: {worktree_path}")
    return worktree_path


def _run_hook_set(
    services: Services,
    hook_type: str,
    worktree_path: Path,
    repo_path: Path,
    config,
    branch_name: str,
    *,
    abort_on_failure: bool = False,
    dry_run: bool = False,
) -> bool:
    """Generic hook runner for all hook types.

    Args:
        services: Services container
        hook_type: Type of hook (from HookType constants)
        worktree_path: Path to the worktree
        repo_path: Path to the repository
        config: Project configuration (already loaded)
        branch_name: Name of the branch
        abort_on_failure: If True, return False on failure; if False, warn and continue
        dry_run: If True, just print what would run

    Returns:
        True if hooks succeeded or no hooks exist, False if hooks failed and abort_on_failure=True
    """
    if dry_run:
        print_info(f"[DRY RUN] Would run {hook_type} hooks for {branch_name}")
        return True

    # Load global config
    global_config = services.config_loader.load_config(project_dir=None)

    # Extract hook scripts
    global_scripts, project_scripts = extract_hook_scripts(
        global_config, config, hook_type
    )

    # Early return if no hooks
    if not global_scripts and not project_scripts:
        return True

    # Run hooks
    print_info(f"Running {hook_type} hooks for {branch_name}")
    success = services.hooks.run_hooks(
        global_scripts,
        project_scripts,
        hook_type,
        worktree_path,
        repo_path,
        branch_name,
    )

    # Handle failure
    if not success and not abort_on_failure:
        print_info(f"Warning: {hook_type} hooks failed, but continuing anyway")

    return success if abort_on_failure else True
