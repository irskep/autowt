"""Tests for CLI --init flag functionality."""

from click.testing import CliRunner

from autowt.cli import main


class TestCLIInitFlag:
    """Test the --init flag in CLI commands."""

    def test_switch_command_has_init_option(self):
        """Test that --init option is available in switch command."""
        runner = CliRunner()
        result = runner.invoke(main, ["switch", "--help"])

        assert result.exit_code == 0
        assert "--init" in result.output

    def test_dynamic_branch_command_has_init_option(self):
        """Test that --init option is available in dynamic branch command."""
        runner = CliRunner()
        result = runner.invoke(main, ["test-branch", "--help"])

        assert result.exit_code == 0
        assert "--init" in result.output
