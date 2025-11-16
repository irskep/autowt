"""Textual TUI for interactive cleanup."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, ListItem, ListView, Static

from autowt.models import BranchStatus


class ClickableStatic(Static):
    """A Static widget that can handle clicks."""

    def __init__(self, *args, on_click_callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_click_callback = on_click_callback

    def on_click(self) -> None:
        """Handle click events on this widget."""
        if self.on_click_callback:
            self.on_click_callback()


class CleanupTUI(App):
    """Interactive cleanup interface using Textual."""

    TITLE = "Autowt - Interactive Cleanup"
    CSS_PATH = "cleanup.css"
    BINDINGS = [
        Binding("q,escape", "quit", "Quit"),
        Binding("a", "select_all", "Select All"),
        Binding("n", "select_none", "None"),
        Binding("m", "select_merged", "Merged"),
        Binding("r", "select_remoteless", "No Remote"),
        Binding("space", "toggle_selection", "Toggle"),
        Binding("j", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("enter", "confirm", "Confirm"),
    ]

    def __init__(self, branch_statuses: list[BranchStatus]):
        super().__init__()
        self.branch_statuses = branch_statuses
        self.selected_rows = set()
        self.selected_branches = []
        self.list_view = None

    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header()

        with Container(id="main"):
            with Vertical(id="header-section"):
                yield Static(
                    "Select worktrees to remove (Space=toggle, Enter=confirm):",
                    id="instructions",
                )
                yield Static(
                    f"Found {len(self.branch_statuses)} worktrees | 0 selected",
                    id="status-bar",
                )

            if not self.branch_statuses:
                yield Static("No worktrees found for cleanup.", id="empty")
            else:
                # Create list items
                list_items = []
                for i, branch_status in enumerate(self.branch_statuses):
                    list_items.append(self._create_list_item(i, branch_status))

                self.list_view = ListView(*list_items, id="branch-list")
                yield self.list_view

            with Horizontal(id="button-row"):
                yield Button(
                    "Confirm Selection", id="confirm", variant="primary", compact=True
                )
                yield Button("Cancel", id="cancel", variant="error", compact=True)

        yield Footer()

    def _create_list_item(self, index: int, branch_status: BranchStatus) -> ListItem:
        """Create a list item for a branch with 3-column layout."""
        # Format path for display
        relative_path = self._format_path_for_display(branch_status.path)

        # Status text
        status_parts = []
        if branch_status.has_uncommitted_changes:
            status_parts.append("[red]uncommitted[/]")
        if branch_status.is_merged:
            status_parts.append("[green]merged[/]")
        if not branch_status.has_remote:
            status_parts.append("[yellow]no remote[/]")
        status_text = ", ".join(status_parts) if status_parts else "[dim]active[/]"

        # Create clickable selection widget
        def handle_selection_click():
            # Toggle selection for this index
            if index in self.selected_rows:
                self.selected_rows.remove(index)
            else:
                self.selected_rows.add(index)

            # Update ListView cursor to this row
            if self.list_view:
                self.list_view.index = index

            self.update_status_bar()
            self._update_selection_display()

        selection_widget = ClickableStatic(
            "[dim][ ][/]",
            id=f"sel-{index}",
            classes="selection-indicator",
            on_click_callback=handle_selection_click,
        )

        content = Horizontal(
            Static(f"{branch_status.branch}\n{relative_path}", classes="branch-info"),
            Static(status_text, classes="status-info"),
            selection_widget,
            classes="branch-row",
        )

        return ListItem(content, id=f"item-{index}")

    def on_mount(self) -> None:
        """Initialize after mounting."""
        self.update_status_bar()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm":
            self.action_confirm()
        elif event.button.id == "cancel":
            self.action_quit()

    def update_status_bar(self) -> None:
        """Update the status bar with selection count."""
        status_bar = self.query_one("#status-bar", Static)
        status_bar.update(
            f"Found {len(self.branch_statuses)} worktrees | {len(self.selected_rows)} selected"
        )

    def action_toggle_selection(self) -> None:
        """Toggle selection of current row."""
        if not self.list_view:
            return

        cursor_row = self.list_view.index
        if cursor_row in self.selected_rows:
            self.selected_rows.remove(cursor_row)
        else:
            self.selected_rows.add(cursor_row)

        self.update_status_bar()
        self._update_selection_display()

    def action_select_all(self) -> None:
        """Select all rows."""
        self.selected_rows = set(range(len(self.branch_statuses)))
        self.update_status_bar()
        self._update_selection_display()

    def action_select_none(self) -> None:
        """Deselect all rows."""
        self.selected_rows.clear()
        self.update_status_bar()
        self._update_selection_display()

    def action_select_merged(self) -> None:
        """Select only merged branches."""
        self.selected_rows = {
            i
            for i, branch_status in enumerate(self.branch_statuses)
            if branch_status.is_merged
        }
        self.update_status_bar()
        self._update_selection_display()

    def action_select_remoteless(self) -> None:
        """Select only branches without remotes."""
        self.selected_rows = {
            i
            for i, branch_status in enumerate(self.branch_statuses)
            if not branch_status.has_remote
        }
        self.update_status_bar()
        self._update_selection_display()

    def action_cursor_down(self) -> None:
        """Move cursor down."""
        if self.list_view:
            self.list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up."""
        if self.list_view:
            self.list_view.action_cursor_up()

    def on_key(self, event) -> None:
        """Handle key presses for quick selection."""
        if event.key.isdigit():
            row_index = int(event.key) - 1
            if 0 <= row_index < len(self.branch_statuses):
                if row_index in self.selected_rows:
                    self.selected_rows.remove(row_index)
                else:
                    self.selected_rows.add(row_index)

                # Move cursor to this row
                if self.list_view:
                    # ListView doesn't have direct move_cursor, but we can use index property
                    self.list_view.index = row_index

                self.update_status_bar()
                self._update_selection_display()
                event.prevent_default()
        elif event.key == "enter":
            # Ensure Enter key triggers confirm action
            self.action_confirm()
            event.prevent_default()

    def _format_path_for_display(self, path) -> str:
        """Format a path for compact display."""
        try:
            # Try to make it relative to current working directory
            current_dir = Path.cwd()
            relative_path = path.relative_to(current_dir)
            return str(relative_path)
        except ValueError:
            # Try to make it relative to home directory
            try:
                home_dir = Path.home()
                relative_path = path.relative_to(home_dir)
                return f"~/{relative_path}"
            except ValueError:
                # Fall back to absolute path
                return str(path)

    def _update_selection_display(self) -> None:
        """Update selection indicators."""
        for i in range(len(self.branch_statuses)):
            try:
                selection_widget = self.query_one(f"#sel-{i}", Static)
                if i in self.selected_rows:
                    selection_widget.update("[bold green][\u2713][/]")
                else:
                    selection_widget.update("[dim][ ][/]")
            except Exception:
                # Ignore errors updating selection indicators
                pass

    def action_confirm(self) -> None:
        """Confirm selection and exit."""
        self.selected_branches = [self.branch_statuses[i] for i in self.selected_rows]
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
