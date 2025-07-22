"""Tests for agent switching functionality with CLI options."""

from unittest.mock import patch

from click.testing import CliRunner

from autowt.cli import main
from autowt.models import SwitchCommand, TerminalMode
from tests.fixtures.service_builders import MockServices


class TestAgentSwitching:
    """Tests for unified agent switching with CLI options."""

    def test_switch_waiting_with_terminal_option(self):
        """Test that --waiting supports --terminal option."""
        runner = CliRunner()

        with patch("autowt.cli.create_services") as mock_create_services:
            # Setup mock services
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Mock find_waiting_agent_branch to return a branch
            with patch("autowt.cli.find_waiting_agent_branch") as mock_find_waiting:
                mock_find_waiting.return_value = "feature-branch"

                with patch("autowt.cli.checkout_branch") as mock_checkout:
                    result = runner.invoke(
                        main, ["switch", "--waiting", "--terminal", "window"]
                    )

                    if result.exit_code != 0:
                        print(f"Exit code: {result.exit_code}")
                        print(f"Output: {result.output}")
                        print(f"Exception: {result.exception}")
                    assert result.exit_code == 0
                    mock_find_waiting.assert_called_once()
                    mock_checkout.assert_called_once()

                    # Verify the SwitchCommand was created with correct options
                    args, kwargs = mock_checkout.call_args
                    switch_cmd = args[0]
                    assert isinstance(switch_cmd, SwitchCommand)
                    assert switch_cmd.branch == "feature-branch"
                    assert switch_cmd.terminal_mode == TerminalMode.WINDOW

    def test_switch_latest_with_init_script(self):
        """Test that --latest supports --init option."""
        runner = CliRunner()

        with patch("autowt.cli.create_services") as mock_create_services:
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            with patch("autowt.cli.find_latest_agent_branch") as mock_find_latest:
                mock_find_latest.return_value = "hotfix-branch"

                with patch("autowt.cli.checkout_branch") as mock_checkout:
                    result = runner.invoke(
                        main, ["switch", "--latest", "--init", "npm install"]
                    )

                    assert result.exit_code == 0
                    mock_find_latest.assert_called_once()
                    mock_checkout.assert_called_once()

                    # Verify checkout was called (init script comes from config + CLI overrides)
                    # This tests that the CLI overrides system works for agent switches
                    args, kwargs = mock_checkout.call_args
                    assert args[0].branch == "hotfix-branch"

    def test_switch_waiting_with_after_init(self):
        """Test that --waiting supports --after-init option."""
        runner = CliRunner()

        with patch("autowt.cli.create_services") as mock_create_services:
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            with patch("autowt.cli.find_waiting_agent_branch") as mock_find_waiting:
                mock_find_waiting.return_value = "feature-ai"

                with patch("autowt.cli.checkout_branch") as mock_checkout:
                    result = runner.invoke(
                        main, ["switch", "--waiting", "--after-init", "npm start"]
                    )

                    assert result.exit_code == 0
                    mock_checkout.assert_called_once()

                    args, kwargs = mock_checkout.call_args
                    switch_cmd = args[0]
                    assert switch_cmd.after_init == "npm start"

    def test_switch_agent_with_auto_confirm(self):
        """Test that agent switches support -y/--yes option."""
        runner = CliRunner()

        with patch("autowt.cli.create_services") as mock_create_services:
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            with patch("autowt.cli.find_waiting_agent_branch") as mock_find_waiting:
                mock_find_waiting.return_value = "test-branch"

                with patch("autowt.cli.checkout_branch") as mock_checkout:
                    result = runner.invoke(main, ["switch", "--waiting", "-y"])

                    assert result.exit_code == 0
                    args, kwargs = mock_checkout.call_args
                    switch_cmd = args[0]
                    assert switch_cmd.auto_confirm is True

    def test_switch_agent_with_ignore_same_session(self):
        """Test that agent switches support --ignore-same-session option."""
        runner = CliRunner()

        with patch("autowt.cli.create_services") as mock_create_services:
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            with patch("autowt.cli.find_latest_agent_branch") as mock_find_latest:
                mock_find_latest.return_value = "dev-branch"

                with patch("autowt.cli.checkout_branch") as mock_checkout:
                    result = runner.invoke(
                        main, ["switch", "--latest", "--ignore-same-session"]
                    )

                    assert result.exit_code == 0
                    args, kwargs = mock_checkout.call_args
                    switch_cmd = args[0]
                    assert switch_cmd.ignore_same_session is True

    def test_switch_agent_with_multiple_options(self):
        """Test agent switches with multiple CLI options combined."""
        runner = CliRunner()

        with patch("autowt.cli.create_services") as mock_create_services:
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            with patch("autowt.cli.find_waiting_agent_branch") as mock_find_waiting:
                mock_find_waiting.return_value = "complex-feature"

                with patch("autowt.cli.checkout_branch") as mock_checkout:
                    result = runner.invoke(
                        main,
                        [
                            "switch",
                            "--waiting",
                            "--terminal",
                            "tab",
                            "--init",
                            "echo 'Setting up'",
                            "--after-init",
                            "code .",
                            "--ignore-same-session",
                            "-y",
                        ],
                    )

                    assert result.exit_code == 0
                    args, kwargs = mock_checkout.call_args
                    switch_cmd = args[0]

                    assert switch_cmd.branch == "complex-feature"
                    assert switch_cmd.terminal_mode == TerminalMode.TAB
                    assert switch_cmd.after_init == "code ."
                    assert switch_cmd.ignore_same_session is True
                    assert switch_cmd.auto_confirm is True

    def test_no_waiting_agents_found(self):
        """Test behavior when no waiting agents are found."""
        runner = CliRunner()

        with patch("autowt.cli.create_services") as mock_create_services:
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            with patch("autowt.cli.find_waiting_agent_branch") as mock_find_waiting:
                mock_find_waiting.return_value = None  # No waiting agents

                with patch("autowt.cli.checkout_branch") as mock_checkout:
                    result = runner.invoke(main, ["switch", "--waiting"])

                    assert result.exit_code == 0
                    mock_find_waiting.assert_called_once()
                    # checkout_branch should NOT be called when no agent found
                    mock_checkout.assert_not_called()

    def test_no_latest_agents_found(self):
        """Test behavior when no latest agents are found."""
        runner = CliRunner()

        with patch("autowt.cli.create_services") as mock_create_services:
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            with patch("autowt.cli.find_latest_agent_branch") as mock_find_latest:
                mock_find_latest.return_value = None  # No recent agents

                with patch("autowt.cli.checkout_branch") as mock_checkout:
                    result = runner.invoke(main, ["switch", "--latest"])

                    assert result.exit_code == 0
                    mock_find_latest.assert_called_once()
                    # checkout_branch should NOT be called when no agent found
                    mock_checkout.assert_not_called()

    def test_mutually_exclusive_options_validation(self):
        """Test that mutually exclusive options are properly validated."""
        runner = CliRunner()

        # Test branch + waiting
        result = runner.invoke(main, ["switch", "my-branch", "--waiting"])
        assert result.exit_code != 0
        assert "Must specify exactly one of" in result.output

        # Test branch + latest
        result = runner.invoke(main, ["switch", "my-branch", "--latest"])
        assert result.exit_code != 0
        assert "Must specify exactly one of" in result.output

        # Test waiting + latest
        result = runner.invoke(main, ["switch", "--waiting", "--latest"])
        assert result.exit_code != 0
        assert "Must specify exactly one of" in result.output

        # Test no options
        result = runner.invoke(main, ["switch"])
        assert result.exit_code != 0
        assert "Must specify exactly one of" in result.output

    def test_switch_help_shows_all_options(self):
        """Test that switch help shows all available options."""
        runner = CliRunner()

        result = runner.invoke(main, ["switch", "--help"])
        assert result.exit_code == 0

        # Verify all options are documented
        expected_options = [
            "--terminal",
            "--init",
            "--after-init",
            "--ignore-same-session",
            "-y, --yes",
            "--waiting",
            "--latest",
            "--debug",
        ]

        for option in expected_options:
            assert option in result.output, f"Missing option {option} in help"
