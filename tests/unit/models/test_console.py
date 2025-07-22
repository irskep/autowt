"""Tests for console styling functionality."""

from unittest.mock import MagicMock

import pytest

from autowt.console import (
    AUTOWT_THEME,
    console,
    print_command,
    print_error,
    print_info,
    print_output,
    print_plain,
    print_prompt,
    print_section,
    print_success,
)
from autowt.console import console as console2
from autowt.global_config import options


@pytest.fixture
def mock_console(monkeypatch):
    """Fixture to mock the console for all print function tests."""
    mock = MagicMock()
    monkeypatch.setattr("autowt.console.console", mock)
    return mock


class TestConsoleTheme:
    """Test console theme configuration."""

    def test_theme_has_expected_styles(self):
        """Test that the theme contains all expected autowt styles."""
        expected_autowt_styles = {
            "command",
            "output",
            "prompt",
            "section",
            "success",
            "warning",
            "error",
            "info",
        }

        theme_styles = set(AUTOWT_THEME.styles.keys())
        assert expected_autowt_styles.issubset(theme_styles)

    def test_command_and_output_use_same_style(self):
        """Test that command and output styles are both gray."""
        command_style = AUTOWT_THEME.styles["command"]
        output_style = AUTOWT_THEME.styles["output"]
        assert command_style == output_style
        assert str(command_style) == "dim grey50"


class TestConsolePrintFunctions:
    """Test console wrapper functions using pytest parametrization."""

    @pytest.mark.parametrize(
        "function,input_text,expected_call",
        [
            (print_command, "git status", ("> git status", {"style": "command"})),
            (print_section, "Test Section", ("Test Section", {"style": "section"})),
            (print_prompt, "Continue? [y/N]", ("Continue? [y/N]", {"style": "prompt"})),
            (
                print_success,
                "✓ Operation completed",
                ("✓ Operation completed", {"style": "success"}),
            ),
            (
                print_error,
                "✗ Operation failed",
                ("✗ Operation failed", {"style": "error"}),
            ),
            (print_info, "Info message", ("Info message", {"style": "info"})),
            (
                print_output,
                "  Sending SIGINT to process (PID 1234)",
                ("  Sending SIGINT to process (PID 1234)", {"style": "output"}),
            ),
            (print_plain, "Plain text", ("Plain text", {})),
        ],
    )
    def test_print_functions_use_correct_style(
        self, mock_console, function, input_text, expected_call
    ):
        """Test that print functions use the correct style and formatting."""
        function(input_text)

        expected_text, expected_kwargs = expected_call
        if expected_kwargs:
            mock_console.print.assert_called_once_with(expected_text, **expected_kwargs)
        else:
            mock_console.print.assert_called_once_with(expected_text)

    def test_output_suppression_when_enabled(self, mock_console):
        """Test that rich output can be suppressed via global option."""
        # Test normal output first
        print_info("Test info message")
        mock_console.print.assert_called_with("Test info message", style="info")
        mock_console.reset_mock()

        # Test suppressed output
        original_suppress = options.suppress_rich_output
        options.suppress_rich_output = True
        try:
            print_info("Suppressed info")
            print_success("Suppressed success")
            print_error("Suppressed error")
            # Should have no console.print calls when suppressed
            mock_console.print.assert_not_called()
        finally:
            options.suppress_rich_output = original_suppress


class TestConsoleIntegration:
    """Test console integration with rich."""

    def test_console_is_singleton(self):
        """Test that console is a singleton instance."""
        assert console is console2
