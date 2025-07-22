"""Service builders and mocks for testing business logic."""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

from autowt.config import Config
from autowt.models import (
    AgentStatus,
    BranchStatus,
    ProcessInfo,
    ProjectConfig,
    TerminalMode,
    WorktreeInfo,
    WorktreeWithAgent,
)


class MockStateService:
    """Mock state service for testing."""

    def __init__(self):
        self.configs: dict[str, Config] = {}
        self.project_configs: dict[str, ProjectConfig] = {}
        self.session_ids: dict[str, str] = {}
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

    def load_session_ids(self) -> dict[str, str]:
        return self.session_ids.copy()

    def save_session_ids(self, session_ids: dict[str, str]) -> None:
        self.session_ids = session_ids.copy()

    def _make_session_key(self, repo_path: Path, branch_name: str) -> str:
        """Create a composite key for session storage."""
        return f"{repo_path.resolve()}:{branch_name}"

    def get_session_id(self, repo_path: Path, branch_name: str) -> str | None:
        """Get session ID for specific repo/branch combination."""
        key = self._make_session_key(repo_path, branch_name)
        return self.session_ids.get(key)

    def set_session_id(
        self, repo_path: Path, branch_name: str, session_id: str
    ) -> None:
        """Set session ID for specific repo/branch combination."""
        key = self._make_session_key(repo_path, branch_name)
        self.session_ids[key] = session_id

    def remove_session_id(self, repo_path: Path, branch_name: str) -> None:
        """Remove session ID for specific repo/branch combination."""
        key = self._make_session_key(repo_path, branch_name)
        if key in self.session_ids:
            self.session_ids.pop(key)

    def get_session_ids_for_repo(self, repo_path: Path) -> dict[str, str]:
        """Get all session IDs for a repo, with branch names as keys."""
        repo_key_prefix = f"{repo_path.resolve()}:"

        result = {}
        for key, session_id in self.session_ids.items():
            if key.startswith(repo_key_prefix):
                branch_name = key[len(repo_key_prefix) :]
                result[branch_name] = session_id

        return result

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
        self.current_session_id = "test-session-123"
        self.switch_success = True

        # Track method calls
        self.switch_calls = []

        # Mock the terminal implementation
        self.terminal = Mock()
        self.terminal.get_current_session_id.return_value = self.current_session_id
        self.terminal.supports_session_management.return_value = True

    def get_current_session_id(self) -> str | None:
        return self.current_session_id

    def switch_to_worktree(
        self,
        worktree_path: Path,
        mode: TerminalMode,
        session_id: str | None = None,
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
                session_id,
                init_script,
                after_init,
                branch_name,
                auto_confirm,
                ignore_same_session,
            )
        )
        return self.switch_success


class MockProcessService:
    """Mock process service for testing."""

    def __init__(self):
        self.processes: list[ProcessInfo] = []
        self.terminate_success = True

        # Track method calls
        self.find_calls = []
        self.terminate_calls = []

    def find_processes_in_directory(self, directory: Path) -> list[ProcessInfo]:
        self.find_calls.append(directory)
        # Return processes that match this directory
        return [p for p in self.processes if p.working_dir == directory]

    def terminate_processes(self, processes: list[ProcessInfo]) -> bool:
        self.terminate_calls.append(processes)
        return self.terminate_success

    def print_process_summary(self, processes: list[ProcessInfo]) -> None:
        # Mock implementation - just track the call
        pass


class MockAgentService:
    """Mock agent service for testing."""

    def __init__(self):
        self.agent_statuses: dict[Path, AgentStatus | None] = {}
        self.process_running_results: dict[Path, bool] = {}

    def detect_agent_status(self, worktree_path: Path) -> AgentStatus | None:
        return self.agent_statuses.get(worktree_path)

    def enhance_worktrees_with_agent_status(
        self, worktrees: list[WorktreeInfo], state_service, repo_path: Path
    ) -> list[WorktreeWithAgent]:
        """Add agent status to worktree information."""
        enhanced = []
        for worktree in worktrees:
            agent_status = self.detect_agent_status(worktree.path)
            session_id = state_service.get_session_id(repo_path, worktree.branch)
            has_session = session_id is not None
            enhanced.append(
                WorktreeWithAgent(
                    branch=worktree.branch,
                    path=worktree.path,
                    is_current=worktree.is_current,
                    is_primary=worktree.is_primary,
                    agent_status=agent_status,
                    has_active_session=has_session,
                )
            )
        return enhanced

    def find_waiting_agents(
        self, enhanced_worktrees: list[WorktreeWithAgent]
    ) -> list[WorktreeWithAgent]:
        """Find worktrees with agents waiting for input."""
        return [
            wt
            for wt in enhanced_worktrees
            if wt.agent_status and wt.agent_status.status == "waiting"
        ]

    def find_latest_active_agent(
        self, enhanced_worktrees: list[WorktreeWithAgent]
    ) -> WorktreeWithAgent | None:
        """Find the most recently active agent."""
        active_agents = [
            wt
            for wt in enhanced_worktrees
            if wt.agent_status
            and wt.agent_status.status in ["working", "idle", "waiting"]
        ]
        if not active_agents:
            return None
        return sorted(
            active_agents, key=lambda w: w.agent_status.last_activity, reverse=True
        )[0]


class MockServices:
    """Mock Services container for testing."""

    def __init__(self):
        self.state = MockStateService()
        self.git = MockGitService()
        self.terminal = MockTerminalService()
        self.process = MockProcessService()
        self.agent = MockAgentService()
