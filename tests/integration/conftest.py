"""Shared fixtures for integration tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from autowt.utils import run_command


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository with sample branches and commits."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir)

        # Initialize git repository with main as default branch
        run_command(["git", "init", "--initial-branch=main"], cwd=repo_path)
        run_command(["git", "config", "user.email", "test@example.com"], cwd=repo_path)
        run_command(["git", "config", "user.name", "Test User"], cwd=repo_path)

        # Create initial commit
        test_file = repo_path / "README.md"
        test_file.write_text("# Test Repository\n")
        run_command(["git", "add", "README.md"], cwd=repo_path)
        run_command(["git", "commit", "-m", "Initial commit"], cwd=repo_path)

        # Create sample branches
        run_command(["git", "branch", "feature/test-branch"], cwd=repo_path)
        run_command(["git", "branch", "bugfix/urgent-fix"], cwd=repo_path)

        # Add some commits to feature branch
        run_command(["git", "checkout", "feature/test-branch"], cwd=repo_path)
        feature_file = repo_path / "feature.txt"
        feature_file.write_text("Feature implementation\n")
        run_command(["git", "add", "feature.txt"], cwd=repo_path)
        run_command(
            ["git", "commit", "-m", "Add feature implementation"], cwd=repo_path
        )

        # Return to main - ensure this succeeds
        result = run_command(["git", "checkout", "main"], cwd=repo_path)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to checkout main branch: {result.stderr}")

        # Verify we're actually on main
        status_result = run_command(["git", "branch", "--show-current"], cwd=repo_path)
        if status_result.returncode != 0 or status_result.stdout.strip() != "main":
            raise RuntimeError(
                f"Expected to be on main branch, but got: {status_result.stdout.strip()}"
            )

        yield repo_path

        # Cleanup: ensure we're on main branch after each test
        try:
            run_command(["git", "checkout", "main"], cwd=repo_path)
        except Exception:
            # Ignore cleanup errors if directory is already gone
            pass


@pytest.fixture
def force_echo_mode():
    """Force all terminal operations to use echo mode for testing."""
    with patch.dict(os.environ, {"AUTOWT_TEST_FORCE_ECHO": "1"}):
        yield


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def isolated_temp_dir():
    """Create an isolated temporary directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)
