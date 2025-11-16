"""Tests for CLI command routing and argument handling."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from autowt.cli import main
from autowt.models import CleanupMode
from tests.fixtures.service_builders import MockServices


class TestCLIRouting:
    """Tests for CLI command routing and fallback behavior."""

    def test_explicit_commands_work(self):
        """Test that explicit subcommands work correctly."""
        runner = CliRunner()

        # Mock all the command functions to avoid actual execution
        with (
            patch("autowt.cli.list_worktrees") as mock_ls,
            patch("autowt.cli.cleanup_worktrees") as mock_cleanup,
            patch("autowt.cli.configure_settings") as mock_configure,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.is_interactive_terminal", return_value=True),
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            # Setup mock services
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_config.cleanup.default_mode = CleanupMode.INTERACTIVE
            mock_get_config.return_value = mock_config

            # Mock config loader to indicate user has configured cleanup mode
            mock_services.config_loader.user_configured_cleanup_mode = True
            # Test ls command
            result = runner.invoke(main, ["ls"])
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
            assert result.exit_code == 0
            mock_ls.assert_called_once()

            # Test cleanup command
            result = runner.invoke(main, ["cleanup"])
            assert result.exit_code == 0
            mock_cleanup.assert_called_once()

            # Test config command
            result = runner.invoke(main, ["config"])
            assert result.exit_code == 0
            mock_configure.assert_called_once()

    def test_switch_command_works(self):
        """Test that explicit switch command works."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_config.terminal.mode = "tab"
            mock_config.scripts.session_init = None
            mock_get_config.return_value = mock_config

            result = runner.invoke(main, ["switch", "feature-branch"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            # Check that the SwitchCommand was created correctly
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-branch"

    def test_branch_name_fallback(self):
        """Test that unknown commands are treated as branch names."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_config.terminal.mode = "tab"
            mock_config.scripts.session_init = None
            mock_config.terminal.always_new = False
            mock_get_config.return_value = mock_config

            # Test simple branch name
            result = runner.invoke(main, ["feature-branch"])
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-branch"

            mock_checkout.reset_mock()

            # Test branch name with slashes
            result = runner.invoke(main, ["steve/bugfix"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "steve/bugfix"

    def test_terminal_option_passed_through(self):
        """Test that --terminal option is passed to checkout function."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_config.terminal.mode = "tab"
            mock_config.scripts.session_init = None
            mock_config.terminal.always_new = False
            mock_get_config.return_value = mock_config

            # Test with explicit switch command
            result = runner.invoke(
                main, ["switch", "feature-branch", "--terminal", "window"]
            )
            assert result.exit_code == 0
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-branch"
            assert switch_cmd.terminal_mode.value == "window"

            mock_checkout.reset_mock()

            # Test with branch name fallback
            result = runner.invoke(main, ["feature-branch", "--terminal", "tab"])
            assert result.exit_code == 0
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-branch"
            assert switch_cmd.terminal_mode.value == "tab"

    def test_no_args_shows_list(self):
        """Test that running with no arguments shows the worktree list."""
        runner = CliRunner()

        with (
            patch("autowt.cli.list_worktrees") as mock_ls,
            patch("autowt.cli.create_services") as mock_create_services,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

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

    def test_debug_flag_works(self):
        """Test that debug flag is handled correctly."""
        runner = CliRunner()

        with (
            patch("autowt.cli.setup_logging") as mock_setup_logging,
            patch("autowt.cli.list_worktrees"),
            patch("autowt.cli.create_services") as mock_create_services,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

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

    def test_cleanup_mode_options(self):
        """Test that cleanup mode options work correctly."""
        runner = CliRunner()

        with (
            patch("autowt.cli.cleanup_worktrees") as mock_cleanup,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_get_config.return_value = mock_config

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
                cleanup_cmd = args[0]
                assert cleanup_cmd.mode == mode_enum
                mock_cleanup.reset_mock()

    def test_complex_branch_names(self):
        """Test that complex branch names work as fallback."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_config.terminal.mode = "tab"
            mock_config.scripts.session_init = None
            mock_config.terminal.always_new = False
            mock_get_config.return_value = mock_config

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
                switch_cmd = args[0]
                assert switch_cmd.branch == branch_name
                mock_checkout.reset_mock()

    def test_reserved_words_as_branch_names(self):
        """Test handling of reserved command names as branch names using switch."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_config.terminal.mode = "tab"
            mock_config.scripts.session_init = None
            mock_config.terminal.always_new = False
            mock_get_config.return_value = mock_config

            # If someone has a branch literally named 'cleanup', they need to use 'switch'
            result = runner.invoke(main, ["switch", "cleanup"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "cleanup"
