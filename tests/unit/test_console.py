"""Tests for console styling functionality."""

import unittest
from unittest.mock import MagicMock, patch

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


class TestConsoleTheme(unittest.TestCase):
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
        # Check that all our custom styles are present
        self.assertTrue(expected_autowt_styles.issubset(theme_styles))

    def test_command_and_output_use_same_style(self):
        """Test that command and output styles are both gray."""
        command_style = AUTOWT_THEME.styles["command"]
        output_style = AUTOWT_THEME.styles["output"]
        self.assertEqual(command_style, output_style)
        self.assertEqual(str(command_style), "dim grey50")


class TestConsoleFunctions(unittest.TestCase):
    """Test console wrapper functions."""

    def setUp(self):
        """Set up test mocks."""
        self.mock_console = MagicMock()

    @patch("autowt.console.console")
    def test_print_command_formats_with_prefix(self, mock_console):
        """Test that print_command adds > prefix and uses command style."""
        print_command("git status")
        mock_console.print.assert_called_once_with("> git status", style="command")

    @patch("autowt.console.console")
    def test_print_section_uses_section_style(self, mock_console):
        """Test that print_section uses section style."""
        print_section("Test Section")
        mock_console.print.assert_called_once_with("Test Section", style="section")

    @patch("autowt.console.console")
    def test_print_prompt_uses_prompt_style(self, mock_console):
        """Test that print_prompt uses prompt style."""
        print_prompt("Continue? [y/N]")
        mock_console.print.assert_called_once_with("Continue? [y/N]", style="prompt")

    @patch("autowt.console.console")
    def test_print_success_uses_success_style(self, mock_console):
        """Test that print_success uses success style."""
        print_success("✓ Operation completed")
        mock_console.print.assert_called_once_with(
            "✓ Operation completed", style="success"
        )

    @patch("autowt.console.console")
    def test_print_error_uses_error_style(self, mock_console):
        """Test that print_error uses error style."""
        print_error("✗ Operation failed")
        mock_console.print.assert_called_once_with("✗ Operation failed", style="error")

    @patch("autowt.console.console")
    def test_print_output_uses_output_style(self, mock_console):
        """Test that print_output uses output style."""
        print_output("  Sending SIGINT to process (PID 1234)")
        mock_console.print.assert_called_once_with(
            "  Sending SIGINT to process (PID 1234)", style="output"
        )

    @patch("autowt.console.console")
    def test_print_plain_no_style(self, mock_console):
        """Test that print_plain uses no style."""
        print_plain("Plain text")
        mock_console.print.assert_called_once_with("Plain text")

    @patch("autowt.console.console")
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


class TestConsoleIntegration(unittest.TestCase):
    """Test console integration with rich."""

    def test_console_is_singleton(self):
        """Test that console is a singleton instance."""
        self.assertIs(console, console2)


if __name__ == "__main__":
    unittest.main()
