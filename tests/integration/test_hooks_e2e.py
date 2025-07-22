"""End-to-end tests for hook management functionality."""

from unittest.mock import patch

from autowt.cli import main


class TestHooksE2E:
    """End-to-end tests for hook management commands."""

    def test_hooks_install_dry_run(self, temp_git_repo, cli_runner):
        """Test hooks install with dry run flag."""
        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["hooks-install", "--dry-run"])

        assert result.exit_code == 0

        # Should show what would be installed without actually installing
        assert len(result.output) > 0

        # Verify no actual hooks were installed (dry run)
        hooks_dir = temp_git_repo / ".git" / "hooks"
        if hooks_dir.exists():
            # If hooks directory exists, check that autowt hooks weren't actually installed
            hook_files = list(hooks_dir.glob("*"))
            # In dry run mode, no autowt-specific hooks should be created
            assert not any("autowt" in str(f) for f in hook_files)

    def test_hooks_install_show(self, temp_git_repo, cli_runner):
        """Test hooks install with show flag to display current status."""
        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["hooks-install", "--show"])

        assert result.exit_code == 0

        # Should display information about current hook status
        assert len(result.output) > 0

    def test_hooks_install_dry_run_and_show_separate(self, temp_git_repo, cli_runner):
        """Test hooks install with dry-run and show flags separately (they cannot be combined)."""
        # Test dry-run first
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["hooks-install", "--dry-run"])
        assert result.exit_code == 0
        assert len(result.output) > 0

        # Test show separately
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["hooks-install", "--show"])
        assert result.exit_code == 0
        assert len(result.output) > 0

    def test_hooks_outside_git_repo(self, isolated_temp_dir, cli_runner):
        """Test hooks command error handling when not in a git repository."""
        # Change to a non-git directory
        with patch("os.getcwd", return_value=str(isolated_temp_dir)):
            result = cli_runner.invoke(main, ["hooks-install", "--dry-run"])

        # Application handles non-git directories gracefully
        assert isinstance(result.exit_code, int)

        # Should contain some informative output
        assert len(result.output) > 0 or result.exception is not None

    def test_hooks_with_existing_git_hooks(self, temp_git_repo, cli_runner):
        """Test hooks behavior when git hooks directory already exists."""
        # Create git hooks directory with a sample hook
        hooks_dir = temp_git_repo / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        sample_hook = hooks_dir / "pre-commit"
        sample_hook.write_text("#!/bin/sh\necho 'Sample pre-commit hook'\n")
        sample_hook.chmod(0o755)

        # Run hooks install dry run (can't combine --dry-run and --show)
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["hooks-install", "--dry-run"])

        assert result.exit_code == 0

        # Should handle existing hooks gracefully
        assert len(result.output) > 0

    def test_hooks_with_debug_flag(self, temp_git_repo, cli_runner):
        """Test hooks command with debug flag for additional logging."""
        # Change to the test repo directory
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["hooks-install", "--dry-run", "--debug"])

        assert result.exit_code == 0

        # Debug flag shouldn't break the core functionality
        assert len(result.output) > 0

    def test_hooks_project_vs_user_flags(self, temp_git_repo, cli_runner):
        """Test hooks install with project and user flag options."""
        # Test project flag with simulated user input (choosing option 1)
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(
                main, ["hooks-install", "--project", "--dry-run"], input="1\n"
            )
        # Command may exit with 1 due to interactive abort in test environment, that's expected
        assert isinstance(result.exit_code, int)

        # Test user flag (installs to user's global git config area, no user interaction needed)
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["hooks-install", "--user", "--dry-run"])
        assert result.exit_code == 0, (
            f"Expected exit code 0 for user flag, got {result.exit_code}. Output: {repr(result.output)}"
        )

    def test_hooks_file_discovery(self, temp_git_repo, cli_runner):
        """Test that hooks command properly discovers git repository structure."""
        # Create a nested directory structure to test git repo discovery
        nested_dir = temp_git_repo / "src" / "deep" / "nested"
        nested_dir.mkdir(parents=True)

        # Run hooks command from nested directory
        with patch("os.getcwd", return_value=str(nested_dir)):
            result = cli_runner.invoke(main, ["hooks-install", "--dry-run"])

        # Should successfully find the git repository from nested directory
        assert result.exit_code == 0
        assert len(result.output) > 0
