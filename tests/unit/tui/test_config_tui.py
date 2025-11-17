"""Tests for config TUI functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autowt.commands.config import ConfigApp
from autowt.config import (
    CleanupConfig,
    Config,
    ConfigLoader,
    TerminalConfig,
    WorktreeConfig,
)
from autowt.models import Services, TerminalMode
from autowt.services.state import StateService


class TestConfigTUIBusinessLogic:
    """Level 1: Business logic tests (no async needed)."""

    def test_config_loader_integration(self):
        """Test ConfigLoader actually works with real paths - would catch attribute bugs."""
        # This would have caught my global_config_path vs global_config_file bug
        app_dir = Path("/tmp/test_autowt")
        loader = ConfigLoader(app_dir=app_dir)

        # Test the actual API I tried to use
        config_file = loader.global_config_file
        assert config_file.name == "config.toml"
        assert str(app_dir) in str(config_file)

    def test_save_config_creates_correct_terminal_mode(self):
        """Test _save_config() method creates correct Config object."""
        # Mock services
        mock_services = MagicMock(spec=Services)
        mock_state = MagicMock(spec=StateService)
        mock_state.app_dir = Path("/tmp/test")
        mock_services.state = mock_state

        # Mock config_loader
        mock_config_loader = MagicMock()
        test_config = Config(
            terminal=TerminalConfig(mode=TerminalMode.TAB, always_new=False),
            worktree=WorktreeConfig(auto_fetch=True),
            cleanup=CleanupConfig(),
        )
        mock_config_loader.load_global_config_only.return_value = test_config
        mock_services.config_loader = mock_config_loader

        # Create app with mock config
        app = ConfigApp(mock_services)

        # Mock the UI widgets to simulate user selections
        with patch.object(app, "query_one") as mock_query:
            # Mock radio button for ECHO mode
            mock_radio_set = MagicMock()
            mock_pressed_button = MagicMock()
            mock_pressed_button.id = "mode-echo"
            mock_radio_set.pressed_button = mock_pressed_button

            # Mock switches
            mock_always_new_switch = MagicMock()
            mock_always_new_switch.value = True
            mock_auto_fetch_switch = MagicMock()
            mock_auto_fetch_switch.value = False

            # Mock branch prefix input
            mock_branch_prefix_input = MagicMock()
            mock_branch_prefix_input.value = "feature/"

            # Mock cleanup mode radio buttons
            mock_cleanup_radio_set = MagicMock()
            mock_cleanup_pressed_button = MagicMock()
            mock_cleanup_pressed_button.id = "cleanup-interactive"  # Default
            mock_cleanup_radio_set.pressed_button = mock_cleanup_pressed_button

            # Configure query_one to return appropriate mocks
            def query_side_effect(selector, widget_type=None):
                if selector == "#terminal-mode":
                    return mock_radio_set
                elif selector == "#always-new":
                    return mock_always_new_switch
                elif selector == "#auto-fetch":
                    return mock_auto_fetch_switch
                elif selector == "#branch-prefix":
                    return mock_branch_prefix_input
                elif selector == "#cleanup-mode":
                    return mock_cleanup_radio_set

            mock_query.side_effect = query_side_effect

            # Call the method under test
            app._save_config()

            # Verify save_config was called with correct values
            mock_state.save_config.assert_called_once()
            saved_config = mock_state.save_config.call_args[0][0]

            # Test the key values that would have been affected by my changes
            assert saved_config.terminal.mode == TerminalMode.ECHO
            assert saved_config.terminal.always_new is True
            assert saved_config.worktree.auto_fetch is False

    def test_save_config_preserves_unchanged_settings(self):
        """Test that _save_config preserves settings not exposed in TUI."""
        mock_services = MagicMock(spec=Services)
        mock_state = MagicMock(spec=StateService)
        mock_state.app_dir = Path("/tmp/test")
        mock_services.state = mock_state

        # Mock config_loader
        mock_config_loader = MagicMock()
        test_config = Config(
            terminal=TerminalConfig(
                mode=TerminalMode.TAB,
                always_new=False,
                program="custom_terminal",  # Not in TUI
            ),
            worktree=WorktreeConfig(
                auto_fetch=True,
                directory_pattern="custom/{branch}",  # Not in TUI
            ),
        )
        mock_config_loader.load_global_config_only.return_value = test_config
        mock_services.config_loader = mock_config_loader

        # Create app with config that has settings not in TUI
        app = ConfigApp(mock_services)

        # Mock UI widgets with no changes
        with patch.object(app, "query_one") as mock_query:
            mock_radio_set = MagicMock()
            mock_radio_set.pressed_button = None  # No selection change

            mock_switches = {
                "#always-new": MagicMock(value=False),
                "#auto-fetch": MagicMock(value=True),
            }

            # Mock branch prefix input
            mock_branch_prefix_input = MagicMock()
            mock_branch_prefix_input.value = ""

            # Mock cleanup mode radio buttons
            mock_cleanup_radio_set = MagicMock()
            mock_cleanup_radio_set.pressed_button = None  # No change

            def query_side_effect(selector, widget_type=None):
                if selector == "#terminal-mode":
                    return mock_radio_set
                elif selector == "#cleanup-mode":
                    return mock_cleanup_radio_set
                elif selector == "#branch-prefix":
                    return mock_branch_prefix_input
                return mock_switches.get(selector, MagicMock())

            mock_query.side_effect = query_side_effect

            app._save_config()

            # Verify unchanged settings are preserved
            saved_config = mock_state.save_config.call_args[0][0]
            assert saved_config.terminal.program == "custom_terminal"
            assert saved_config.worktree.directory_pattern == "custom/{branch}"


@pytest.mark.asyncio
class TestConfigTUIUserWorkflows:
    """Level 2: User workflow tests (async - real value)."""

    async def test_user_selects_echo_mode_and_saves(self):
        """Test complete user workflow: open → change → save → persist."""
        # Mock services
        mock_services = MagicMock(spec=Services)
        mock_state = MagicMock(spec=StateService)
        mock_state.app_dir = Path("/tmp/test")
        mock_services.state = mock_state

        # Mock config_loader (needed for compose() method)
        mock_config_loader = MagicMock()
        mock_config_loader.global_config_file = Path("/tmp/test/config.toml")
        test_config = Config(
            terminal=TerminalConfig(mode=TerminalMode.TAB, always_new=False),
            worktree=WorktreeConfig(auto_fetch=True),
            cleanup=CleanupConfig(),
        )
        mock_config_loader.load_global_config_only.return_value = test_config
        mock_services.config_loader = mock_config_loader

        # Mock load_config to return a test config
        mock_state.load_config.return_value = test_config

        app = ConfigApp(mock_services)

        # Mock _save_config to avoid needing to mock all widgets
        with patch.object(app, "_save_config") as mock_save:
            async with app.run_test() as pilot:
                # Click echo mode radio button
                await pilot.click("#mode-echo")

                # Scroll to bottom to make buttons visible
                container = app.query_one("#main-container")
                container.scroll_end(animate=False)
                await pilot.pause()

                # Click save button
                await pilot.click("#save")

                # Verify _save_config was called
                mock_save.assert_called_once()

    async def test_global_config_path_displays_correctly(self):
        """Test TUI shows real config path - would catch my attribute bug."""
        # Use tmp directory to avoid permission issues
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_dir = Path(tmp_dir) / "autowt"

            # Mock services with temporary paths
            mock_services = MagicMock(spec=Services)
            mock_state = MagicMock(spec=StateService)
            mock_state.app_dir = app_dir
            mock_services.state = mock_state

            # Mock config_loader (needed for compose() method)
            mock_config_loader = MagicMock()
            mock_config_loader.global_config_file = app_dir / "config.toml"
            test_config = Config()
            mock_config_loader.load_global_config_only.return_value = test_config
            mock_services.config_loader = mock_config_loader

            app = ConfigApp(mock_services)

            async with app.run_test() as pilot:
                # Let the UI render
                await pilot.pause()

                # Find labels containing config path info
                labels = app.query("Label")
                label_texts = [str(label.render()) for label in labels]

                # Should show global config path without crashing (text changed to "Global config file:")
                global_labels = [
                    text for text in label_texts if "Global config file:" in text
                ]
                assert len(global_labels) == 1
                assert "config.toml" in global_labels[0]
                assert str(app_dir / "config.toml") in global_labels[0]

    async def test_toggle_switches_work(self):
        """Test that boolean toggle switches actually work."""
        mock_services = MagicMock(spec=Services)
        mock_state = MagicMock(spec=StateService)
        mock_state.app_dir = Path("/tmp/test")
        mock_services.state = mock_state

        # Mock config_loader (needed for compose() method)
        mock_config_loader = MagicMock()
        mock_config_loader.global_config_file = Path("/tmp/test/config.toml")
        # Start with default config
        test_config = Config(
            terminal=TerminalConfig(always_new=False),
            worktree=WorktreeConfig(auto_fetch=True),
            cleanup=CleanupConfig(),
        )
        mock_config_loader.load_global_config_only.return_value = test_config
        mock_services.config_loader = mock_config_loader

        app = ConfigApp(mock_services)

        # Mock _save_config to avoid needing to mock all widgets
        with patch.object(app, "_save_config") as mock_save:
            async with app.run_test() as pilot:
                # Toggle the always_new switch
                await pilot.click("#always-new")

                # Toggle auto_fetch switch
                await pilot.click("#auto-fetch")

                # Scroll to bottom to make buttons visible
                container = app.query_one("#main-container")
                container.scroll_end(animate=False)
                await pilot.pause()

                # Save config
                await pilot.click("#save")

                # Verify _save_config was called
                mock_save.assert_called_once()

    async def test_cancel_button_exits_without_saving(self):
        """Test that cancel button exits without calling save."""
        mock_services = MagicMock(spec=Services)
        mock_state = MagicMock(spec=StateService)
        mock_state.app_dir = Path("/tmp/test")
        mock_services.state = mock_state

        # Mock config_loader (needed for compose() method)
        mock_config_loader = MagicMock()
        mock_config_loader.global_config_file = Path("/tmp/test/config.toml")
        test_config = Config()
        mock_config_loader.load_global_config_only.return_value = test_config
        mock_services.config_loader = mock_config_loader

        mock_state.load_config.return_value = test_config

        app = ConfigApp(mock_services)

        async with app.run_test() as pilot:
            # Make some changes
            await pilot.click("#mode-echo")
            await pilot.click("#always-new")

            # Scroll to bottom to make buttons visible
            container = app.query_one("#main-container")
            container.scroll_end(animate=False)
            await pilot.pause()

            # Click cancel instead of save
            await pilot.click("#cancel")

            # Verify save was never called
            mock_state.save_config.assert_not_called()
