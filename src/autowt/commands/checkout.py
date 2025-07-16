"""Checkout/create worktree command."""

import logging
from pathlib import Path

from autowt.console import print_error, print_info, print_success
from autowt.global_config import options
from autowt.models import TerminalMode, WorktreeInfo
from autowt.services.git import GitService
from autowt.services.process import ProcessService
from autowt.services.state import StateService
from autowt.services.terminal import TerminalService
from autowt.utils import sanitize_branch_name

logger = logging.getLogger(__name__)


def checkout_branch(
    branch: str,
    terminal_mode: TerminalMode | None,
    state_service: StateService,
    git_service: GitService,
    terminal_service: TerminalService,
    process_service: ProcessService,
    init_script: str | None = None,
) -> None:
    """Switch to or create a worktree for the specified branch."""
    logger.debug(f"Checking out branch: {branch}")

    # Find git repository
    repo_path = git_service.find_repo_root()
    if not repo_path:
        print_error("Error: Not in a git repository")
        return

    # Load configuration and state
    config = state_service.load_config()
    project_config = state_service.load_project_config(repo_path)
    state = state_service.load_state(repo_path)
    session_ids = state_service.load_session_ids()

    # Use project config init as default if no init_script provided
    if init_script is None:
        init_script = project_config.init

    # Use provided terminal mode or fall back to config
    if terminal_mode is None:
        terminal_mode = config.terminal

    # Get current worktrees
    git_worktrees = git_service.list_worktrees(repo_path)

    # Check if worktree already exists
    existing_worktree = None
    for worktree in git_worktrees:
        if worktree.branch == branch:
            existing_worktree = worktree
            break

    if existing_worktree:
        # Switch to existing worktree - the terminal service handles prompting
        session_id = session_ids.get(branch)
        success = terminal_service.switch_to_worktree(
            existing_worktree.path,
            terminal_mode,
            session_id,
            init_script,
            branch_name=branch,
            auto_confirm=options.auto_confirm,
        )

        if not success:
            print_error(f"Failed to switch to {branch} worktree")
            return

        # Update session ID if we're in a terminal that supports it
        current_session = terminal_service.get_current_session_id()
        if current_session:
            session_ids[branch] = current_session
            state_service.save_session_ids(session_ids)

        return

    # Create new worktree
    _create_new_worktree(
        branch,
        repo_path,
        terminal_mode,
        state,
        session_ids,
        git_service,
        terminal_service,
        state_service,
        init_script,
    )


def _create_new_worktree(
    branch: str,
    repo_path: Path,
    terminal_mode: TerminalMode,
    state,
    session_ids: dict,
    git_service: GitService,
    terminal_service: TerminalService,
    state_service: StateService,
    init_script: str | None = None,
) -> None:
    """Create a new worktree for the branch."""
    print_info("Fetching branches...")
    if not git_service.fetch_branches(repo_path):
        print_error("Warning: Failed to fetch latest branches")

    # Generate worktree path with sanitized branch name
    worktree_path = _generate_worktree_path(repo_path, branch)

    print_info(f"Creating worktree for {branch}...")

    # Create the worktree
    if not git_service.create_worktree(repo_path, branch, worktree_path):
        print_error(f"✗ Failed to create worktree for {branch}")
        return

    print_success(f"✓ Worktree created at {worktree_path}")

    # Switch to the new worktree
    success = terminal_service.switch_to_worktree(
        worktree_path, terminal_mode, None, init_script
    )

    if not success:
        print_error("Worktree created but failed to switch terminals")
        return

    # Save session ID if available
    current_session = terminal_service.get_current_session_id()
    if current_session:
        session_ids[branch] = current_session
        state_service.save_session_ids(session_ids)

    # Update state
    new_worktree = WorktreeInfo(
        branch=branch,
        path=worktree_path,
        session_id=current_session,
    )
    state.worktrees.append(new_worktree)
    state.current_worktree = branch
    state_service.save_state(state)

    print_success(f"Switched to new {branch} worktree")


def _generate_worktree_path(repo_path: Path, branch: str) -> Path:
    """Generate a path for the new worktree."""
    from autowt.services.git import GitService

    # Find the main repository path (not a worktree)
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
