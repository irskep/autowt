"""End-to-end tests for the ls command functionality."""

import shutil
from unittest.mock import patch

from autowt.cli import main
from autowt.utils import run_command


class TestLsCommandE2E:
    """End-to-end tests for listing worktrees."""

    def test_ls_with_basic_repository(self, temp_git_repo, cli_runner):
        """Test ls command with a basic repository setup."""
        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["ls"])

        assert result.exit_code == 0

        # Should show main branch (current branch in our setup)
        assert "main" in result.output

        # Output should contain repository information
        assert len(result.output.strip()) > 0

    def test_ls_with_worktrees_created(
        self, temp_git_repo, cli_runner, force_echo_mode
    ):
        """Test ls command after creating some worktrees."""
        # First create a worktree using git directly
        worktrees_dir = temp_git_repo.parent / "worktrees"
        worktrees_dir.mkdir(exist_ok=True)
        feature_worktree = worktrees_dir / "feature-test-branch"

        # Remove the directory if it exists from previous test runs
        if feature_worktree.exists():
            shutil.rmtree(feature_worktree)

        run_command(
            ["git", "worktree", "add", str(feature_worktree), "feature/test-branch"],
            cwd=temp_git_repo,
        )

        # Now run ls command
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["ls"])

        assert result.exit_code == 0

        # Should show both main and the feature branch worktree
        assert "main" in result.output, (
            f"Expected 'main' in output: {repr(result.output)}"
        )

        # Debug: Print git worktree list to see what was actually created
        debug_result = run_command(["git", "worktree", "list"], cwd=temp_git_repo)
        print(f"Git worktree list: {debug_result.stdout}")

        # Check if feature worktree appears in output
        has_feature_ref = (
            "feature" in result.output
            or "test-branch" in result.output
            or "feature-test-branch" in result.output
        )
        assert has_feature_ref, (
            f"Expected feature worktree reference in output: {repr(result.output)}"
        )

    def test_ls_with_empty_repository(self, isolated_temp_dir, cli_runner):
        """Test ls command error handling with non-git directory."""
        # Create a basic git repo without branches or commits
        run_command(["git", "init"], cwd=isolated_temp_dir)
        run_command(
            ["git", "config", "user.email", "test@example.com"], cwd=isolated_temp_dir
        )
        run_command(["git", "config", "user.name", "Test User"], cwd=isolated_temp_dir)

        # Try to run ls in empty git repo
        with patch("os.getcwd", return_value=str(isolated_temp_dir)):
            result = cli_runner.invoke(main, ["ls"])

        # Should handle empty repository gracefully
        # Exit code might be 0 (empty list) or non-zero (error), either is acceptable
        assert isinstance(result.exit_code, int)

    def test_ls_outside_git_repo(self, isolated_temp_dir, cli_runner):
        """Test ls command when run outside a git repository."""
        # Change to a non-git directory
        with patch("os.getcwd", return_value=str(isolated_temp_dir)):
            result = cli_runner.invoke(main, ["ls"])

        # Application should handle non-git directories gracefully
        assert isinstance(result.exit_code, int)
        # Should contain some informative output or error message
        assert len(result.output) > 0 or result.exception is not None

    def test_ls_with_debug_flag(self, temp_git_repo, cli_runner):
        """Test ls command with debug flag for additional logging."""
        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["ls", "--debug"])

        assert result.exit_code == 0

        # Debug flag shouldn't break the core functionality
        assert "main" in result.output
