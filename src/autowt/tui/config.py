"""Textual TUI for configuration."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, RadioButton, RadioSet, Switch

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
                        "same - Switch to existing tab/window if available",
                        value=self.config.terminal == TerminalMode.SAME,
                        id="mode-same",
                    )
                    yield RadioButton(
                        "tab - Always open new tab",
                        value=self.config.terminal == TerminalMode.TAB,
                        id="mode-tab",
                    )
                    yield RadioButton(
                        "window - Always open new window",
                        value=self.config.terminal == TerminalMode.WINDOW,
                        id="mode-window",
                    )
                    yield RadioButton(
                        "inplace - Change directory in current terminal",
                        value=self.config.terminal == TerminalMode.INPLACE,
                        id="mode-inplace",
                    )

                yield Label("", classes="spacer")  # Spacer

                yield Label("Terminal Behavior:", classes="section-label")
                with Horizontal(classes="switch-row"):
                    yield Switch(value=self.config.terminal_always_new, id="always-new")
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

        if pressed_button:
            if pressed_button.id == "mode-same":
                self.config.terminal = TerminalMode.SAME
            elif pressed_button.id == "mode-tab":
                self.config.terminal = TerminalMode.TAB
            elif pressed_button.id == "mode-window":
                self.config.terminal = TerminalMode.WINDOW
            elif pressed_button.id == "mode-inplace":
                self.config.terminal = TerminalMode.INPLACE

        # Get always new setting
        always_new_switch = self.query_one("#always-new", Switch)
        self.config.terminal_always_new = always_new_switch.value

        # Save configuration
        try:
            self.state_service.save_config(self.config)
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
