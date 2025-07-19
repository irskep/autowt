"""Checkout/create worktree command."""

import logging
from pathlib import Path

import click

from autowt.config import get_config
from autowt.console import print_error, print_info, print_success
from autowt.global_config import options
from autowt.models import Services, SwitchCommand, TerminalMode
from autowt.prompts import confirm_default_yes
from autowt.utils import sanitize_branch_name

logger = logging.getLogger(__name__)


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
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print_error("Error: Not in a git repository")
        return

    # Load configuration
    config = services.state.load_config()
    project_config = services.state.load_project_config(repo_path)
    session_ids = services.state.load_session_ids()

    # Use project config init as default if no init_script provided
    init_script = switch_cmd.init_script
    if init_script is None:
        init_script = project_config.init

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
        session_id = session_ids.get(switch_cmd.branch)
        try:
            success = services.terminal.switch_to_worktree(
                existing_worktree.path,
                terminal_mode,
                session_id,
                None,  # No init script for existing worktrees
                branch_name=switch_cmd.branch,
                auto_confirm=options.auto_confirm,
                ignore_same_session=switch_cmd.ignore_same_session,
            )

            if not success:
                print_error(f"Failed to switch to {switch_cmd.branch} worktree")
                return

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
            session_ids,
            init_script,
        )
    finally:
        # Restore original suppression setting
        options.suppress_rich_output = original_suppress


def _create_new_worktree(
    services: Services,
    switch_cmd: SwitchCommand,
    repo_path: Path,
    terminal_mode,
    session_ids: dict,
    init_script: str | None = None,
) -> None:
    """Create a new worktree for the branch."""
    print_info("Fetching branches...")
    if not services.git.fetch_branches(repo_path):
        print_error("Warning: Failed to fetch latest branches")

    # Generate worktree path with sanitized branch name
    worktree_path = _generate_worktree_path(repo_path, switch_cmd.branch)

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
    if not services.git.create_worktree(repo_path, switch_cmd.branch, worktree_path):
        print_error(f"✗ Failed to create worktree for {switch_cmd.branch}")
        return

    print_success(f"✓ Worktree created at {worktree_path}")

    # Switch to the new worktree
    success = services.terminal.switch_to_worktree(
        worktree_path,
        terminal_mode,
        None,
        init_script,
        switch_cmd.after_init,
        branch_name=switch_cmd.branch,
        ignore_same_session=switch_cmd.ignore_same_session,
    )

    if not success:
        print_error("Worktree created but failed to switch terminals")
        return

    # Session ID will be registered by the new tab itself

    print_success(f"Switched to new {switch_cmd.branch} worktree")


def _generate_worktree_path(repo_path: Path, branch: str) -> Path:
    """Generate a path for the new worktree."""
    # Find the main repository path (not a worktree)
    from autowt.services.git import GitService  # noqa: PLC0415

    git_service = GitService()
    worktrees = git_service.list_worktrees(repo_path)

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

    # Sanitize branch name for filesystem
    safe_branch = sanitize_branch_name(branch)

    # Create worktrees directory next to main repo
    worktrees_dir = main_repo_path.parent / f"{repo_name}-worktrees"
    worktrees_dir.mkdir(exist_ok=True)

    return worktrees_dir / safe_branch


def switch_to_waiting_agent(services: Services) -> None:
    """Switch to an agent waiting for input."""
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print_error("Error: Not in a git repository")
        return

    git_worktrees = services.git.list_worktrees(repo_path)
    session_ids = services.state.load_session_ids()
    enhanced_worktrees = services.agent.enhance_worktrees_with_agent_status(
        git_worktrees, session_ids
    )

    waiting_agents = services.agent.find_waiting_agents(enhanced_worktrees)

    if not waiting_agents:
        print_info("No agents are currently waiting for input")
        return

    if len(waiting_agents) == 1:
        # Switch directly to the only waiting agent
        target_branch = waiting_agents[0].branch
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
        target_branch = waiting_agents[choice - 1].branch

    # Execute switch
    config = get_config()

    switch_cmd = SwitchCommand(
        branch=target_branch,
        terminal_mode=config.terminal.mode,
        init_script=config.scripts.init,
    )
    checkout_branch(switch_cmd, services)


def switch_to_latest_agent(services: Services) -> None:
    """Switch to the most recently active agent."""
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print_error("Error: Not in a git repository")
        return

    git_worktrees = services.git.list_worktrees(repo_path)
    session_ids = services.state.load_session_ids()
    enhanced_worktrees = services.agent.enhance_worktrees_with_agent_status(
        git_worktrees, session_ids
    )

    latest_agent = services.agent.find_latest_active_agent(enhanced_worktrees)

    if not latest_agent:
        print_info("No recently active agents found")
        return

    print_info(f"Switching to most recent agent: {latest_agent.branch}")

    # Execute switch
    config = get_config()

    switch_cmd = SwitchCommand(
        branch=latest_agent.branch,
        terminal_mode=config.terminal.mode,
        init_script=config.scripts.init,
    )
    checkout_branch(switch_cmd, services)
