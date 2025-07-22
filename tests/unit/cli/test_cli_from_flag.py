"""Tests for CLI --from flag functionality."""

from click.testing import CliRunner

from autowt.cli import main


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
