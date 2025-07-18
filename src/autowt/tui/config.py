"""Textual TUI for configuration."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, RadioButton, RadioSet, Switch

from autowt.config import Config, TerminalConfig
from autowt.models import TerminalMode
from autowt.services.state import StateService


class ConfigTUI(App):
    """Interactive configuration interface using Textual."""

    TITLE = "Autowt - Configuration"
    CSS_PATH = "config.css"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "save", "Save & Exit"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, state_service: StateService):
        super().__init__()
        self.state_service = state_service
        self.config = state_service.load_config()
        self.saved = False

    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header()

        with Container(id="main"):
            yield Label("Autowt Configuration", id="title")

            with Vertical(id="config-form"):
                yield Label("Terminal Mode:", classes="section-label")
                yield Label("How to open worktree terminals", classes="help-text")

                with RadioSet(id="terminal-mode"):
                    yield RadioButton(
                        "tab - Switch to existing session or open new tab",
                        value=self.config.terminal.mode == TerminalMode.TAB,
                        id="mode-tab",
                    )
                    yield RadioButton(
                        "window - Switch to existing session or open new window",
                        value=self.config.terminal.mode == TerminalMode.WINDOW,
                        id="mode-window",
                    )
                    yield RadioButton(
                        "inplace - Change directory in current terminal",
                        value=self.config.terminal.mode == TerminalMode.INPLACE,
                        id="mode-inplace",
                    )

                yield Label("", classes="spacer")  # Spacer

                yield Label("Terminal Behavior:", classes="section-label")
                with Horizontal(classes="switch-row"):
                    yield Switch(value=self.config.terminal.always_new, id="always-new")
                    yield Label(
                        "Always create new terminal (don't switch to existing)",
                        classes="switch-label",
                    )

            with Horizontal(id="button-row"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel", variant="error")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save":
            self.action_save()
        elif event.button.id == "cancel":
            self.action_cancel()

    def action_save(self) -> None:
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

        # Get always new setting
        always_new_switch = self.query_one("#always-new", Switch)
        always_new = always_new_switch.value

        # Create new config with updated values (immutable dataclasses)

        new_config = Config(
            terminal=TerminalConfig(
                mode=terminal_mode,
                always_new=always_new,
                program=self.config.terminal.program,
            ),
            worktree=self.config.worktree,
            cleanup=self.config.cleanup,
            scripts=self.config.scripts,
            confirmations=self.config.confirmations,
        )

        # Save configuration
        try:
            self.state_service.save_config(new_config)
            self.saved = True
            self.exit()
        except Exception as e:
            # In a real app, we'd show an error dialog
            self.notify(f"Failed to save configuration: {e}", severity="error")

    def action_cancel(self) -> None:
        """Cancel without saving."""
        self.saved = False
        self.exit()

    def action_quit(self) -> None:
        """Quit without saving."""
        self.action_cancel()


def run_config_tui(state_service: StateService) -> bool:
    """Run the configuration TUI and return whether settings were saved."""
    app = ConfigTUI(state_service)
    app.run()
    return app.saved
