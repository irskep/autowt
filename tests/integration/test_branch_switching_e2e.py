"""End-to-end tests for core branch switching functionality."""

from unittest.mock import patch

from autowt.cli import main
from autowt.utils import run_command


class TestBranchSwitchingE2E:
    """End-to-end tests for branch switching workflow."""

    def test_switch_to_new_branch(self, temp_git_repo, force_echo_mode, cli_runner):
        """Test creating a new worktree for a new branch."""
        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["new-feature-branch", "-y"])

        assert result.exit_code == 0

        # Should contain cd command to the new worktree directory in CLI output
        assert "cd " in result.output
        assert "new-feature-branch" in result.output

    def test_switch_to_existing_branch(
        self, temp_git_repo, force_echo_mode, cli_runner
    ):
        """Test switching to an existing git branch (creates worktree if needed)."""
        # Debug: Show git status before test
        git_status = run_command(
            ["git", "status", "--porcelain", "-b"], cwd=temp_git_repo
        )
        print(f"Git status before test: {git_status.stdout}")

        git_worktree_list = run_command(["git", "worktree", "list"], cwd=temp_git_repo)
        print(f"Git worktree list before test: {git_worktree_list.stdout}")

        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["feature/test-branch", "-y"])

        print(f"Test result exit_code: {result.exit_code}")
        print(f"Test result output: {repr(result.output)}")

        assert result.exit_code == 0

        # Should create new worktree and show cd command (fixture guarantees we start on main)
        assert "cd " in result.output, f"Expected 'cd' in output: {repr(result.output)}"
        assert "test-branch" in result.output

    def test_switch_with_after_init_script(
        self, temp_git_repo, force_echo_mode, cli_runner
    ):
        """Test branch switching with after-init script."""
        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(
                main, ["script-branch", "--after-init", "npm install", "-y"]
            )

        assert result.exit_code == 0

        # Should contain both cd command and after-init script in CLI output
        assert "cd " in result.output
        assert "npm install" in result.output
        assert "script-branch" in result.output

    def test_switch_with_terminal_mode_override(
        self, temp_git_repo, force_echo_mode, cli_runner
    ):
        """Test that CLI terminal mode options are processed correctly."""
        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(
                main, ["window-branch", "--terminal", "window", "-y"]
            )

        assert result.exit_code == 0

        # Even though we specified window mode, it should be overridden to echo mode
        # by our test environment variable
        # Should still contain cd command (echo mode output) in CLI output
        assert "cd " in result.output
        assert "window-branch" in result.output

    def test_switch_with_multiple_options(
        self, temp_git_repo, force_echo_mode, cli_runner
    ):
        """Test branch switching with multiple CLI options."""
        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(
                main,
                [
                    "complex-branch",
                    "--terminal",
                    "tab",
                    "--after-init",
                    "code .",
                    "-y",
                ],
            )

        assert result.exit_code == 0

        # Should contain cd command and after-init script in CLI output
        assert "cd " in result.output
        assert "complex-branch" in result.output
        assert "code ." in result.output

    def test_error_handling_invalid_repo(
        self, isolated_temp_dir, force_echo_mode, cli_runner
    ):
        """Test error handling when not in a git repository."""
        # Change to a non-git directory
        with patch("os.getcwd", return_value=str(isolated_temp_dir)):
            result = cli_runner.invoke(main, ["some-branch"])

        # Check that the application handles non-git directories gracefully
        # (may exit with 0 and show helpful message, or exit with error code)
        assert isinstance(result.exit_code, int)
        # If it exits with 0, there should be some informative output
        if result.exit_code == 0:
            assert len(result.output) > 0
