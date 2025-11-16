"""Service builders and mocks for testing business logic."""

from collections import namedtuple
from pathlib import Path
from typing import Any

from autowt.config import Config
from autowt.models import (
    BranchStatus,
    ProjectConfig,
    TerminalMode,
    WorktreeInfo,
)


class MockStateService:
    """Mock state service for testing."""

    def __init__(self):
        self.configs: dict[str, Config] = {}
        self.project_configs: dict[str, ProjectConfig] = {}
        self.app_state: dict[str, Any] = {}

    def load_config(self, project_dir: Path | None = None) -> Config:
        return self.configs.get("default", Config())

    def save_config(self, config: Config) -> None:
        self.configs["default"] = config

    def load_project_config(self, repo_path: Path) -> ProjectConfig:
        key = str(repo_path)
        return self.project_configs.get(key, ProjectConfig())

    def save_project_config(self, repo_path: Path, config: ProjectConfig) -> None:
        self.project_configs[str(repo_path)] = config

    def load_app_state(self) -> dict[str, Any]:
        return self.app_state.copy()

    def save_app_state(self, state: dict[str, Any]) -> None:
        self.app_state = state.copy()

    def has_shown_hooks_prompt(self) -> bool:
        return self.app_state.get("hooks_prompt_shown", False)

    def mark_hooks_prompt_shown(self) -> None:
        self.app_state["hooks_prompt_shown"] = True

    def has_shown_experimental_terminal_warning(self) -> bool:
        return self.app_state.get("experimental_terminal_warning_shown", False)

    def mark_experimental_terminal_warning_shown(self) -> None:
        self.app_state["experimental_terminal_warning_shown"] = True


class MockBranchResolver:
    """Mock branch resolver for testing."""

    def __init__(self):
        self.remote_branch_availability = (False, None)

    def check_remote_branch_availability(
        self, repo_path: Path, branch: str
    ) -> tuple[bool, str | None]:
        """Mock remote branch availability check."""
        return self.remote_branch_availability


class MockGitService:
    """Mock git service for testing."""

    def __init__(self):
        self.repo_root: Path | None = None
        self.worktrees: list[WorktreeInfo] = []
        self.branch_statuses: list[BranchStatus] = []
        self.current_branch = "main"
        self.fetch_success = True
        self.create_success = True
        self.remove_success = True
        self.install_hooks_success = True
        self.branch_resolver = MockBranchResolver()

        # Track method calls
        self.fetch_called = False
        self.create_worktree_calls = []
        self.remove_worktree_calls = []
        self.install_hooks_called = False

    def find_repo_root(self, start_path: Path | None = None) -> Path | None:
        return self.repo_root

    def is_git_repo(self, path: Path) -> bool:
        return self.repo_root is not None

    def get_current_branch(self, repo_path: Path) -> str | None:
        return self.current_branch

    def list_worktrees(self, repo_path: Path) -> list[WorktreeInfo]:
        return self.worktrees.copy()

    def fetch_branches(self, repo_path: Path) -> bool:
        self.fetch_called = True
        return self.fetch_success

    def create_worktree(
        self,
        repo_path: Path,
        branch: str,
        worktree_path: Path,
        from_branch: str | None = None,
    ) -> bool:
        self.create_worktree_calls.append(
            (repo_path, branch, worktree_path, from_branch)
        )
        if self.create_success:
            # Add to our mock worktree list
            self.worktrees.append(
                WorktreeInfo(branch=branch, path=worktree_path, is_current=False)
            )
        return self.create_success

    def remove_worktree(
        self,
        repo_path: Path,
        worktree_path: Path,
        force: bool = False,
        interactive: bool = True,
    ) -> bool:
        self.remove_worktree_calls.append((repo_path, worktree_path))
        if self.remove_success:
            # Remove from our mock worktree list
            self.worktrees = [wt for wt in self.worktrees if wt.path != worktree_path]
        return self.remove_success

    def delete_branch(self, repo_path: Path, branch: str, force: bool = False) -> bool:
        """Mock branch deletion."""
        return True  # Always succeed for tests

    def analyze_branches_for_cleanup(
        self,
        repo_path: Path,
        worktrees: list[WorktreeInfo],
        preferred_remote: str | None = None,
    ) -> list[BranchStatus]:
        return self.branch_statuses.copy()

    def install_hooks(self, repo_path: Path) -> bool:
        self.install_hooks_called = True
        return self.install_hooks_success


class MockTerminalService:
    """Mock terminal service for testing."""

    def __init__(self):
        self.switch_success = True

        # Track method calls
        self.switch_calls = []

    def switch_to_worktree(
        self,
        worktree_path: Path,
        mode: TerminalMode,
        init_script: str | None = None,
        after_init: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
        ignore_same_session: bool = False,
    ) -> bool:
        self.switch_calls.append(
            (
                worktree_path,
                mode,
                init_script,
                after_init,
                branch_name,
                auto_confirm,
                ignore_same_session,
            )
        )
        return self.switch_success


class MockGitHubService:
    """Mock GitHub service for testing."""

    def __init__(self):
        self.is_github = False
        self.gh_available = False
        self.pr_statuses: dict[str, str | None] = {}
        self.analyze_result: list[BranchStatus] = []

    def is_github_repo(self, repo_path: Path) -> bool:
        return self.is_github

    def check_gh_available(self) -> bool:
        return self.gh_available

    def get_pr_status_for_branch(self, repo_path: Path, branch: str) -> str | None:
        return self.pr_statuses.get(branch)

    def analyze_branches_for_cleanup(
        self,
        repo_path: Path,
        worktrees: list[WorktreeInfo],
        git_service,
    ) -> list[BranchStatus]:
        return self.analyze_result.copy()


class MockConfigLoader:
    """Mock config loader for testing."""

    def __init__(self):
        self.global_config_file = Path("/tmp/config.toml")
        self.configs: dict[str, Config] = {}
        self.user_configured_cleanup_mode = False

    def load_config(
        self,
        project_dir: Path | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> Config:
        key = str(project_dir) if project_dir else "default"
        return self.configs.get(key, Config())

    def save_config(self, config: Config) -> None:
        self.configs["default"] = config

    def save_cleanup_mode(self, mode: Any) -> None:
        """Mock save cleanup mode."""
        pass

    def has_user_configured_cleanup_mode(self) -> bool:
        """Mock check for user configured cleanup mode."""
        return self.user_configured_cleanup_mode


class MockHookRunner:
    """Mock hook runner for testing."""

    def __init__(self):
        self.run_hooks_success = True
        self.run_hooks_calls = []

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
        self.run_hooks_calls.append(
            (
                global_scripts,
                project_scripts,
                hook_type,
                worktree_dir,
                main_repo_dir,
                branch_name,
                timeout,
            )
        )
        return self.run_hooks_success


class MockVersionCheckService:
    """Mock version check service for testing."""

    def __init__(self):
        self.version_info = None
        self.check_for_updates_called = False

    def check_for_updates(self, force: bool = False) -> Any | None:
        self.check_for_updates_called = True
        return self.version_info

    def _detect_installation_method(self) -> Any:
        """Mock installation method detection."""
        InstallationMethod = namedtuple("InstallationMethod", ["name", "command"])
        return InstallationMethod("pip", "pip install --upgrade autowt")


class MockServices:
    """Mock Services container for testing."""

    def __init__(self):
        self.state = MockStateService()
        self.git = MockGitService()
        self.terminal = MockTerminalService()
        self.github = MockGitHubService()
        self.config_loader = MockConfigLoader()
        self.hooks = MockHookRunner()
        self.version_check = MockVersionCheckService()
