"""Lifecycle hooks execution for autowt.

This module provides utilities for executing lifecycle hooks (scripts that run at specific
points during worktree operations). Hooks receive both positional arguments and environment
variables for maximum flexibility.
"""

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class HookType:
    """Constants for hook types."""

    PRE_CREATE = "pre_create"
    POST_CREATE = "post_create"
    POST_CREATE_ASYNC = "post_create_async"
    SESSION_INIT = "session_init"
    PRE_CLEANUP = "pre_cleanup"
    POST_CLEANUP = "post_cleanup"
    PRE_SWITCH = "pre_switch"
    POST_SWITCH = "post_switch"


class HookRunner:
    """Executes lifecycle hooks with proper environment and arguments."""

    def __init__(self):
        """Initialize hook runner."""
        self.logger = logging.getLogger(__name__)

    def run_hook(
        self,
        hook_script: str,
        hook_type: str,
        worktree_dir: Path,
        main_repo_dir: Path,
        branch_name: str,
        timeout: int = 60,
    ) -> bool:
        """Execute a hook script with environment variables.

        Args:
            hook_script: The script command to execute
            hook_type: Type of hook being executed (init, pre_cleanup, etc.)
            worktree_dir: Path to the worktree directory
            main_repo_dir: Path to the main repository directory
            branch_name: Name of the branch
            timeout: Timeout in seconds for script execution

        Returns:
            True if hook executed successfully, False otherwise
        """
        if not hook_script or not hook_script.strip():
            return True

        logger.info(f"Executing {hook_type} hook")

        # Prepare environment variables
        env = self._prepare_environment(
            hook_type, worktree_dir, main_repo_dir, branch_name
        )

        try:
            # Determine working directory based on hook type
            # For pre_create, use main repo since worktree doesn't exist yet
            # For post_cleanup, use main repo since worktree has been deleted
            working_dir = (
                main_repo_dir
                if hook_type in (HookType.PRE_CREATE, HookType.POST_CLEANUP)
                else worktree_dir
            )

            # Execute the hook script directly with shell=True
            # The shell naturally handles multi-line scripts without preprocessing
            # Output streams directly to terminal for visibility
            result = subprocess.run(
                hook_script,
                shell=True,
                cwd=str(working_dir),
                env=env,
                timeout=timeout,
                capture_output=False,
                text=True,
            )

            if result.returncode == 0:
                logger.info(f"{hook_type} hook completed successfully")
                return True
            else:
                logger.error(
                    f"{hook_type} hook failed with exit code {result.returncode}"
                )
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"{hook_type} hook timed out after {timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Failed to execute {hook_type} hook: {e}")
            return False

    def run_hooks(
        self,
        global_scripts: list[str],
        project_scripts: list[str],
        hook_type: str,
        worktree_dir: Path,
        main_repo_dir: Path,
        branch_name: str,
        timeout: int = 60,
    ) -> bool:
        """Execute both global and project hooks of the same type.

        As requested, this runs BOTH sets of hooks - global hooks don't get replaced
        by project hooks, they both run.

        Args:
            global_scripts: List of global hook scripts to run
            project_scripts: List of project hook scripts to run
            hook_type: Type of hook being executed
            worktree_dir: Path to the worktree directory
            main_repo_dir: Path to the main repository directory
            branch_name: Name of the branch
            timeout: Timeout in seconds for each script

        Returns:
            True if all hooks executed successfully, False if any failed
        """
        all_scripts = []

        # Add global scripts first
        all_scripts.extend(global_scripts)

        # Add project scripts
        all_scripts.extend(project_scripts)

        if not all_scripts:
            return True

        logger.debug(f"Running {len(all_scripts)} {hook_type} hook(s)")

        # Execute all scripts in order
        for script in all_scripts:
            if not self.run_hook(
                script, hook_type, worktree_dir, main_repo_dir, branch_name, timeout
            ):
                logger.error(
                    f"Hook execution failed, stopping remaining {hook_type} hooks"
                )
                return False

        return True

    def _prepare_environment(
        self,
        hook_type: str,
        worktree_dir: Path,
        main_repo_dir: Path,
        branch_name: str,
    ) -> dict[str, str]:
        """Prepare environment variables for hook execution.

        Returns a copy of the current environment with autowt-specific variables added.
        """
        env = os.environ.copy()

        # Add autowt-specific environment variables
        env["AUTOWT_WORKTREE_DIR"] = str(worktree_dir)
        env["AUTOWT_MAIN_REPO_DIR"] = str(main_repo_dir)
        env["AUTOWT_BRANCH_NAME"] = branch_name
        env["AUTOWT_HOOK_TYPE"] = hook_type

        return env


def extract_hook_scripts(
    global_config, project_config, hook_type: str
) -> tuple[list[str], list[str]]:
    """Extract hook scripts from global and project configurations.

    Args:
        global_config: Global configuration object
        project_config: Project configuration object
        hook_type: Type of hook to extract (post_create, session_init, pre_cleanup, etc.)

    Returns:
        Tuple of (global_scripts, project_scripts) lists
    """
    global_scripts = []
    project_scripts = []

    # Handle backward compatibility for legacy 'init' hook type
    effective_hook_type = hook_type
    if hook_type == "init":
        # Legacy support: map 'init' to 'session_init' for backward compatibility
        effective_hook_type = "session_init"
        logger.warning(
            "Hook type 'init' is deprecated. Use 'session_init' instead. "
            "This will be removed in a future version."
        )

    # Extract from global config
    if global_config and hasattr(global_config, "scripts") and global_config.scripts:
        script = getattr(global_config.scripts, effective_hook_type, None)
        if script:
            global_scripts.append(script)

    # Extract from project config
    if project_config and hasattr(project_config, "scripts") and project_config.scripts:
        script = getattr(project_config.scripts, effective_hook_type, None)
        if script:
            project_scripts.append(script)

    return global_scripts, project_scripts
