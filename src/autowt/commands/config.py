"""Configuration command."""

import logging

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, RadioButton, RadioSet, Switch

from autowt.config import (
    CleanupConfig,
    Config,
    ConfigLoader,
    TerminalConfig,
    WorktreeConfig,
)
from autowt.models import Services, TerminalMode

logger = logging.getLogger(__name__)


class ConfigApp(App):
    """Simple configuration interface."""

    BINDINGS = [
        Binding("ctrl+s", "save", "Save & Exit"),
        Binding("escape", "cancel", "Cancel & Exit"),
        Binding("q", "cancel", "Quit"),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self.config = services.state.load_config()

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        with Vertical():
            yield Label("Autowt Configuration")
            yield Label("")

            yield Label("Terminal Mode:")
            with RadioSet(id="terminal-mode"):
                yield RadioButton(
                    "tab - Open/switch to terminal tab",
                    value=self.config.terminal.mode == TerminalMode.TAB,
                    id="mode-tab",
                )
                yield RadioButton(
                    "window - Open/switch to terminal window",
                    value=self.config.terminal.mode == TerminalMode.WINDOW,
                    id="mode-window",
                )
                yield RadioButton(
                    "inplace - Change directory in current terminal",
                    value=self.config.terminal.mode == TerminalMode.INPLACE,
                    id="mode-inplace",
                )
                yield RadioButton(
                    "echo - Output shell commands (for manual navigation)",
                    value=self.config.terminal.mode == TerminalMode.ECHO,
                    id="mode-echo",
                )

            yield Label("")

            with Horizontal():
                yield Switch(value=self.config.terminal.always_new, id="always-new")
                yield Label("Always create new terminal")

            yield Label("")

            with Horizontal():
                yield Switch(value=self.config.worktree.auto_fetch, id="auto-fetch")
                yield Label("Automatically fetch from remote before creating worktrees")

            yield Label("")

            with Horizontal():
                yield Switch(
                    value=self.config.cleanup.kill_processes, id="kill-processes"
                )
                yield Label("Kill processes during cleanup")

            yield Label("")

            with Horizontal():
                yield Button("Save", id="save")
                yield Button("Cancel", id="cancel")

            yield Label("")
            yield Label("For all settings, edit the config file directly:")

            # Get the actual global config path for this platform
            config_loader = ConfigLoader(app_dir=self.services.state.app_dir)
            global_config_path = config_loader.global_config_file
            yield Label(f"• Global: {global_config_path}")
            yield Label("• Project: autowt.toml or .autowt.toml in repository root")
            yield Label("")
            yield Label(
                "Navigation: Tab to move around • Ctrl+S to save • Esc/Q to cancel"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save":
            self._save_config()
        elif event.button.id == "cancel":
            self.exit()

    def action_save(self) -> None:
        """Save configuration via keyboard shortcut."""
        self._save_config()

    def action_cancel(self) -> None:
        """Cancel configuration via keyboard shortcut."""
        self.exit()

    def _save_config(self) -> None:
        """Save configuration and exit."""

        # Get terminal mode from radio buttons
        radio_set = self.query_one("#terminal-mode", RadioSet)
        pressed_button = radio_set.pressed_button

        terminal_mode = self.config.terminal.mode
        if pressed_button:
            if pressed_button.id == "mode-tab":
                terminal_mode = TerminalMode.TAB
            elif pressed_button.id == "mode-window":
                terminal_mode = TerminalMode.WINDOW
            elif pressed_button.id == "mode-inplace":
                terminal_mode = TerminalMode.INPLACE
            elif pressed_button.id == "mode-echo":
                terminal_mode = TerminalMode.ECHO

        # Get always new setting
        always_new_switch = self.query_one("#always-new", Switch)
        always_new = always_new_switch.value

        # Get auto fetch setting
        auto_fetch_switch = self.query_one("#auto-fetch", Switch)
        auto_fetch = auto_fetch_switch.value

        # Get kill processes setting
        kill_processes_switch = self.query_one("#kill-processes", Switch)
        kill_processes = kill_processes_switch.value

        # Create new config with updated values (immutable dataclasses)

        new_config = Config(
            terminal=TerminalConfig(
                mode=terminal_mode,
                always_new=always_new,
                program=self.config.terminal.program,
            ),
            worktree=WorktreeConfig(
                directory_pattern=self.config.worktree.directory_pattern,
                max_worktrees=self.config.worktree.max_worktrees,
                auto_fetch=auto_fetch,
                default_remote=self.config.worktree.default_remote,
                branch_sanitization=self.config.worktree.branch_sanitization,
            ),
            cleanup=CleanupConfig(
                kill_processes=kill_processes,
                kill_process_timeout=self.config.cleanup.kill_process_timeout,
                default_mode=self.config.cleanup.default_mode,
            ),
            scripts=self.config.scripts,
            confirmations=self.config.confirmations,
        )

        # Save configuration
        try:
            self.services.state.save_config(new_config)
            self.exit()
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            self.exit()


def show_config(services: Services) -> None:
    """Show current configuration values."""
    config = services.state.load_config()
    config_loader = ConfigLoader(app_dir=services.state.app_dir)

    print("Current Configuration:")
    print("=" * 50)
    print()

    print("Terminal:")
    print(f"  mode: {config.terminal.mode.value}")
    print(f"  always_new: {config.terminal.always_new}")
    print(f"  program: {config.terminal.program}")
    print()

    print("Worktree:")
    print(f"  directory_pattern: {config.worktree.directory_pattern}")
    print(f"  max_worktrees: {config.worktree.max_worktrees}")
    print(f"  auto_fetch: {config.worktree.auto_fetch}")
    print(f"  default_remote: {config.worktree.default_remote}")
    print(f"  branch_sanitization: {config.worktree.branch_sanitization}")
    print()

    print("Cleanup:")
    print(f"  kill_processes: {config.cleanup.kill_processes}")
    print(f"  kill_process_timeout: {config.cleanup.kill_process_timeout}")
    print(f"  default_mode: {config.cleanup.default_mode.value}")
    print()

    print("Scripts:")
    print(f"  session_init: {config.scripts.session_init}")
    if config.scripts.custom:
        print("  custom:")
        for name, script in config.scripts.custom.items():
            print(f"    {name}: {script}")
    else:
        print("  custom: {}")
    print()

    print("Confirmations:")
    print(f"  cleanup_multiple: {config.confirmations.cleanup_multiple}")
    print(f"  kill_process: {config.confirmations.kill_process}")
    print(f"  force_operations: {config.confirmations.force_operations}")
    print()

    print("Config Files:")
    print(f"  Global: {config_loader.global_config_file}")
    print("  Project: autowt.toml or .autowt.toml in repository root")


def configure_settings(services: Services) -> None:
    """Configure autowt settings interactively."""
    logger.debug("Configuring settings")

    app = ConfigApp(services)
    app.run()
