"""Tests for terminal service init script functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

from autowt.models import TerminalMode
from autowt.services.terminal import TerminalService


class TestTerminalServiceInitScripts:
    """Tests for init script handling in terminal service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.terminal_service = TerminalService()
        self.test_path = Path("/test/worktree")
        self.init_script = "setup.sh"

    def test_change_directory_inplace_without_init_script(self, capsys):
        """Test inplace mode without init script."""
        success = self.terminal_service._change_directory_inplace(self.test_path)

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree"

    def test_change_directory_inplace_with_init_script(self, capsys):
        """Test inplace mode with init script."""
        success = self.terminal_service._change_directory_inplace(
            self.test_path, self.init_script
        )

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree; setup.sh"

    def test_change_directory_inplace_with_complex_script(self, capsys):
        """Test inplace mode with complex init script."""
        complex_script = "mise install && uv sync --extra=dev"
        success = self.terminal_service._change_directory_inplace(
            self.test_path, complex_script
        )

        captured = capsys.readouterr()
        assert success
        assert (
            captured.out.strip()
            == "cd /test/worktree; mise install && uv sync --extra=dev"
        )

    def test_switch_to_iterm_session_without_init_script(
        self, mock_terminal_operations
    ):
        """Test switching to iTerm session without init script."""
        self.terminal_service.is_iterm = True

        success = self.terminal_service._switch_to_iterm_session("test-session")

        assert success
        mock_terminal_operations["applescript"].assert_called_once()
        script = mock_terminal_operations["applescript"].call_args[0][0]
        assert "test-session" in script
        assert "write text" not in script  # No init script execution

    def test_switch_to_iterm_session_with_init_script(self, mock_terminal_operations):
        """Test switching to iTerm session with init script."""
        self.terminal_service.is_iterm = True

        success = self.terminal_service._switch_to_iterm_session(
            "test-session", "setup.sh"
        )

        assert success
        mock_terminal_operations["applescript"].assert_called_once()
        script = mock_terminal_operations["applescript"].call_args[0][0]
        assert "test-session" in script
        assert "write text" in script
        assert "setup.sh" in script

    def test_open_iterm_tab_without_init_script(self, mock_terminal_operations):
        """Test opening iTerm tab without init script."""
        success = self.terminal_service._open_iterm_tab(self.test_path)

        assert success
        mock_terminal_operations["applescript"].assert_called_once()
        script = mock_terminal_operations["applescript"].call_args[0][0]
        assert "cd /test/worktree" in script
        assert "setup.sh" not in script

    def test_open_iterm_tab_with_init_script(self, mock_terminal_operations):
        """Test opening iTerm tab with init script."""
        success = self.terminal_service._open_iterm_tab(
            self.test_path, self.init_script
        )

        assert success
        mock_terminal_operations["applescript"].assert_called_once()
        script = mock_terminal_operations["applescript"].call_args[0][0]
        assert "cd /test/worktree; setup.sh" in script

    def test_open_iterm_window_with_init_script(self, mock_terminal_operations):
        """Test opening iTerm window with init script."""
        success = self.terminal_service._open_iterm_window(
            self.test_path, self.init_script
        )

        assert success
        mock_terminal_operations["applescript"].assert_called_once()
        script = mock_terminal_operations["applescript"].call_args[0][0]
        assert "cd /test/worktree; setup.sh" in script

    def test_open_generic_terminal_with_init_script_gnome(
        self, mock_terminal_operations
    ):
        """Test opening gnome-terminal with init script."""
        mock_terminal_operations["platform"].return_value = "Linux"
        self.terminal_service.is_macos = False

        success = self.terminal_service._open_generic_terminal(
            self.test_path, self.init_script
        )

        assert success
        mock_terminal_operations["run_command"].assert_called_once()
        cmd = mock_terminal_operations["run_command"].call_args[0][0]
        assert "gnome-terminal" in cmd
        assert "--working-directory" in cmd
        assert str(self.test_path) in cmd
        assert "setup.sh" in " ".join(cmd)

    def test_open_generic_terminal_with_init_script_konsole(
        self, mock_terminal_operations
    ):
        """Test opening konsole with init script when gnome-terminal fails."""

        # Make gnome-terminal fail, konsole succeed
        def run_command_side_effect(cmd, **kwargs):
            if "gnome-terminal" in cmd:
                raise FileNotFoundError("gnome-terminal not found")
            return Mock(returncode=0)

        mock_terminal_operations["run_command"].side_effect = run_command_side_effect
        mock_terminal_operations["platform"].return_value = "Linux"
        self.terminal_service.is_macos = False

        success = self.terminal_service._open_generic_terminal(
            self.test_path, self.init_script
        )

        assert success
        # Should be called twice: once for gnome-terminal (fails), once for konsole (succeeds)
        assert mock_terminal_operations["run_command"].call_count == 2

        # Check the successful konsole call
        konsole_call = mock_terminal_operations["run_command"].call_args_list[1]
        cmd = konsole_call[0][0]
        assert "konsole" in cmd
        assert "setup.sh" in " ".join(cmd)

    def test_escape_for_applescript(self):
        """Test AppleScript string escaping."""
        # Test basic escaping
        result = self.terminal_service._escape_for_applescript('echo "hello"')
        assert result == 'echo \\"hello\\"'

        # Test backslash escaping
        result = self.terminal_service._escape_for_applescript("echo \\test")
        assert result == "echo \\\\test"

        # Test complex script
        complex_script = 'echo "test \\"nested\\" quotes" && ls \\'
        result = self.terminal_service._escape_for_applescript(complex_script)
        expected = 'echo \\"test \\\\\\"nested\\\\\\" quotes\\" && ls \\\\'
        assert result == expected

    def test_switch_to_worktree_delegates_correctly(self):
        """Test that switch_to_worktree passes init_script to appropriate methods."""
        with patch.object(
            self.terminal_service, "_change_directory_inplace"
        ) as mock_inplace:
            mock_inplace.return_value = True

            success = self.terminal_service.switch_to_worktree(
                self.test_path, TerminalMode.INPLACE, None, self.init_script
            )

            assert success
            mock_inplace.assert_called_once_with(self.test_path, self.init_script)

        with patch.object(self.terminal_service, "_open_new_tab") as mock_tab:
            mock_tab.return_value = True

            success = self.terminal_service.switch_to_worktree(
                self.test_path, TerminalMode.TAB, None, self.init_script
            )

            assert success
            mock_tab.assert_called_once_with(self.test_path, self.init_script)

        with patch.object(self.terminal_service, "_open_new_window") as mock_window:
            mock_window.return_value = True

            success = self.terminal_service.switch_to_worktree(
                self.test_path, TerminalMode.WINDOW, None, self.init_script
            )

            assert success
            mock_window.assert_called_once_with(self.test_path, self.init_script)

    def test_switch_to_existing_or_new_with_init_script(self):
        """Test switch_to_existing_or_new handles init scripts."""
        with (
            patch.object(
                self.terminal_service, "_switch_to_iterm_session"
            ) as mock_switch,
            patch.object(self.terminal_service, "_open_new_tab") as mock_tab,
        ):
            mock_switch.return_value = False  # Simulate session switch failure
            mock_tab.return_value = True
            self.terminal_service.is_iterm = True

            success = self.terminal_service._switch_to_existing_or_new(
                self.test_path, "session-id", self.init_script
            )

            assert success
            # Should try to switch to session first, then fall back to new tab
            mock_switch.assert_called_once_with("session-id", self.init_script)
            mock_tab.assert_called_once_with(self.test_path, self.init_script)


class TestInitScriptEdgeCases:
    """Test edge cases and error handling for init scripts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.terminal_service = TerminalService()
        self.test_path = Path("/test/worktree")

    def test_empty_init_script_treated_as_none(self, capsys):
        """Test that empty string init script is handled gracefully."""
        success = self.terminal_service._change_directory_inplace(self.test_path, "")

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree"

    def test_whitespace_only_init_script(self, capsys):
        """Test init script with only whitespace."""
        success = self.terminal_service._change_directory_inplace(self.test_path, "   ")

        captured = capsys.readouterr()
        assert success
        # The whitespace gets trimmed when joining commands
        assert captured.out.strip() == "cd /test/worktree;"

    def test_init_script_with_special_characters(self, capsys):
        """Test init script with special shell characters."""
        special_script = "echo 'test'; ls | grep '*.py' && echo $HOME"
        success = self.terminal_service._change_directory_inplace(
            self.test_path, special_script
        )

        captured = capsys.readouterr()
        assert success
        expected = f"cd /test/worktree; {special_script}"
        assert captured.out.strip() == expected

    def test_applescript_failure_with_init_script(self, mock_terminal_operations):
        """Test handling of AppleScript execution failure with init script."""
        mock_terminal_operations["applescript"].return_value = False

        success = self.terminal_service._open_iterm_tab(self.test_path, "setup.sh")

        assert not success
        mock_terminal_operations["applescript"].assert_called_once()

    def test_path_with_spaces_and_init_script(self, capsys):
        """Test handling paths with spaces combined with init scripts."""
        path_with_spaces = Path("/test/my worktree/branch")
        success = self.terminal_service._change_directory_inplace(
            path_with_spaces, "setup.sh"
        )

        captured = capsys.readouterr()
        assert success
        # Path should be properly quoted
        assert "'/test/my worktree/branch'" in captured.out
        assert "setup.sh" in captured.out
