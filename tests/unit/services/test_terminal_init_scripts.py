"""Tests for terminal service init script functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from autowt.models import TerminalMode
from autowt.services.terminal import TerminalService
from tests.fixtures.service_builders import MockStateService


@pytest.fixture
def mock_state_service():
    """Mock state service for testing."""
    return MockStateService()


@pytest.fixture
def terminal_service(mock_state_service):
    """Terminal service with mocked dependencies."""
    return TerminalService(mock_state_service)


@pytest.fixture
def test_path():
    """Test worktree path."""
    return Path("/test/worktree")


@pytest.fixture
def init_script():
    """Sample init script."""
    return "setup.sh"


class TestTerminalServiceInitScripts:
    """Tests for init script handling in terminal service."""

    @pytest.mark.parametrize(
        "script,expected_output",
        [
            (None, "cd /test/worktree"),
            ("setup.sh", "cd /test/worktree; setup.sh"),
            (
                "mise install && uv sync --extra=dev",
                "cd /test/worktree; mise install && uv sync --extra=dev",
            ),
        ],
    )
    def test_echo_commands(
        self, terminal_service, test_path, capsys, script, expected_output
    ):
        """Test echo mode with various init script configurations."""
        success = terminal_service._echo_commands(test_path, script)

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == expected_output

    def test_change_directory_inplace_with_mock_terminal(
        self, terminal_service, test_path, init_script
    ):
        """Test new inplace mode with mocked terminal execution."""
        # Mock terminal with execute_in_current_session method
        mock_terminal = Mock()
        mock_terminal.execute_in_current_session.return_value = True
        terminal_service.terminal = mock_terminal

        success = terminal_service._change_directory_inplace(test_path, init_script)

        assert success
        mock_terminal.execute_in_current_session.assert_called_once_with(
            "cd /test/worktree; setup.sh"
        )

    def test_change_directory_inplace_fallback_to_echo(
        self, terminal_service, test_path, init_script, capsys
    ):
        """Test inplace mode falls back to echo when terminal doesn't support it."""
        # Mock terminal without execute_in_current_session method
        mock_terminal = Mock(spec=[])  # Empty spec means no methods/attributes
        terminal_service.terminal = mock_terminal

        success = terminal_service._change_directory_inplace(test_path, init_script)

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree; setup.sh"

    def test_terminal_implementation_delegation(
        self, terminal_service, test_path, init_script
    ):
        """Test that TerminalService properly delegates to terminal implementations."""
        # Mock the terminal implementation
        mock_terminal = Mock()
        mock_terminal.open_new_tab.return_value = True
        mock_terminal.open_new_window.return_value = True
        mock_terminal.switch_to_session.return_value = True
        mock_terminal.supports_session_management.return_value = True

        # Replace the terminal with our mock
        terminal_service.terminal = mock_terminal

        # Test tab creation delegation
        success = terminal_service._switch_to_existing_or_new_tab(
            test_path, None, init_script, None, False
        )

        assert success
        mock_terminal.open_new_tab.assert_called_once_with(test_path, init_script)

        # Test window creation delegation
        mock_terminal.reset_mock()
        success = terminal_service._switch_to_existing_or_new_window(
            test_path, None, init_script, None, None, False
        )

        assert success
        mock_terminal.open_new_window.assert_called_once_with(test_path, init_script)

    def test_switch_to_worktree_delegates_correctly(
        self, terminal_service, test_path, init_script
    ):
        """Test that switch_to_worktree passes init_script to appropriate methods."""
        with patch.object(
            terminal_service, "_change_directory_inplace"
        ) as mock_inplace:
            mock_inplace.return_value = True

            success = terminal_service.switch_to_worktree(
                test_path, TerminalMode.INPLACE, None, init_script
            )

            assert success
            mock_inplace.assert_called_once_with(test_path, init_script, None)

        # Test ECHO mode delegation
        with patch.object(terminal_service, "_echo_commands") as mock_echo:
            mock_echo.return_value = True

            success = terminal_service.switch_to_worktree(
                test_path, TerminalMode.ECHO, None, init_script
            )

            assert success
            mock_echo.assert_called_once_with(test_path, init_script, None)

        # Mock the terminal implementation to test delegation
        mock_terminal = Mock()
        mock_terminal.open_new_tab.return_value = True
        mock_terminal.open_new_window.return_value = True
        mock_terminal.supports_session_management.return_value = False
        terminal_service.terminal = mock_terminal

        # Test TAB mode delegation
        success = terminal_service.switch_to_worktree(
            test_path, TerminalMode.TAB, None, init_script
        )

        assert success
        mock_terminal.open_new_tab.assert_called_once_with(test_path, init_script)

        # Test WINDOW mode delegation
        mock_terminal.reset_mock()
        success = terminal_service.switch_to_worktree(
            test_path, TerminalMode.WINDOW, None, init_script
        )

        assert success
        mock_terminal.open_new_window.assert_called_once_with(test_path, init_script)

    def test_switch_to_existing_or_new_tab_with_init_script(
        self, terminal_service, test_path, init_script
    ):
        """Test switch_to_existing_or_new_tab handles init scripts."""
        # Mock the terminal implementation
        mock_terminal = Mock()
        mock_terminal.switch_to_session.return_value = (
            False  # Simulate session switch failure
        )
        mock_terminal.open_new_tab.return_value = True
        mock_terminal.supports_session_management.return_value = True
        terminal_service.terminal = mock_terminal

        with patch.object(
            terminal_service, "_should_switch_to_existing"
        ) as mock_should_switch:
            mock_should_switch.return_value = True  # User wants to switch

            success = terminal_service._switch_to_existing_or_new_tab(
                test_path,
                "session-id",
                init_script,
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
            mock_terminal.open_new_tab.assert_called_once_with(test_path, init_script)


class TestInitScriptEdgeCases:
    """Test edge cases and error handling for init scripts."""

    def test_empty_init_script_treated_as_none(
        self, terminal_service, test_path, capsys
    ):
        """Test that empty string init script is handled gracefully in echo mode."""
        success = terminal_service._echo_commands(test_path, "")

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree"

    def test_whitespace_only_init_script(self, terminal_service, test_path, capsys):
        """Test init script with only whitespace in echo mode."""
        success = terminal_service._echo_commands(test_path, "   ")

        captured = capsys.readouterr()
        assert success
        # The whitespace gets trimmed and filtered out, leaving only the cd command
        assert captured.out.strip() == "cd /test/worktree"

    def test_init_script_with_special_characters(
        self, terminal_service, test_path, capsys
    ):
        """Test init script with special shell characters in echo mode."""
        special_script = "echo 'test'; ls | grep '*.py' && echo $HOME"
        success = terminal_service._echo_commands(test_path, special_script)

        captured = capsys.readouterr()
        assert success
        expected = f"cd /test/worktree; {special_script}"
        assert captured.out.strip() == expected

    def test_multiline_init_script(self, terminal_service, test_path, capsys):
        """Test multi-line init script gets normalized to single line in echo mode."""
        multiline_script = "echo 'line1'\necho 'line2'\necho 'line3'"
        success = terminal_service._echo_commands(test_path, multiline_script)

        captured = capsys.readouterr()
        assert success
        expected = "cd /test/worktree; echo 'line1'; echo 'line2'; echo 'line3'"
        assert captured.out.strip() == expected

    def test_terminal_implementation_applescript_failure(
        self, terminal_service, test_path, mock_terminal_operations
    ):
        """Test handling of AppleScript execution failure with init script."""
        mock_terminal_operations["applescript"].return_value = False

        # Mock the terminal implementation
        mock_terminal = Mock()
        mock_terminal.open_new_tab.return_value = False  # Simulate failure
        mock_terminal.supports_session_management.return_value = False
        terminal_service.terminal = mock_terminal

        success = terminal_service._switch_to_existing_or_new_tab(
            test_path, None, "setup.sh", None, False
        )

        assert not success
        mock_terminal.open_new_tab.assert_called_once_with(test_path, "setup.sh")

    def test_path_with_spaces_and_init_script(self, terminal_service, capsys):
        """Test handling paths with spaces combined with init scripts in echo mode."""
        path_with_spaces = Path("/test/my worktree/branch")
        success = terminal_service._echo_commands(path_with_spaces, "setup.sh")

        captured = capsys.readouterr()
        assert success
        # Path should be properly quoted
        assert "'/test/my worktree/branch'" in captured.out
        assert "setup.sh" in captured.out
