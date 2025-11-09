"""Tests for terminal service init script functionality."""

from pathlib import Path
from unittest.mock import patch

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

    @patch("autowt.services.terminal.run_script_inplace")
    def test_inplace_commands_with_supported_terminal(
        self, mock_run_script, terminal_service, test_path, init_script
    ):
        """Test new inplace mode with mocked terminal execution."""
        mock_run_script.return_value = True

        success = terminal_service._inplace_commands(test_path, init_script)

        assert success
        mock_run_script.assert_called_once_with("cd /test/worktree; setup.sh")

    @patch("autowt.services.terminal.run_script_inplace")
    def test_inplace_commands_fallback_to_echo(
        self, mock_run_script, terminal_service, test_path, init_script, capsys
    ):
        """Test inplace mode falls back to echo when terminal doesn't support it."""
        mock_run_script.return_value = False

        success = terminal_service._inplace_commands(test_path, init_script)

        captured = capsys.readouterr()
        assert success
        assert captured.out.strip() == "cd /test/worktree; setup.sh"

    @patch("autowt.services.terminal.check")
    @patch("autowt.services.terminal.new_tab")
    def test_terminal_implementation_delegation_tab(
        self, mock_new_tab, mock_check, terminal_service, test_path, init_script
    ):
        """Test that TerminalService properly delegates to automate_terminal for tabs."""
        mock_check.return_value = {
            "capabilities": {
                "can_create_tabs": True,
                "can_paste_commands": True,
            }
        }
        mock_new_tab.return_value = True

        # Test tab creation delegation
        success = terminal_service._tab_mode(
            test_path, init_script, None, None, False, False
        )

        assert success
        mock_new_tab.assert_called_once_with(
            working_directory=str(test_path),
            paste_script=init_script,
        )

    @patch("autowt.services.terminal.check")
    @patch("autowt.services.terminal.new_window")
    def test_terminal_implementation_delegation_window(
        self, mock_new_window, mock_check, terminal_service, test_path, init_script
    ):
        """Test that TerminalService properly delegates to automate_terminal for windows."""
        mock_check.return_value = {
            "capabilities": {
                "can_create_windows": True,
                "can_paste_commands": True,
            }
        }
        mock_new_window.return_value = True

        # Test window creation delegation
        success = terminal_service._window_mode(
            test_path, init_script, None, None, False, False
        )

        assert success
        mock_new_window.assert_called_once_with(
            working_directory=str(test_path),
            paste_script=init_script,
        )

    def test_switch_to_worktree_delegates_correctly(
        self, terminal_service, test_path, init_script
    ):
        """Test that switch_to_worktree passes init_script to appropriate methods."""
        with patch.object(terminal_service, "_inplace_commands") as mock_inplace:
            mock_inplace.return_value = True

            success = terminal_service.switch_to_worktree(
                test_path, TerminalMode.INPLACE, init_script
            )

            assert success
            mock_inplace.assert_called_once_with(test_path, init_script, None)

        # Test ECHO mode delegation
        with patch.object(terminal_service, "_echo_commands") as mock_echo:
            mock_echo.return_value = True

            success = terminal_service.switch_to_worktree(
                test_path, TerminalMode.ECHO, init_script
            )

            assert success
            mock_echo.assert_called_once_with(test_path, init_script, None)

        # Test TAB mode delegation
        with patch.object(terminal_service, "_tab_mode") as mock_tab:
            mock_tab.return_value = True

            success = terminal_service.switch_to_worktree(
                test_path, TerminalMode.TAB, init_script
            )

            assert success
            # branch_name, auto_confirm, ignore_same_session default to None, False, False
            mock_tab.assert_called_once_with(
                test_path, init_script, None, None, False, False
            )

        # Test WINDOW mode delegation
        with patch.object(terminal_service, "_window_mode") as mock_window:
            mock_window.return_value = True

            success = terminal_service.switch_to_worktree(
                test_path, TerminalMode.WINDOW, init_script
            )

            assert success
            mock_window.assert_called_once_with(
                test_path, init_script, None, None, False, False
            )

    @patch("autowt.services.terminal.check")
    @patch("autowt.services.terminal.list_sessions")
    @patch("autowt.services.terminal.switch_to_session")
    @patch("autowt.services.terminal.new_tab")
    def test_tab_mode_with_existing_session(
        self,
        mock_new_tab,
        mock_switch,
        mock_list_sessions,
        mock_check,
        terminal_service,
        test_path,
        init_script,
    ):
        """Test tab mode handles switching to existing sessions."""
        mock_check.return_value = {
            "capabilities": {
                "can_create_tabs": True,
                "can_switch_to_session": True,
                "can_paste_commands": True,
            }
        }
        mock_list_sessions.return_value = [{"working_directory": str(test_path)}]
        mock_switch.return_value = True

        success = terminal_service._tab_mode(
            test_path,
            init_script,
            None,
            "test-branch",
            auto_confirm=True,  # Skip user prompt
            ignore_same_session=False,
        )

        assert success
        # Should switch to session, not create new tab
        mock_switch.assert_called_once_with(working_directory=str(test_path))
        mock_new_tab.assert_not_called()


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

    @patch("autowt.services.terminal.check")
    @patch("autowt.services.terminal.new_tab")
    def test_terminal_tab_creation_failure(
        self, mock_new_tab, mock_check, terminal_service, test_path
    ):
        """Test handling of tab creation failure with init script."""
        mock_check.return_value = {
            "capabilities": {
                "can_create_tabs": True,
                "can_paste_commands": True,
            }
        }
        mock_new_tab.return_value = False

        success = terminal_service._tab_mode(
            test_path, "setup.sh", None, None, False, False
        )

        assert not success
        mock_new_tab.assert_called_once()

    def test_path_with_spaces_and_init_script(self, terminal_service, capsys):
        """Test handling paths with spaces combined with init scripts in echo mode."""
        path_with_spaces = Path("/test/my worktree/branch")
        success = terminal_service._echo_commands(path_with_spaces, "setup.sh")

        captured = capsys.readouterr()
        assert success
        # Path should be properly quoted
        assert "'/test/my worktree/branch'" in captured.out
        assert "setup.sh" in captured.out

    def test_combine_scripts(self, terminal_service):
        """Test _combine_scripts helper method."""
        # Both scripts
        result = terminal_service._combine_scripts("script1", "script2")
        assert result == "script1; script2"

        # Only first script
        result = terminal_service._combine_scripts("script1", None)
        assert result == "script1"

        # Only second script
        result = terminal_service._combine_scripts(None, "script2")
        assert result == "script2"

        # No scripts
        result = terminal_service._combine_scripts(None, None)
        assert result is None
