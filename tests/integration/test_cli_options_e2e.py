"""End-to-end tests for CLI option processing and configuration integration."""

from unittest.mock import patch

from autowt.cli import main


class TestCLIOptionsE2E:
    """End-to-end tests for CLI option processing and configuration integration."""

    def test_terminal_option_parsing(self, temp_git_repo, force_echo_mode, cli_runner):
        """Test that --terminal options are correctly parsed and processed."""
        # Test different terminal mode options
        terminal_modes = ["tab", "window", "inplace", "echo"]

        for mode in terminal_modes:
            with patch("os.getcwd", return_value=str(temp_git_repo)):
                result = cli_runner.invoke(
                    main, ["test-branch", "--terminal", mode, "-y"]
                )

            assert result.exit_code == 0

            # All modes should result in echo output due to AUTOWT_TEST_FORCE_ECHO
            assert "cd " in result.output
            assert "test-branch" in result.output

    def test_after_init_option(self, temp_git_repo, force_echo_mode, cli_runner):
        """Test --after-init option processing."""
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(
                main,
                [
                    "after-init-branch",
                    "--after-init",
                    "code . && echo 'Ready to code!'",
                    "-y",
                ],
            )

        assert result.exit_code == 0

        assert "cd " in result.output
        assert "code . && echo 'Ready to code!'" in result.output
        assert "after-init-branch" in result.output

    def test_yes_auto_confirm_option(self, temp_git_repo, force_echo_mode, cli_runner):
        """Test -y/--yes auto-confirm option."""
        # Test short form
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["auto-confirm-short", "-y"])
        assert result.exit_code == 0

        # Test long form
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["auto-confirm-long", "--yes"])
        assert result.exit_code == 0

    def test_ignore_same_session_option(
        self, temp_git_repo, force_echo_mode, cli_runner
    ):
        """Test --ignore-same-session option."""
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(
                main, ["ignore-session-branch", "--ignore-same-session", "-y"]
            )

        assert result.exit_code == 0

        assert "cd " in result.output
        assert "ignore-session-branch" in result.output

    def test_debug_option(self, temp_git_repo, force_echo_mode, cli_runner):
        """Test --debug option enables additional logging."""
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(main, ["debug-branch", "--debug", "-y"])

        assert result.exit_code == 0

        # Debug mode should still work with branch switching
        # Specific debug output verification would require capturing logs

    def test_complex_option_combination(
        self, temp_git_repo, force_echo_mode, cli_runner
    ):
        """Test complex combination of multiple CLI options."""
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(
                main,
                [
                    "complex-options-branch",
                    "--terminal",
                    "window",
                    "--after-init",
                    "echo 'Project ready'",
                    "--ignore-same-session",
                    "--yes",
                    "--debug",
                ],
            )

        assert result.exit_code == 0

        assert "cd " in result.output
        assert "complex-options-branch" in result.output
        assert "Project ready" in result.output

    def test_invalid_terminal_option(self, temp_git_repo, cli_runner):
        """Test error handling for invalid terminal mode."""
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(
                main, ["invalid-terminal", "--terminal", "invalid-mode"]
            )

        # Should fail due to invalid terminal mode
        assert result.exit_code != 0
        assert "invalid-mode" in result.output or result.exception is not None

    def test_option_inheritance_from_config(
        self, temp_git_repo, force_echo_mode, cli_runner
    ):
        """Test that CLI options properly override configuration defaults."""
        # This tests the integration between CLI parsing and config system
        with patch("os.getcwd", return_value=str(temp_git_repo)):
            result = cli_runner.invoke(
                main,
                [
                    "config-override-branch",
                    "--after-init",
                    "echo 'CLI provided after-init'",
                    "-y",
                ],
            )

        assert result.exit_code == 0

        assert "cd " in result.output
        assert "CLI provided after-init" in result.output
        assert "config-override-branch" in result.output
