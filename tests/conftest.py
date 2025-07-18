"""Pytest configuration and shared fixtures."""

from unittest.mock import Mock, patch

import pytest

from autowt.config import Config
from autowt.models import (
    BranchStatus,
    ProcessInfo,
    WorktreeInfo,
)
from tests.mocks.services import MockTerminalService


@pytest.fixture
def temp_repo_path(tmp_path):
    """Create a temporary repository path."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    return repo_path


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return Config()


@pytest.fixture
def sample_worktrees(temp_repo_path):
    """Sample worktree data for testing."""
    return [
        WorktreeInfo(
            branch="feature1",
            path=temp_repo_path.parent / "test-repo-worktrees" / "feature1",
            is_current=False,
        ),
        WorktreeInfo(
            branch="feature2",
            path=temp_repo_path.parent / "test-repo-worktrees" / "feature2",
            is_current=True,
        ),
        WorktreeInfo(
            branch="bugfix",
            path=temp_repo_path.parent / "test-repo-worktrees" / "bugfix",
            is_current=False,
        ),
    ]


@pytest.fixture
def sample_branch_statuses(sample_worktrees):
    """Sample branch status data for testing."""
    return [
        BranchStatus(
            branch="feature1",
            has_remote=False,  # Make it remoteless so it gets cleaned up
            is_merged=False,
            is_identical=False,
            path=sample_worktrees[0].path,
        ),
        BranchStatus(
            branch="feature2",
            has_remote=False,
            is_merged=False,
            is_identical=True,  # This branch is identical to main
            path=sample_worktrees[1].path,
        ),
        BranchStatus(
            branch="bugfix",
            has_remote=True,
            is_merged=True,
            is_identical=False,
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


@pytest.fixture(autouse=True)
def mock_terminal_operations():
    """Automatically mock potentially harmful terminal operations in all tests."""
    with (
        patch(
            "autowt.services.terminal.Terminal._run_applescript",
            return_value=True,
        ) as mock_applescript,
        patch(
            "autowt.services.terminal.run_command", return_value=Mock(returncode=0)
        ) as mock_run_command,
        patch("platform.system", return_value="Darwin") as mock_platform,
    ):
        yield {
            "applescript": mock_applescript,
            "run_command": mock_run_command,
            "platform": mock_platform,
        }


@pytest.fixture
def mock_terminal_service():
    """Provide a fully mocked terminal service."""
    return MockTerminalService()
