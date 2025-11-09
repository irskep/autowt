"""Tests for new terminal mode functionality (ECHO and INPLACE)."""

from pathlib import Path
from unittest.mock import Mock, patch

from autowt.models import TerminalMode
from autowt.services.terminal import TerminalService, run_script_inplace
from tests.fixtures.service_builders import MockStateService


class TestTerminalModes:
    """Tests for ECHO and INPLACE terminal modes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_state_service = MockStateService()
        self.terminal_service = TerminalService(self.mock_state_service)
        self.test_path = Path("/test/worktree")
        self.init_script = "setup.sh"

    def test_switch_to_worktree_echo_mode(self):
        """Test switch_to_worktree with ECHO mode."""
        with patch.object(self.terminal_service, "_echo_commands") as mock_echo:
            mock_echo.return_value = True

            success = self.terminal_service.switch_to_worktree(
                self.test_path, TerminalMode.ECHO, self.init_script
            )

            assert success
            mock_echo.assert_called_once_with(self.test_path, self.init_script, None)

    def test_switch_to_worktree_inplace_mode(self):
        """Test switch_to_worktree with INPLACE mode."""
        with patch.object(self.terminal_service, "_inplace_commands") as mock_inplace:
            mock_inplace.return_value = True

            success = self.terminal_service.switch_to_worktree(
                self.test_path, TerminalMode.INPLACE, self.init_script
            )

            assert success
            mock_inplace.assert_called_once_with(self.test_path, self.init_script, None)

    def test_switch_to_worktree_unknown_mode(self):
        """Test switch_to_worktree with unknown mode."""
        # Mock an unknown mode
        unknown_mode = "unknown"

        success = self.terminal_service.switch_to_worktree(
            self.test_path, unknown_mode, self.init_script
        )

        assert not success


class TestInplaceExecution:
    """Tests for run_script_inplace function."""

    @patch("autowt.services.terminal.run_command")
    @patch.dict("os.environ", {"TERM_PROGRAM": "iTerm.app"})
    def test_run_script_inplace_iterm2_success(self, mock_run_command):
        """Test successful command execution in iTerm2."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_command.return_value = mock_result

        command = "cd /test/worktree; setup.sh"
        success = run_script_inplace(command)

        assert success
        mock_run_command.assert_called_once()
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "osascript"
        assert "write text" in call_args[2]

    @patch("autowt.services.terminal.run_command")
    @patch.dict("os.environ", {"TERM_PROGRAM": "Apple_Terminal"})
    def test_run_script_inplace_terminal_app_success(self, mock_run_command):
        """Test successful command execution in Terminal.app."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_command.return_value = mock_result

        command = "cd /test/worktree; setup.sh"
        success = run_script_inplace(command)

        assert success
        mock_run_command.assert_called_once()
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "osascript"
        assert "do script" in call_args[2]

    @patch.dict("os.environ", {"TERM_PROGRAM": "unsupported"})
    def test_run_script_inplace_unsupported_terminal(self):
        """Test unsupported terminal returns False."""
        command = "cd /test/worktree"
        success = run_script_inplace(command)

        assert not success

    @patch("autowt.services.terminal.run_command")
    @patch.dict("os.environ", {"TERM_PROGRAM": "iTerm.app"})
    def test_run_script_inplace_escapes_command(self, mock_run_command):
        """Test that special characters in command are properly escaped."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_command.return_value = mock_result

        command = 'cd "/test/path with spaces"; echo "hello world"'
        run_script_inplace(command)

        # Check that the command was escaped
        call_args = mock_run_command.call_args[0][0]
        assert '\\"' in call_args[2]  # Quotes should be escaped


class TestTerminalModeIntegration:
    """Integration tests for terminal modes with different terminals."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_state_service = MockStateService()
        self.terminal_service = TerminalService(self.mock_state_service)
        self.test_path = Path("/test/worktree")

    @patch("autowt.services.terminal.run_script_inplace")
    def test_inplace_mode_with_supported_terminal(self, mock_run_script):
        """Test inplace mode with supported terminal."""
        mock_run_script.return_value = True

        success = self.terminal_service._inplace_commands(self.test_path, "setup.sh")

        assert success
        mock_run_script.assert_called_once_with("cd /test/worktree; setup.sh")

    @patch("autowt.services.terminal.run_script_inplace")
    def test_inplace_mode_fallback_for_unsupported_terminal(
        self, mock_run_script, capsys
    ):
        """Test inplace mode falls back to echo for unsupported terminals."""
        mock_run_script.return_value = False

        success = self.terminal_service._inplace_commands(self.test_path, "setup.sh")

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree; setup.sh"
