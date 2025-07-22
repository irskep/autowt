"""Checkout/create worktree command."""

import logging
from pathlib import Path

import click

from autowt.cli_config import resolve_custom_script_with_interpolation
from autowt.config import get_config_loader
from autowt.console import print_error, print_info, print_success
from autowt.global_config import options
from autowt.hooks import HookRunner, HookType, extract_hook_scripts
from autowt.models import Services, SwitchCommand, TerminalMode
from autowt.prompts import confirm_default_yes
from autowt.utils import sanitize_branch_name

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
    logger.debug(f"Checking out branch: {switch_cmd.branch}")

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

    # Get current worktrees
    git_worktrees = services.git.list_worktrees(repo_path)

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
        session_id = services.state.get_session_id(repo_path, switch_cmd.branch)
        # Combine after_init and custom script for existing worktrees too
        combined_after_init = _combine_after_init_and_custom_script(
            switch_cmd.after_init, custom_script_resolved
        )
        try:
            # Run pre_switch hooks
            _run_pre_switch_hooks(
                existing_worktree.path, repo_path, config, switch_cmd.branch
            )

            success = services.terminal.switch_to_worktree(
                existing_worktree.path,
                terminal_mode,
                session_id,
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
            _run_post_switch_hooks(
                existing_worktree.path, repo_path, config, switch_cmd.branch
            )

            # Session ID will be registered by the new tab itself
            return
        finally:
            # Restore original suppression setting
            options.suppress_rich_output = original_suppress

    # Create new worktree
    try:
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

    # Create the worktree
    if not services.git.create_worktree(
        repo_path, switch_cmd.branch, worktree_path, switch_cmd.from_branch
    ):
        print_error(f"✗ Failed to create worktree for {switch_cmd.branch}")
        return

    print_success(f"✓ Worktree created at {worktree_path}")

    # Load configuration for hooks
    config = services.state.load_config(project_dir=repo_path)

    # Run post_create hooks after worktree creation
    if not _run_post_create_hooks(worktree_path, repo_path, config, switch_cmd.branch):
        print_error("post_create hooks failed, aborting worktree creation")
        return

    # Run pre_switch hooks for new worktree
    _run_pre_switch_hooks(worktree_path, repo_path, config, switch_cmd.branch)

    # Switch to the new worktree
    # Combine after_init and custom script
    combined_after_init = _combine_after_init_and_custom_script(
        switch_cmd.after_init, custom_script_resolved
    )
    success = services.terminal.switch_to_worktree(
        worktree_path,
        terminal_mode,
        None,
        session_init_script,
        combined_after_init,
        branch_name=switch_cmd.branch,
        ignore_same_session=switch_cmd.ignore_same_session,
    )

    if not success:
        print_error("Worktree created but failed to switch terminals")
        return

    # Run post_switch hooks for new worktree
    _run_post_switch_hooks(worktree_path, repo_path, config, switch_cmd.branch)

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


def find_waiting_agent_branch(services: Services) -> str | None:
    """Find the branch of an agent waiting for input."""
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print_error("Error: Not in a git repository")
        return None

    git_worktrees = services.git.list_worktrees(repo_path)
    enhanced_worktrees = services.agent.enhance_worktrees_with_agent_status(
        git_worktrees, services.state, repo_path
    )

    waiting_agents = services.agent.find_waiting_agents(enhanced_worktrees)

    if not waiting_agents:
        print_info("No agents are currently waiting for input")
        return None

    if len(waiting_agents) == 1:
        # Return the only waiting agent's branch
        return waiting_agents[0].branch
    else:
        # Show interactive choice
        print_info("Multiple agents waiting for input:")
        for i, agent in enumerate(waiting_agents, 1):
            print_info(
                f"{i}. {agent.branch} (waiting since {agent.agent_status.last_activity})"
            )

        choice = click.prompt(
            "Choose agent", type=click.IntRange(1, len(waiting_agents))
        )
        return waiting_agents[choice - 1].branch


def find_latest_agent_branch(services: Services) -> str | None:
    """Find the branch of the most recently active agent."""
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print_error("Error: Not in a git repository")
        return None

    git_worktrees = services.git.list_worktrees(repo_path)
    enhanced_worktrees = services.agent.enhance_worktrees_with_agent_status(
        git_worktrees, services.state, repo_path
    )

    latest_agent = services.agent.find_latest_active_agent(enhanced_worktrees)

    if not latest_agent:
        print_info("No recently active agents found")
        return None

    print_info(f"Switching to most recent agent: {latest_agent.branch}")
    return latest_agent.branch


def _run_post_create_hooks(
    worktree_path: Path,
    repo_path: Path,
    config,
    branch_name: str,
) -> bool:
    """Run post_create hooks after creating a worktree but before terminal switch.

    Returns:
        True if all hooks succeeded, False if any failed
    """
    # Load both global and project configurations to run both sets of hooks
    hook_runner = HookRunner()

    # Get global config by loading without project dir
    loader = get_config_loader()
    global_config = loader.load_config(project_dir=None)

    global_scripts, project_scripts = extract_hook_scripts(
        global_config, config, HookType.POST_CREATE
    )

    if global_scripts or project_scripts:
        print_info(f"Running post_create hooks for {branch_name}")
        return hook_runner.run_hooks(
            global_scripts,
            project_scripts,
            HookType.POST_CREATE,
            worktree_path,
            repo_path,
            branch_name,
        )

    return True


def _run_pre_switch_hooks(
    worktree_path: Path,
    repo_path: Path,
    config,
    branch_name: str,
) -> None:
    """Run pre_switch hooks before switching to a worktree."""
    # Load both global and project configurations to run both sets of hooks
    hook_runner = HookRunner()

    # Get global config by loading without project dir

    loader = get_config_loader()
    global_config = loader.load_config(project_dir=None)

    global_scripts, project_scripts = extract_hook_scripts(
        global_config, config, HookType.PRE_SWITCH
    )

    if global_scripts or project_scripts:
        print_info(f"Running pre_switch hooks for {branch_name}")
        hook_runner.run_hooks(
            global_scripts,
            project_scripts,
            HookType.PRE_SWITCH,
            worktree_path,
            repo_path,
            branch_name,
        )


def _run_post_switch_hooks(
    worktree_path: Path,
    repo_path: Path,
    config,
    branch_name: str,
) -> None:
    """Run post_switch hooks after switching to a worktree."""
    # Load both global and project configurations to run both sets of hooks
    hook_runner = HookRunner()

    # Get global config by loading without project dir

    loader = get_config_loader()
    global_config = loader.load_config(project_dir=None)

    global_scripts, project_scripts = extract_hook_scripts(
        global_config, config, HookType.POST_SWITCH
    )

    if global_scripts or project_scripts:
        print_info(f"Running post_switch hooks for {branch_name}")
        hook_runner.run_hooks(
            global_scripts,
            project_scripts,
            HookType.POST_SWITCH,
            worktree_path,
            repo_path,
            branch_name,
        )
