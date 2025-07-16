"""Textual TUI for interactive cleanup."""


from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Checkbox, Footer, Header, Label

from autowt.models import BranchStatus


class CleanupTUI(App):
    """Interactive cleanup interface using Textual."""

    TITLE = "Autowt - Interactive Cleanup"
    CSS_PATH = "cleanup.css"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "select_all", "Select All"),
        Binding("n", "select_none", "Select None"),
        Binding("m", "select_merged", "Select Merged"),
        Binding("r", "select_remoteless", "Select No Remote"),
        Binding("enter", "confirm", "Confirm Selection"),
    ]

    def __init__(self, branch_statuses: list[BranchStatus]):
        super().__init__()
        self.branch_statuses = branch_statuses
        self.checkboxes = []
        self.selected_branches = []

    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header()

        with Container(id="main"):
            yield Label("Select worktrees to remove:", id="instructions")

            if not self.branch_statuses:
                yield Label("No worktrees found for cleanup.", id="empty")
            else:
                with Vertical(id="worktree-list"):
                    for branch_status in self.branch_statuses:
                        status_info = []
                        if not branch_status.has_remote:
                            status_info.append("no remote")
                        if branch_status.is_merged:
                            status_info.append("merged")

                        status_str = (
                            f" ({', '.join(status_info)})" if status_info else ""
                        )
                        label_text = f"{branch_status.branch}{status_str}"

                        checkbox = Checkbox(
                            label_text, value=False, id=f"cb_{branch_status.branch}"
                        )
                        self.checkboxes.append((checkbox, branch_status))
                        yield checkbox

            with Horizontal(id="button-row"):
                yield Button("Select All", id="select-all", variant="success")
                yield Button("Select None", id="select-none")
                yield Button("Select Merged", id="select-merged", variant="warning")
                yield Button(
                    "Select No Remote", id="select-remoteless", variant="warning"
                )
                yield Button("Confirm", id="confirm", variant="primary")
                yield Button("Cancel", id="cancel", variant="error")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "select-all":
            self.action_select_all()
        elif event.button.id == "select-none":
            self.action_select_none()
        elif event.button.id == "select-merged":
            self.action_select_merged()
        elif event.button.id == "select-remoteless":
            self.action_select_remoteless()
        elif event.button.id == "confirm":
            self.action_confirm()
        elif event.button.id == "cancel":
            self.action_quit()

    def action_select_all(self) -> None:
        """Select all checkboxes."""
        for checkbox, _ in self.checkboxes:
            checkbox.value = True

    def action_select_none(self) -> None:
        """Deselect all checkboxes."""
        for checkbox, _ in self.checkboxes:
            checkbox.value = False

    def action_select_merged(self) -> None:
        """Select only merged branches."""
        for checkbox, branch_status in self.checkboxes:
            checkbox.value = branch_status.is_merged

    def action_select_remoteless(self) -> None:
        """Select only branches without remotes."""
        for checkbox, branch_status in self.checkboxes:
            checkbox.value = not branch_status.has_remote

    def action_confirm(self) -> None:
        """Confirm selection and exit."""
        self.selected_branches = [
            branch_status
            for checkbox, branch_status in self.checkboxes
            if checkbox.value
        ]
        self.exit()

    def action_quit(self) -> None:
        """Cancel and exit without selection."""
        self.selected_branches = []
        self.exit()


def run_cleanup_tui(branch_statuses: list[BranchStatus]) -> list[BranchStatus]:
    """Run the cleanup TUI and return selected branches."""
    app = CleanupTUI(branch_statuses)
    app.run()
    return app.selected_branches
