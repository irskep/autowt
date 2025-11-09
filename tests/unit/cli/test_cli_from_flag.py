"""Tests for CLI --from flag functionality."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from autowt.cli import main
from tests.fixtures.service_builders import MockServices


class TestCLIFromFlag:
    """Test the --from flag in CLI commands."""

    def test_switch_command_help_shows_from_option(self):
        """Test that --from option appears in switch command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["switch", "--help"])

        assert result.exit_code == 0
        assert "--from TEXT" in result.output
        assert "Source branch/commit to create worktree from" in result.output

    def test_dynamic_branch_command_help_shows_from_option(self):
        """Test that --from option appears in dynamic branch command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["test-branch", "--help"])

        assert result.exit_code == 0
        assert "--from TEXT" in result.output
        assert "Source branch/commit to create worktree from" in result.output

    def test_from_flag_works_with_dynamic_command(self):
        """Test that --from flag works with dynamic branch command syntax (issue #71)."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            # Setup mocks
            mock_services = MockServices()
            mock_create_services.return_value = mock_services
            mock_config = Mock()
            mock_config.terminal.mode = "tab"
            mock_config.scripts.session_init = None
            mock_config.terminal.always_new = False
            mock_get_config.return_value = mock_config

            # Test: autowt my-sub-feature --from my-big-feature
            result = runner.invoke(main, ["my-sub-feature", "--from", "my-big-feature"])

            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, _ = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "my-sub-feature"
            assert switch_cmd.from_branch == "my-big-feature"
