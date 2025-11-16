"""Pytest configuration and shared fixtures."""

from unittest.mock import Mock, patch

import pytest

from tests.fixtures.config_fixtures import build_sample_config
from tests.fixtures.git_fixtures import (
    build_sample_branch_statuses,
    build_sample_worktrees,
)
from tests.fixtures.service_builders import MockServices, MockTerminalService


@pytest.fixture
def temp_repo_path(tmp_path):
    """Create a temporary repository path."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    return repo_path


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return build_sample_config()


@pytest.fixture
def sample_worktrees(temp_repo_path):
    """Sample worktree data for testing."""
    return build_sample_worktrees(temp_repo_path)


@pytest.fixture
def sample_branch_statuses(sample_worktrees):
    """Sample branch status data for testing."""
    return build_sample_branch_statuses(sample_worktrees)


@pytest.fixture(autouse=True)
def mock_terminal_operations():
    """Automatically mock potentially harmful terminal operations in all tests."""
    with (
        patch(
            "autowt.utils.run_command", return_value=Mock(returncode=0)
        ) as mock_run_command,
        patch("platform.system", return_value="Darwin") as mock_platform,
    ):
        yield {
            "run_command": mock_run_command,
            "platform": mock_platform,
        }


@pytest.fixture
def mock_terminal_service():
    """Provide a fully mocked terminal service."""
    return MockTerminalService()


@pytest.fixture
def mock_services() -> MockServices:
    """Create a fresh MockServices instance for each test.

    Example:
        def test_something(mock_services):
            # Configure as needed
            mock_services.hooks.run_hooks_success = True
            mock_services.git.create_success = True

            result = my_function(mock_services)
            assert result is True
    """
    return MockServices()
