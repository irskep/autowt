"""Configuration command."""

import logging

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Input, Label, RadioButton, RadioSet

from autowt.config import (
    CleanupConfig,
    Config,
    TerminalConfig,
    WorktreeConfig,
)
from autowt.models import CleanupMode, Services, TerminalMode

logger = logging.getLogger(__name__)


class ConfigApp(App):
    """Simple configuration interface."""

    CSS_PATH = "config.css"
    AUTO_FOCUS = None  # Disable auto-focus to prevent scroll-on-mount

    BINDINGS = [
        Binding("ctrl+s", "save", "Save & Exit"),
        Binding("escape", "cancel", "Cancel & Exit"),
        Binding("q", "cancel", "Quit"),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        # Load only global config for editing (not merged with project config)
        self.config = services.config_loader.load_global_config_only()

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        with Vertical(id="main-container"):
            yield Label("Global Configuration")

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

            yield Checkbox(
                "Always create new terminal",
                value=self.config.terminal.always_new,
                id="always-new",
            )

            yield Checkbox(
                "Automatically fetch from remote before creating worktrees",
                value=self.config.worktree.auto_fetch,
                id="auto-fetch",
            )

            yield Label(
                "Branch prefix (optional, e.g., 'feature/' or '{github_username}/'):"
            )
            yield Input(
                value=self.config.worktree.branch_prefix or "",
                placeholder="e.g., feature/ or {github_username}/",
                id="branch-prefix",
            )

            yield Label("Default Cleanup Mode:")
            with RadioSet(id="cleanup-mode"):
                yield RadioButton(
                    "interactive - Choose branches via TUI",
                    value=self.config.cleanup.default_mode == CleanupMode.INTERACTIVE,
                    id="cleanup-interactive",
                )
                yield RadioButton(
                    "merged - Auto-select merged branches",
                    value=self.config.cleanup.default_mode == CleanupMode.MERGED,
                    id="cleanup-merged",
                )
                yield RadioButton(
                    "remoteless - Auto-select branches without remote",
                    value=self.config.cleanup.default_mode == CleanupMode.REMOTELESS,
                    id="cleanup-remoteless",
                )
                yield RadioButton(
                    "all - Auto-select merged + remoteless branches",
                    value=self.config.cleanup.default_mode == CleanupMode.ALL,
                    id="cleanup-all",
                )
                yield RadioButton(
                    "github - Use GitHub CLI to find merged/closed PRs",
                    value=self.config.cleanup.default_mode == CleanupMode.GITHUB,
                    id="cleanup-github",
                )

            with Horizontal(id="button-row"):
                yield Button("Save", id="save", variant="primary", compact=True)
                yield Button("Cancel", id="cancel", variant="error", compact=True)

            yield Label("These settings apply globally to all repositories.")

            # Get the actual global config path for this platform
            global_config_path = self.services.config_loader.global_config_file
            yield Label(f"Global config file: {global_config_path}")
            yield Label(
                "For project-specific settings, create .autowt.toml in your repository root."
            )
            yield Label(
                "Navigation: Tab to move around • Ctrl+S to save • Esc/Q to cancel"
            )

    def on_mount(self) -> None:
        """Ensure scroll position starts at top when app loads."""
        container = self.query_one("#main-container")
        container.scroll_to(0, 0, animate=False)

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
        always_new_checkbox = self.query_one("#always-new", Checkbox)
        always_new = always_new_checkbox.value

        # Get auto fetch setting
        auto_fetch_checkbox = self.query_one("#auto-fetch", Checkbox)
        auto_fetch = auto_fetch_checkbox.value

        # Get branch prefix setting
        branch_prefix_input = self.query_one("#branch-prefix", Input)
        branch_prefix = branch_prefix_input.value.strip() or None

        # Get cleanup mode from radio buttons
        cleanup_radio_set = self.query_one("#cleanup-mode", RadioSet)
        cleanup_pressed_button = cleanup_radio_set.pressed_button

        cleanup_mode = self.config.cleanup.default_mode
        if cleanup_pressed_button:
            if cleanup_pressed_button.id == "cleanup-interactive":
                cleanup_mode = CleanupMode.INTERACTIVE
            elif cleanup_pressed_button.id == "cleanup-merged":
                cleanup_mode = CleanupMode.MERGED
            elif cleanup_pressed_button.id == "cleanup-remoteless":
                cleanup_mode = CleanupMode.REMOTELESS
            elif cleanup_pressed_button.id == "cleanup-all":
                cleanup_mode = CleanupMode.ALL
            elif cleanup_pressed_button.id == "cleanup-github":
                cleanup_mode = CleanupMode.GITHUB

        # Create new config with updated values (immutable dataclasses)

        new_config = Config(
            terminal=TerminalConfig(
                mode=terminal_mode,
                always_new=always_new,
                program=self.config.terminal.program,
            ),
            worktree=WorktreeConfig(
                directory_pattern=self.config.worktree.directory_pattern,
                auto_fetch=auto_fetch,
                branch_prefix=branch_prefix,
            ),
            cleanup=CleanupConfig(
                default_mode=cleanup_mode,
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
    print(f"  auto_fetch: {config.worktree.auto_fetch}")
    print(f"  branch_prefix: {config.worktree.branch_prefix}")
    print()

    print("Cleanup:")
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
    print(f"  force_operations: {config.confirmations.force_operations}")
    print()

    print("Config Files:")
    print(f"  Global: {services.config_loader.global_config_file}")
    print("  Project: autowt.toml or .autowt.toml in repository root")


def configure_settings(services: Services) -> None:
    """Configure autowt settings interactively."""
    logger.debug("Configuring settings")

    app = ConfigApp(services)
    app.run()
