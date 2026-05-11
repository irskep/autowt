"""Tests for prompt behavior under shell integration mode."""

from unittest.mock import patch

from autowt.global_config import options
from autowt.prompts import confirm


class TestConfirmShellIntegration:
    def setup_method(self):
        self._original_shell_integration = options.shell_integration
        self._original_auto_confirm = options.auto_confirm

    def teardown_method(self):
        options.shell_integration = self._original_shell_integration
        options.auto_confirm = self._original_auto_confirm

    def test_auto_confirm_writes_to_stderr_when_shell_integration(self, capsys):
        options.shell_integration = True
        options.auto_confirm = True

        result = confirm("Create worktree?")

        assert result is True
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "auto-confirmed" in captured.err

    def test_auto_confirm_writes_to_stdout_normally(self, capsys):
        options.shell_integration = False
        options.auto_confirm = True

        result = confirm("Create worktree?")

        assert result is True
        captured = capsys.readouterr()
        assert "auto-confirmed" in captured.out
        assert captured.err == ""

    @patch("builtins.input", return_value="y")
    def test_interactive_prompt_goes_to_stderr_when_shell_integration(
        self, mock_input, capsys
    ):
        options.shell_integration = True
        options.auto_confirm = False

        result = confirm("Create worktree?", default=True)

        assert result is True
        captured = capsys.readouterr()
        # Prompt should be on stderr, not stdout
        assert captured.out == ""
        assert "Create worktree?" in captured.err
        # input() called without prompt arg (we wrote it to stderr ourselves)
        mock_input.assert_called_once_with()

    @patch("builtins.input", return_value="y")
    def test_interactive_prompt_goes_to_stdout_normally(self, mock_input, capsys):
        options.shell_integration = False
        options.auto_confirm = False

        result = confirm("Create worktree?", default=True)

        assert result is True
        # input(prompt) writes prompt to stdout — but capsys doesn't capture
        # what input() writes, so we just verify input was called with the prompt
        mock_input.assert_called_once_with("Create worktree? (Y/n) ")
