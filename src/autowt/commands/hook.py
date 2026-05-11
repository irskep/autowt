"""Run a specific lifecycle hook."""

import logging
from pathlib import Path

from autowt.console import print_error, print_info
from autowt.hooks import extract_hook_scripts
from autowt.models import Services

logger = logging.getLogger(__name__)


def _find_main_repo_dir(services: Services, repo_root: Path) -> Path:
    """Find the primary (main) repository directory from any worktree."""
    worktrees = services.git.list_worktrees(repo_root)
    for worktree in worktrees:
        if worktree.is_primary:
            return worktree.path
    return repo_root


def run_hook_command(hook_name: str, services: Services) -> bool:
    """Run a specific lifecycle hook using the global + project config cascade.

    Args:
        hook_name: The hook type to run (e.g. "session_init", "post_create")
        services: Services container

    Returns:
        True if all hooks succeeded (or none were configured), False on failure.
    """
    repo_root = services.git.find_repo_root()
    if not repo_root:
        print_error("Not in a git repository")
        return False

    branch_name = services.git.get_current_branch(repo_root)
    if not branch_name:
        print_error("Could not determine current branch")
        return False

    worktree_dir = repo_root
    main_repo_dir = _find_main_repo_dir(services, repo_root)

    global_config = services.config_loader.load_config(project_dir=None)
    project_config = services.state.load_config(project_dir=repo_root)

    global_scripts, project_scripts = extract_hook_scripts(
        global_config, project_config, hook_name
    )
    all_scripts = global_scripts + project_scripts

    if not all_scripts:
        print_info(f"No {hook_name} hooks configured")
        return True

    for script in all_scripts:
        success = services.hooks.run_hook(
            script,
            hook_name,
            worktree_dir,
            main_repo_dir,
            branch_name,
        )
        if not success:
            print_error(f"{hook_name} hook failed")
            return False

    return True
