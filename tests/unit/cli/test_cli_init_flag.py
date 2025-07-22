"""Tests for CLI --init flag functionality."""

from click.testing import CliRunner

from autowt.cli import main


class TestCLIInitFlag:
    """Test the --init flag in CLI commands."""

    def test_switch_command_help_shows_init_option(self):
        """Test that --init option appears in switch command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["switch", "--help"])

        assert result.exit_code == 0
        assert "--init TEXT" in result.output
        assert "Init script to run in the new terminal" in result.output

    def test_dynamic_branch_command_help_shows_init_option(self):
        """Test that --init option appears in dynamic branch command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["test-branch", "--help"])

        assert result.exit_code == 0
        assert "--init TEXT" in result.output
        assert "Init script to run in the new terminal" in result.output
