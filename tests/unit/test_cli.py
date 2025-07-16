"""Tests for CLI command routing and argument handling."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from autowt.cli import main


class TestCLIRouting:
    """Tests for CLI command routing and fallback behavior."""

    @pytest.mark.skip(
        reason="CLI tests need refactoring - mocking issues with create_services"
    )
    def test_explicit_commands_work(self):
        """Test that explicit subcommands work correctly."""
        runner = CliRunner()

        # Mock all the command functions to avoid actual execution
        with (
            patch("autowt.commands.init.init_autowt") as mock_init,
            patch("autowt.commands.ls.list_worktrees") as mock_ls,
            patch("autowt.commands.cleanup.cleanup_worktrees") as mock_cleanup,
            patch("autowt.commands.config.configure_settings") as mock_config,
            patch(
                "autowt.cli.create_services",
                return_value=(Mock(), Mock(), Mock(), Mock()),
            ),
        ):
            # Test init command
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0
            mock_init.assert_called_once()

            # Test ls command
            result = runner.invoke(main, ["ls"])
            assert result.exit_code == 0
            mock_ls.assert_called_once()

            # Test cleanup command
            result = runner.invoke(main, ["cleanup"])
            assert result.exit_code == 0
            mock_cleanup.assert_called_once()

            # Test config command
            result = runner.invoke(main, ["config"])
            assert result.exit_code == 0
            mock_config.assert_called_once()

    @pytest.mark.skip(
        reason="CLI tests need refactoring - mocking issues with create_services"
    )
    def test_switch_command_works(self):
        """Test that explicit switch command works."""
        runner = CliRunner()

        with (
            patch("autowt.commands.checkout.checkout_branch") as mock_checkout,
            patch(
                "autowt.cli.create_services",
                return_value=(Mock(), Mock(), Mock(), Mock()),
            ),
        ):
            result = runner.invoke(main, ["switch", "feature-branch"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            # Check that the branch name was passed correctly
            args, kwargs = mock_checkout.call_args
            assert args[0] == "feature-branch"  # branch name

    @pytest.mark.skip(
        reason="CLI tests need refactoring - mocking issues with create_services"
    )
    def test_branch_name_fallback(self):
        """Test that unknown commands are treated as branch names."""
        runner = CliRunner()

        with (
            patch("autowt.commands.checkout.checkout_branch") as mock_checkout,
            patch(
                "autowt.cli.create_services",
                return_value=(Mock(), Mock(), Mock(), Mock()),
            ),
        ):
            # Test simple branch name
            result = runner.invoke(main, ["feature-branch"])
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            assert args[0] == "feature-branch"

            mock_checkout.reset_mock()

            # Test branch name with slashes
            result = runner.invoke(main, ["steve/bugfix"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            assert args[0] == "steve/bugfix"

    @pytest.mark.skip(
        reason="CLI tests need refactoring - mocking issues with create_services"
    )
    def test_terminal_option_passed_through(self):
        """Test that --terminal option is passed to checkout function."""
        runner = CliRunner()

        with (
            patch("autowt.commands.checkout.checkout_branch") as mock_checkout,
            patch(
                "autowt.cli.create_services",
                return_value=(Mock(), Mock(), Mock(), Mock()),
            ),
        ):
            # Test with explicit switch command
            result = runner.invoke(
                main, ["switch", "feature-branch", "--terminal", "window"]
            )
            assert result.exit_code == 0
            args, kwargs = mock_checkout.call_args
            assert args[0] == "feature-branch"  # branch name
            # args[1] should be the TerminalMode
            from autowt.models import TerminalMode

            assert args[1] == TerminalMode.WINDOW

            mock_checkout.reset_mock()

            # Test with branch name fallback
            result = runner.invoke(main, ["feature-branch", "--terminal", "tab"])
            assert result.exit_code == 0
            args, kwargs = mock_checkout.call_args
            assert args[0] == "feature-branch"
            assert args[1] == TerminalMode.TAB

    @pytest.mark.skip(
        reason="CLI tests need refactoring - mocking issues with create_services"
    )
    def test_no_args_shows_list(self):
        """Test that running with no arguments shows the worktree list."""
        runner = CliRunner()

        with (
            patch("autowt.commands.ls.list_worktrees") as mock_ls,
            patch(
                "autowt.cli.create_services",
                return_value=(Mock(), Mock(), Mock(), Mock()),
            ),
        ):
            result = runner.invoke(main, [])
            assert result.exit_code == 0
            mock_ls.assert_called_once()

    def test_help_works(self):
        """Test that help commands work correctly."""
        runner = CliRunner()

        # Main help
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Git worktree manager" in result.output

        # Subcommand help
        result = runner.invoke(main, ["switch", "--help"])
        assert result.exit_code == 0
        assert "Switch to or create a worktree" in result.output

    @pytest.mark.skip(
        reason="CLI tests need refactoring - mocking issues with create_services"
    )
    def test_debug_flag_works(self):
        """Test that debug flag is handled correctly."""
        runner = CliRunner()

        with (
            patch("autowt.cli.setup_logging") as mock_setup_logging,
            patch("autowt.commands.ls.list_worktrees"),
            patch(
                "autowt.cli.create_services",
                return_value=(Mock(), Mock(), Mock(), Mock()),
            ),
        ):
            # Test debug flag - setup_logging is called in both main and ls command
            result = runner.invoke(main, ["ls", "--debug"])
            assert result.exit_code == 0
            # Should be called twice: once from main group, once from ls command
            assert mock_setup_logging.call_count == 2
            mock_setup_logging.assert_any_call(True)

            mock_setup_logging.reset_mock()

            # Test without debug flag
            result = runner.invoke(main, ["ls"])
            assert result.exit_code == 0
            # Should be called twice: once from main group, once from ls command
            assert mock_setup_logging.call_count == 2
            mock_setup_logging.assert_any_call(False)

    @pytest.mark.skip(
        reason="CLI tests need refactoring - mocking issues with create_services"
    )
    def test_cleanup_mode_options(self):
        """Test that cleanup mode options work correctly."""
        runner = CliRunner()

        with (
            patch("autowt.commands.cleanup.cleanup_worktrees") as mock_cleanup,
            patch(
                "autowt.cli.create_services",
                return_value=(Mock(), Mock(), Mock(), Mock()),
            ),
        ):
            from autowt.models import CleanupMode

            # Test different modes
            for mode_str, mode_enum in [
                ("all", CleanupMode.ALL),
                ("merged", CleanupMode.MERGED),
                ("remoteless", CleanupMode.REMOTELESS),
                ("interactive", CleanupMode.INTERACTIVE),
            ]:
                result = runner.invoke(main, ["cleanup", "--mode", mode_str])
                assert result.exit_code == 0
                mock_cleanup.assert_called_once()
                args, kwargs = mock_cleanup.call_args
                assert args[0] == mode_enum
                mock_cleanup.reset_mock()

    @pytest.mark.skip(
        reason="CLI tests need refactoring - mocking issues with create_services"
    )
    def test_complex_branch_names(self):
        """Test that complex branch names work as fallback."""
        runner = CliRunner()

        with (
            patch("autowt.commands.checkout.checkout_branch") as mock_checkout,
            patch(
                "autowt.cli.create_services",
                return_value=(Mock(), Mock(), Mock(), Mock()),
            ),
        ):
            # Test various complex branch names
            complex_names = [
                "feature/user-auth",
                "steve/bugfix-123",
                "release/v2.1.0",
                "hotfix/critical-bug",
                "chore/update-deps",
            ]

            for branch_name in complex_names:
                result = runner.invoke(main, [branch_name])
                assert result.exit_code == 0, f"Failed for branch: {branch_name}"
                mock_checkout.assert_called_once()
                args, kwargs = mock_checkout.call_args
                assert args[0] == branch_name
                mock_checkout.reset_mock()

    @pytest.mark.skip(
        reason="CLI tests need refactoring - mocking issues with create_services"
    )
    def test_reserved_words_as_branch_names(self):
        """Test handling of reserved command names as branch names using switch."""
        runner = CliRunner()

        with (
            patch("autowt.commands.checkout.checkout_branch") as mock_checkout,
            patch(
                "autowt.cli.create_services",
                return_value=(Mock(), Mock(), Mock(), Mock()),
            ),
        ):
            # If someone has a branch literally named 'init', they need to use 'switch'
            result = runner.invoke(main, ["switch", "init"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            assert args[0] == "init"
