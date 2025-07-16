"""Pytest configuration and shared fixtures."""

import pytest

from autowt.models import (
    ApplicationState,
    BranchStatus,
    Configuration,
    ProcessInfo,
    TerminalMode,
    WorktreeInfo,
)


@pytest.fixture
def temp_repo_path(tmp_path):
    """Create a temporary repository path."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    return repo_path


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return Configuration(terminal=TerminalMode.TAB, terminal_always_new=False)


@pytest.fixture
def sample_worktrees(temp_repo_path):
    """Sample worktree data for testing."""
    return [
        WorktreeInfo(
            branch="feature1",
            path=temp_repo_path.parent / "test-repo-worktrees" / "feature1",
            is_current=False,
            session_id="session1",
        ),
        WorktreeInfo(
            branch="feature2",
            path=temp_repo_path.parent / "test-repo-worktrees" / "feature2",
            is_current=True,
            session_id="session2",
        ),
        WorktreeInfo(
            branch="bugfix",
            path=temp_repo_path.parent / "test-repo-worktrees" / "bugfix",
            is_current=False,
            session_id=None,
        ),
    ]


@pytest.fixture
def sample_app_state(temp_repo_path, sample_worktrees):
    """Sample application state for testing."""
    return ApplicationState(
        primary_clone=temp_repo_path,
        worktrees=sample_worktrees,
        current_worktree="feature2",
    )


@pytest.fixture
def sample_branch_statuses(sample_worktrees):
    """Sample branch status data for testing."""
    return [
        BranchStatus(
            branch="feature1",
            has_remote=True,
            is_merged=False,
            path=sample_worktrees[0].path,
        ),
        BranchStatus(
            branch="feature2",
            has_remote=False,
            is_merged=False,
            path=sample_worktrees[1].path,
        ),
        BranchStatus(
            branch="bugfix",
            has_remote=True,
            is_merged=True,
            path=sample_worktrees[2].path,
        ),
    ]


@pytest.fixture
def sample_processes(sample_worktrees):
    """Sample process data for testing."""
    return [
        ProcessInfo(
            pid=1234, command="python server.py", working_dir=sample_worktrees[0].path
        ),
        ProcessInfo(
            pid=5678, command="npm run dev", working_dir=sample_worktrees[1].path
        ),
    ]
