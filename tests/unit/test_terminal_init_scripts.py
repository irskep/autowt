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

    def test_echo_commands_without_init_script(self, capsys):
        """Test echo mode without init script."""
        success = self.terminal_service._echo_commands(self.test_path)

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree"

    def test_echo_commands_with_init_script(self, capsys):
        """Test echo mode with init script."""
        success = self.terminal_service._echo_commands(self.test_path, self.init_script)

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree; setup.sh"

    def test_echo_commands_with_complex_script(self, capsys):
        """Test echo mode with complex init script."""
        complex_script = "mise install && uv sync --extra=dev"
        success = self.terminal_service._echo_commands(self.test_path, complex_script)

        captured = capsys.readouterr()
        assert success
        assert (
            captured.out.strip()
            == "cd /test/worktree; mise install && uv sync --extra=dev"
        )

    def test_change_directory_inplace_with_mock_terminal(self):
        """Test new inplace mode with mocked terminal execution."""
        # Mock terminal with execute_in_current_session method
        mock_terminal = Mock()
        mock_terminal.execute_in_current_session.return_value = True
        self.terminal_service.terminal = mock_terminal

        success = self.terminal_service._change_directory_inplace(
            self.test_path, self.init_script
        )

        assert success
        mock_terminal.execute_in_current_session.assert_called_once_with(
            "cd /test/worktree; setup.sh"
        )

    def test_change_directory_inplace_fallback_to_echo(self, capsys):
        """Test inplace mode falls back to echo when terminal doesn't support it."""
        # Mock terminal without execute_in_current_session method
        mock_terminal = Mock()
        # Explicitly set the method to not exist by using spec
        mock_terminal = Mock(spec=[])  # Empty spec means no methods/attributes
        self.terminal_service.terminal = mock_terminal

        success = self.terminal_service._change_directory_inplace(
            self.test_path, self.init_script
        )

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree; setup.sh"

    def test_terminal_implementation_delegation(self):
        """Test that TerminalService properly delegates to terminal implementations."""
        # Mock the terminal implementation
        mock_terminal = Mock()
        mock_terminal.open_new_tab.return_value = True
        mock_terminal.open_new_window.return_value = True
        mock_terminal.switch_to_session.return_value = True
        mock_terminal.supports_session_management.return_value = True

        # Replace the terminal with our mock
        self.terminal_service.terminal = mock_terminal

        # Test tab creation delegation
        success = self.terminal_service._switch_to_existing_or_new_tab(
            self.test_path, None, self.init_script, None, False
        )

        assert success
        mock_terminal.open_new_tab.assert_called_once_with(
            self.test_path, self.init_script
        )

        # Test window creation delegation
        mock_terminal.reset_mock()
        success = self.terminal_service._switch_to_existing_or_new_window(
            self.test_path, None, self.init_script, None, None, False
        )

        assert success
        mock_terminal.open_new_window.assert_called_once_with(
            self.test_path, self.init_script
        )

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
            mock_inplace.assert_called_once_with(self.test_path, self.init_script, None)

        # Test ECHO mode delegation
        with patch.object(self.terminal_service, "_echo_commands") as mock_echo:
            mock_echo.return_value = True

            success = self.terminal_service.switch_to_worktree(
                self.test_path, TerminalMode.ECHO, None, self.init_script
            )

            assert success
            mock_echo.assert_called_once_with(self.test_path, self.init_script, None)

        # Mock the terminal implementation to test delegation
        mock_terminal = Mock()
        mock_terminal.open_new_tab.return_value = True
        mock_terminal.open_new_window.return_value = True
        mock_terminal.supports_session_management.return_value = False
        self.terminal_service.terminal = mock_terminal

        # Test TAB mode delegation
        success = self.terminal_service.switch_to_worktree(
            self.test_path, TerminalMode.TAB, None, self.init_script
        )

        assert success
        mock_terminal.open_new_tab.assert_called_once_with(
            self.test_path, self.init_script
        )

        # Test WINDOW mode delegation
        mock_terminal.reset_mock()
        success = self.terminal_service.switch_to_worktree(
            self.test_path, TerminalMode.WINDOW, None, self.init_script
        )

        assert success
        mock_terminal.open_new_window.assert_called_once_with(
            self.test_path, self.init_script
        )

    def test_switch_to_existing_or_new_tab_with_init_script(self):
        """Test switch_to_existing_or_new_tab handles init scripts."""
        # Mock the terminal implementation
        mock_terminal = Mock()
        mock_terminal.switch_to_session.return_value = (
            False  # Simulate session switch failure
        )
        mock_terminal.open_new_tab.return_value = True
        mock_terminal.supports_session_management.return_value = True
        self.terminal_service.terminal = mock_terminal

        with patch.object(
            self.terminal_service, "_should_switch_to_existing"
        ) as mock_should_switch:
            mock_should_switch.return_value = True  # User wants to switch

            success = self.terminal_service._switch_to_existing_or_new_tab(
                self.test_path,
                "session-id",
                self.init_script,
                None,
                "test-branch",
                False,
            )

            assert success
            # Should try to switch to session first (no init script), then fall back to new tab
            mock_should_switch.assert_called_once_with("test-branch")
            mock_terminal.switch_to_session.assert_called_once_with(
                "session-id",
                None,  # No init script when switching to existing session
            )
            mock_terminal.open_new_tab.assert_called_once_with(
                self.test_path, self.init_script
            )


class TestInitScriptEdgeCases:
    """Test edge cases and error handling for init scripts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.terminal_service = TerminalService()
        self.test_path = Path("/test/worktree")

    def test_empty_init_script_treated_as_none(self, capsys):
        """Test that empty string init script is handled gracefully in echo mode."""
        success = self.terminal_service._echo_commands(self.test_path, "")

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree"

    def test_whitespace_only_init_script(self, capsys):
        """Test init script with only whitespace in echo mode."""
        success = self.terminal_service._echo_commands(self.test_path, "   ")

        captured = capsys.readouterr()
        assert success
        # The whitespace gets trimmed when joining commands
        assert captured.out.strip() == "cd /test/worktree;"

    def test_init_script_with_special_characters(self, capsys):
        """Test init script with special shell characters in echo mode."""
        special_script = "echo 'test'; ls | grep '*.py' && echo $HOME"
        success = self.terminal_service._echo_commands(self.test_path, special_script)

        captured = capsys.readouterr()
        assert success
        expected = f"cd /test/worktree; {special_script}"
        assert captured.out.strip() == expected

    def test_terminal_implementation_applescript_failure(
        self, mock_terminal_operations
    ):
        """Test handling of AppleScript execution failure with init script."""
        mock_terminal_operations["applescript"].return_value = False

        # Mock the terminal implementation
        mock_terminal = Mock()
        mock_terminal.open_new_tab.return_value = False  # Simulate failure
        mock_terminal.supports_session_management.return_value = False
        self.terminal_service.terminal = mock_terminal

        success = self.terminal_service._switch_to_existing_or_new_tab(
            self.test_path, None, "setup.sh", None, False
        )

        assert not success
        mock_terminal.open_new_tab.assert_called_once_with(self.test_path, "setup.sh")

    def test_path_with_spaces_and_init_script(self, capsys):
        """Test handling paths with spaces combined with init scripts in echo mode."""
        path_with_spaces = Path("/test/my worktree/branch")
        success = self.terminal_service._echo_commands(path_with_spaces, "setup.sh")

        captured = capsys.readouterr()
        assert success
        # Path should be properly quoted
        assert "'/test/my worktree/branch'" in captured.out
        assert "setup.sh" in captured.out
