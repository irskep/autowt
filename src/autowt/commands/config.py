"""Configuration command."""

import logging

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, RadioButton, RadioSet, Switch

from autowt.models import TerminalMode
from autowt.services.git import GitService
from autowt.services.process import ProcessService
from autowt.services.state import StateService
from autowt.services.terminal import TerminalService

logger = logging.getLogger(__name__)


class ConfigApp(App):
    """Simple configuration interface."""

    BINDINGS = [
        Binding("ctrl+s", "save", "Save & Exit"),
        Binding("escape", "cancel", "Cancel & Exit"),
        Binding("q", "cancel", "Quit"),
    ]

    def __init__(self, state_service: StateService):
        super().__init__()
        self.state_service = state_service
        self.config = state_service.load_config()

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        with Vertical():
            yield Label("Autowt Configuration")
            yield Label("")

            yield Label("Terminal Mode:")
            with RadioSet(id="terminal-mode"):
                yield RadioButton(
                    "tab - Open/switch to terminal tab",
                    value=self.config.terminal == TerminalMode.TAB,
                    id="mode-tab",
                )
                yield RadioButton(
                    "window - Open/switch to terminal window",
                    value=self.config.terminal == TerminalMode.WINDOW,
                    id="mode-window",
                )
                yield RadioButton(
                    "inplace - Change directory in current terminal",
                    value=self.config.terminal == TerminalMode.INPLACE,
                    id="mode-inplace",
                )

            yield Label("")

            with Horizontal():
                yield Switch(value=self.config.terminal_always_new, id="always-new")
                yield Label("Always create new terminal")

            yield Label("")

            with Horizontal():
                yield Button("Save", id="save")
                yield Button("Cancel", id="cancel")

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

        if pressed_button:
            if pressed_button.id == "mode-tab":
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
            self.exit()
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            self.exit()


def configure_settings(
    state_service: StateService,
    git_service: GitService,
    terminal_service: TerminalService,
    process_service: ProcessService,
) -> None:
    """Configure autowt settings interactively."""
    logger.debug("Configuring settings")

    app = ConfigApp(state_service)
    app.run()
