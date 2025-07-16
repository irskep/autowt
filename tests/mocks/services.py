"""Mock services for testing business logic."""

from pathlib import Path

from autowt.models import (
    ApplicationState,
    BranchStatus,
    Configuration,
    ProcessInfo,
    TerminalMode,
    WorktreeInfo,
)


class MockStateService:
    """Mock state service for testing."""

    def __init__(self):
        self.states: dict[str, ApplicationState] = {}
        self.configs: dict[str, Configuration] = {}
        self.session_ids: dict[str, str] = {}
        self.save_called = False
        self.load_called = False

    def load_state(self, repo_path: Path) -> ApplicationState:
        self.load_called = True
        key = str(repo_path)
        return self.states.get(
            key, ApplicationState(primary_clone=repo_path, worktrees=[])
        )

    def save_state(self, state: ApplicationState) -> None:
        self.save_called = True
        self.states[str(state.primary_clone)] = state

    def load_config(self) -> Configuration:
        return self.configs.get("default", Configuration())

    def save_config(self, config: Configuration) -> None:
        self.configs["default"] = config

    def load_session_ids(self) -> dict[str, str]:
        return self.session_ids.copy()

    def save_session_ids(self, session_ids: dict[str, str]) -> None:
        self.session_ids = session_ids.copy()


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
        self, repo_path: Path, branch: str, worktree_path: Path
    ) -> bool:
        self.create_worktree_calls.append((repo_path, branch, worktree_path))
        if self.create_success:
            # Add to our mock worktree list
            self.worktrees.append(
                WorktreeInfo(branch=branch, path=worktree_path, is_current=False)
            )
        return self.create_success

    def remove_worktree(self, repo_path: Path, worktree_path: Path) -> bool:
        self.remove_worktree_calls.append((repo_path, worktree_path))
        if self.remove_success:
            # Remove from our mock worktree list
            self.worktrees = [wt for wt in self.worktrees if wt.path != worktree_path]
        return self.remove_success

    def analyze_branches_for_cleanup(
        self, repo_path: Path, worktrees: list[WorktreeInfo]
    ) -> list[BranchStatus]:
        return self.branch_statuses.copy()

    def install_hooks(self, repo_path: Path) -> bool:
        self.install_hooks_called = True
        return self.install_hooks_success


class MockTerminalService:
    """Mock terminal service for testing."""

    def __init__(self):
        self.is_macos = True
        self.is_iterm = True
        self.current_session_id = "test-session-123"
        self.switch_success = True

        # Track method calls
        self.switch_calls = []

    def get_current_session_id(self) -> str | None:
        return self.current_session_id

    def switch_to_worktree(
        self,
        worktree_path: Path,
        mode: TerminalMode,
        session_id: str | None = None,
        init_script: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
    ) -> bool:
        self.switch_calls.append(
            (worktree_path, mode, session_id, init_script, branch_name, auto_confirm)
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
