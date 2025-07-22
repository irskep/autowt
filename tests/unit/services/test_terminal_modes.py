"""Tests for new terminal mode functionality (ECHO and INPLACE)."""

from pathlib import Path
from unittest.mock import Mock, patch

from autowt.models import TerminalMode
from autowt.services.terminal import (
    ITerm2Terminal,
    TerminalAppTerminal,
    TerminalService,
)
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
                self.test_path, TerminalMode.ECHO, None, self.init_script
            )

            assert success
            mock_echo.assert_called_once_with(self.test_path, self.init_script, None)

    def test_switch_to_worktree_inplace_mode(self):
        """Test switch_to_worktree with INPLACE mode."""
        with patch.object(
            self.terminal_service, "_change_directory_inplace"
        ) as mock_inplace:
            mock_inplace.return_value = True

            success = self.terminal_service.switch_to_worktree(
                self.test_path, TerminalMode.INPLACE, None, self.init_script
            )

            assert success
            mock_inplace.assert_called_once_with(self.test_path, self.init_script, None)

    def test_switch_to_worktree_unknown_mode(self):
        """Test switch_to_worktree with unknown mode."""
        # Mock an unknown mode
        unknown_mode = "unknown"

        success = self.terminal_service.switch_to_worktree(
            self.test_path, unknown_mode, None, self.init_script
        )

        assert not success


class TestITerm2Terminal:
    """Tests for iTerm2 terminal execute_in_current_session method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.terminal = ITerm2Terminal()

    def test_execute_in_current_session_success(self):
        """Test successful command execution in iTerm2."""
        command = "cd /test/worktree; setup.sh"

        with patch.object(self.terminal, "_run_applescript") as mock_applescript:
            mock_applescript.return_value = True

            success = self.terminal.execute_in_current_session(command)

            assert success
            mock_applescript.assert_called_once()

            # Check that the applescript contains the expected command
            call_args = mock_applescript.call_args[0][0]
            assert "write text" in call_args
            assert "cd /test/worktree; setup.sh" in call_args

    def test_execute_in_current_session_failure(self):
        """Test failed command execution in iTerm2."""
        command = "cd /test/worktree"

        with patch.object(self.terminal, "_run_applescript") as mock_applescript:
            mock_applescript.return_value = False

            success = self.terminal.execute_in_current_session(command)

            assert not success
            mock_applescript.assert_called_once()

    def test_execute_in_current_session_escapes_command(self):
        """Test that special characters in command are properly escaped."""
        command = 'cd "/test/path with spaces"; echo "hello world"'

        with patch.object(self.terminal, "_run_applescript") as mock_applescript:
            mock_applescript.return_value = True

            self.terminal.execute_in_current_session(command)

            # Check that the command was escaped
            call_args = mock_applescript.call_args[0][0]
            assert '\\"' in call_args  # Quotes should be escaped


class TestTerminalAppTerminal:
    """Tests for Terminal.app execute_in_current_session method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.terminal = TerminalAppTerminal()

    def test_execute_in_current_session_success(self):
        """Test successful command execution in Terminal.app."""
        command = "cd /test/worktree; setup.sh"

        with patch.object(self.terminal, "_run_applescript") as mock_applescript:
            mock_applescript.return_value = True

            success = self.terminal.execute_in_current_session(command)

            assert success
            mock_applescript.assert_called_once()

            # Check that the applescript contains the expected command
            call_args = mock_applescript.call_args[0][0]
            assert "do script" in call_args
            assert "selected tab of front window" in call_args
            assert "cd /test/worktree; setup.sh" in call_args

    def test_execute_in_current_session_failure(self):
        """Test failed command execution in Terminal.app."""
        command = "cd /test/worktree"

        with patch.object(self.terminal, "_run_applescript") as mock_applescript:
            mock_applescript.return_value = False

            success = self.terminal.execute_in_current_session(command)

            assert not success
            mock_applescript.assert_called_once()


class TestTerminalModeIntegration:
    """Integration tests for terminal modes with different terminals."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_state_service = MockStateService()
        self.terminal_service = TerminalService(self.mock_state_service)
        self.test_path = Path("/test/worktree")

    def test_inplace_mode_with_iterm2_terminal(self):
        """Test inplace mode with iTerm2 terminal."""
        # Mock iTerm2 terminal
        mock_terminal = Mock(spec=ITerm2Terminal)
        mock_terminal.execute_in_current_session.return_value = True
        self.terminal_service.terminal = mock_terminal

        success = self.terminal_service._change_directory_inplace(
            self.test_path, "setup.sh"
        )

        assert success
        mock_terminal.execute_in_current_session.assert_called_once_with(
            "cd /test/worktree; setup.sh"
        )

    def test_inplace_mode_with_terminal_app(self):
        """Test inplace mode with Terminal.app."""
        # Mock Terminal.app terminal
        mock_terminal = Mock(spec=TerminalAppTerminal)
        mock_terminal.execute_in_current_session.return_value = True
        self.terminal_service.terminal = mock_terminal

        success = self.terminal_service._change_directory_inplace(
            self.test_path, "setup.sh"
        )

        assert success
        mock_terminal.execute_in_current_session.assert_called_once_with(
            "cd /test/worktree; setup.sh"
        )

    def test_inplace_mode_fallback_for_unsupported_terminal(self, capsys):
        """Test inplace mode falls back to echo for unsupported terminals."""
        # Mock a terminal without execute_in_current_session
        mock_terminal = Mock(spec=[])  # Empty spec means no methods/attributes
        self.terminal_service.terminal = mock_terminal

        success = self.terminal_service._change_directory_inplace(
            self.test_path, "setup.sh"
        )

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree; setup.sh"
