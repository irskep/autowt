"""Textual TUI for interactive branch switching."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, ListItem, ListView, Static

from autowt.models import WorktreeInfo


class ClickableStatic(Static):
    """A Static widget that can handle clicks."""

    def __init__(self, *args, on_click_callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_click_callback = on_click_callback

    def on_click(self) -> None:
        """Handle click events on this widget."""
        if self.on_click_callback:
            self.on_click_callback()


class SwitchTUI(App):
    """Interactive switch interface using Textual."""

    TITLE = "Autowt - Interactive Switch"
    CSS_PATH = "switch.css"
    BINDINGS = [
        Binding("q,escape", "quit", "Quit"),
        Binding("n", "new_branch", "New"),
        Binding("space", "toggle_selection", "Select"),
        Binding("j", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("enter", "confirm", "Switch"),
    ]

    def __init__(self, worktrees: list[WorktreeInfo], all_branches: list[str]):
        super().__init__()

        # Sort worktrees by creation time (latest first)
        self.worktrees = self._sort_worktrees_by_creation_time(worktrees)
        self.all_branches = all_branches
        self.selected_index = None
        self.selected_branch = None
        self.is_new_branch = False
        self.list_view = None
        self.new_branch_input = None

        # Find branches without worktrees
        worktree_branches = {wt.branch for wt in self.worktrees}
        self.branches_without_worktrees = [
            branch for branch in all_branches if branch not in worktree_branches
        ]

    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header()

        with Container(id="main"):
            with Vertical(id="header-section"):
                yield Static(
                    "Select a branch to switch to (Enter=switch, n=new branch):",
                    id="instructions",
                )
                yield Static(
                    f"Found {len(self.worktrees)} worktrees, {len(self.branches_without_worktrees)} branches without worktrees",
                    id="status-bar",
                )

            # Create list items for worktrees and branches without worktrees
            list_items = []

            # Add existing worktrees
            if self.worktrees:
                header_item = ListItem(
                    Static("[bold]Existing Worktrees[/]", classes="section-header")
                )
                header_item.disabled = True
                list_items.append(header_item)
                for i, worktree in enumerate(self.worktrees):
                    list_items.append(self._create_worktree_item(i, worktree))

            # Add branches without worktrees
            if self.branches_without_worktrees:
                header_item = ListItem(
                    Static("[bold]Branches (no worktree)[/]", classes="section-header")
                )
                header_item.disabled = True
                list_items.append(header_item)
                for i, branch in enumerate(self.branches_without_worktrees):
                    list_items.append(
                        self._create_branch_item(len(self.worktrees) + i, branch)
                    )

            # Add "New Branch" option
            actions_header = ListItem(
                Static("[bold]Actions[/]", classes="section-header")
            )
            actions_header.disabled = True
            list_items.append(actions_header)
            new_branch_item = self._create_new_branch_item(
                len(self.worktrees) + len(self.branches_without_worktrees)
            )
            list_items.append(new_branch_item)

            if not list_items:
                yield Static("No worktrees or branches found.", id="empty")
            else:
                self.list_view = ListView(*list_items, id="branch-list")
                yield self.list_view

            # New branch input (initially hidden)
            self.new_branch_input = Input(
                placeholder="Enter new branch name...",
                id="new-branch-input",
            )
            self.new_branch_input.display = False
            yield self.new_branch_input

            with Horizontal(id="button-row"):
                yield Button("Switch", id="confirm", variant="primary", compact=True)
                yield Button("Cancel", id="cancel", variant="error", compact=True)

        yield Footer()

    def _sort_worktrees_by_creation_time(
        self, worktrees: list[WorktreeInfo]
    ) -> list[WorktreeInfo]:
        """Sort worktrees by creation time (latest first), with primary worktree last."""

        def get_creation_time(worktree: WorktreeInfo) -> float:
            try:
                # Get directory creation time (stat.st_ctime on most systems)
                stat = worktree.path.stat()
                return stat.st_ctime
            except (OSError, AttributeError):
                # Fallback for cases where path doesn't exist or stat fails
                return 0.0

        # Separate primary worktree from others
        primary_worktrees = [wt for wt in worktrees if wt.is_primary]
        regular_worktrees = [wt for wt in worktrees if not wt.is_primary]

        # Sort regular worktrees by creation time (newest first)
        regular_worktrees.sort(key=get_creation_time, reverse=True)

        # Return regular worktrees first, then primary
        return regular_worktrees + primary_worktrees

    def _create_worktree_item(self, index: int, worktree: WorktreeInfo) -> ListItem:
        """Create a list item for an existing worktree."""
        # Format path for display
        relative_path = self._format_path_for_display(worktree.path)

        status_text = "[green]ready[/]"
        if worktree.is_current:
            status_text = "[blue]current[/]"

        def handle_selection_click():
            self.selected_index = index
            self.selected_branch = worktree.branch
            self.is_new_branch = False
            if self.list_view:
                self.list_view.index = index + 1  # +1 for section header
            self._update_selection_display()

        selection_widget = ClickableStatic(
            "[dim][ ][/]",
            id=f"sel-{index}",
            classes="selection-indicator",
            on_click_callback=handle_selection_click,
        )

        content = Horizontal(
            Static(f"{worktree.branch}\n{relative_path}", classes="branch-info"),
            Static(status_text, classes="status-info"),
            selection_widget,
            classes="branch-row",
        )

        return ListItem(content, id=f"worktree-{index}")

    def _create_branch_item(self, index: int, branch: str) -> ListItem:
        """Create a list item for a branch without a worktree."""

        def handle_selection_click():
            self.selected_index = index
            self.selected_branch = branch
            self.is_new_branch = False
            if self.list_view:
                # Calculate actual list position (account for section headers)
                list_pos = 1 + len(self.worktrees) + 1 + (index - len(self.worktrees))
                self.list_view.index = list_pos
            self._update_selection_display()

        selection_widget = ClickableStatic(
            "[dim][ ][/]",
            id=f"sel-{index}",
            classes="selection-indicator",
            on_click_callback=handle_selection_click,
        )

        content = Horizontal(
            Static(f"{branch}\nNo worktree", classes="branch-info"),
            Static("[yellow]needs worktree[/]", classes="status-info"),
            selection_widget,
            classes="branch-row",
        )

        return ListItem(content, id=f"branch-{index}")

    def _create_new_branch_item(self, index: int) -> ListItem:
        """Create a list item for creating a new branch."""

        def handle_selection_click():
            self.action_new_branch()

        selection_widget = ClickableStatic(
            "[bold green]+[/]",
            id=f"sel-{index}",
            classes="selection-indicator",
            on_click_callback=handle_selection_click,
        )

        content = Horizontal(
            Static("Create new branch\nEnter branch name", classes="branch-info"),
            Static("[cyan]new[/]", classes="status-info"),
            selection_widget,
            classes="branch-row",
        )

        return ListItem(content, id=f"new-{index}")

    def on_mount(self) -> None:
        """Initialize after mounting."""
        # Auto-select first worktree (most recently created) if available
        if self.worktrees:
            self.selected_index = 0
            self.selected_branch = self.worktrees[0].branch
            self.is_new_branch = False
            self._update_selection_display()

            # Set ListView cursor to the first worktree item
            # Account for the "Existing Worktrees" section header
            if self.list_view:
                self.list_view.index = 1  # Skip section header

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm":
            self.action_confirm()
        elif event.button.id == "cancel":
            self.action_quit()

    def action_toggle_selection(self) -> None:
        """Toggle selection of current row."""
        if not self.list_view:
            return

        cursor_row = self.list_view.index
        self._handle_cursor_selection(cursor_row)

    def action_new_branch(self) -> None:
        """Show new branch input."""
        if self.new_branch_input:
            self.new_branch_input.display = True
            self.new_branch_input.focus()
            self.is_new_branch = True
            self.selected_branch = None

    def action_cursor_down(self) -> None:
        """Move cursor down."""
        if self.list_view:
            self.list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up."""
        if self.list_view:
            self.list_view.action_cursor_up()

    def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "enter":
            # If the input field has focus, let it handle the enter key
            if self.new_branch_input and self.new_branch_input.has_focus:
                return  # Let the input field handle this

            # If on the "new branch" option, show input; otherwise confirm
            if self.list_view:
                cursor_row = self.list_view.index
                # Check if cursor is on "new branch" option
                total_items = (
                    (1 + len(self.worktrees) if self.worktrees else 0)
                    + (
                        1 + len(self.branches_without_worktrees)
                        if self.branches_without_worktrees
                        else 0
                    )
                    + 1
                    + 1  # Actions header + new branch item
                )
                if cursor_row == total_items - 1:  # Last item is "new branch"
                    self.action_new_branch()
                else:
                    # Update selection based on cursor position first
                    self._handle_cursor_selection(cursor_row)
                    self.action_confirm()
            else:
                self.action_confirm()
            event.prevent_default()
        elif event.key == "n":
            # Don't interfere if input field has focus
            if self.new_branch_input and self.new_branch_input.has_focus:
                return
            self.action_new_branch()
            event.prevent_default()
        elif event.key == " ":  # Space key
            # Don't interfere if input field has focus
            if self.new_branch_input and self.new_branch_input.has_focus:
                return
            if self.list_view:
                self._handle_cursor_selection(self.list_view.index)
            event.prevent_default()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission for new branch name."""
        if event.input.id == "new-branch-input":
            branch_name = event.input.value.strip()
            if branch_name:
                self.selected_branch = branch_name
                self.is_new_branch = True
                self.action_confirm()
            else:
                # Hide input and go back to list
                self.new_branch_input.display = False
                self.is_new_branch = False
                if self.list_view:
                    self.list_view.focus()

    def _handle_list_selection(self, index: int) -> None:
        """Handle selection based on list index."""
        if index < len(self.worktrees):
            # Selecting a worktree
            self.selected_index = index
            self.selected_branch = self.worktrees[index].branch
            self.is_new_branch = False
        elif index < len(self.worktrees) + len(self.branches_without_worktrees):
            # Selecting a branch without worktree
            branch_index = index - len(self.worktrees)
            self.selected_index = index
            self.selected_branch = self.branches_without_worktrees[branch_index]
            self.is_new_branch = False
        else:
            # Selecting "new branch" option
            self.action_new_branch()
            return

        self._update_selection_display()

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
        # Clear all selections first
        for i in range(len(self.worktrees) + len(self.branches_without_worktrees) + 1):
            try:
                selection_widget = self.query_one(f"#sel-{i}", Static)
                if i == self.selected_index:
                    selection_widget.update("[bold green][\u2713][/]")
                else:
                    selection_widget.update("[dim][ ][/]")
            except Exception:
                # Ignore errors updating selection indicators
                pass

    def action_confirm(self) -> None:
        """Confirm selection and exit."""
        if (
            self.is_new_branch
            and self.new_branch_input
            and self.new_branch_input.value.strip()
        ):
            self.selected_branch = self.new_branch_input.value.strip()

        if self.selected_branch:
            self.exit()
        else:
            # No selection made
            self.action_quit()

    def action_quit(self) -> None:
        """Cancel and exit without selection."""
        self.selected_branch = None
        self.is_new_branch = False
        self.exit()

    def _handle_cursor_selection(self, cursor_row: int) -> None:
        """Handle selection based on ListView cursor position, accounting for section headers."""
        # Calculate which item the cursor is on, accounting for section headers
        # Structure: [Existing Worktrees header, worktrees..., Branches header, branches..., Actions header, new branch]

        current_row = 0

        # Skip "Existing Worktrees" header if present
        if self.worktrees:
            current_row += 1  # Section header
            if cursor_row < current_row + len(self.worktrees):
                # Cursor is on a worktree
                item_index = cursor_row - current_row
                self.selected_index = item_index
                self.selected_branch = self.worktrees[item_index].branch
                self.is_new_branch = False
                self._update_selection_display()
                return
            current_row += len(self.worktrees)

        # Skip "Branches (no worktree)" header if present
        if self.branches_without_worktrees:
            current_row += 1  # Section header
            if cursor_row < current_row + len(self.branches_without_worktrees):
                # Cursor is on a branch without worktree
                item_index = cursor_row - current_row
                branch_index = item_index
                self.selected_index = len(self.worktrees) + branch_index
                self.selected_branch = self.branches_without_worktrees[branch_index]
                self.is_new_branch = False
                self._update_selection_display()
                return
            current_row += len(self.branches_without_worktrees)

        # Skip "Actions" header
        current_row += 1  # Section header
        if cursor_row >= current_row:
            # Cursor is on "new branch" option
            self.action_new_branch()


def run_switch_tui(
    worktrees: list[WorktreeInfo], all_branches: list[str]
) -> tuple[str | None, bool]:
    """Run the switch TUI and return selected branch and whether it's a new branch.

    Returns:
        tuple: (selected_branch, is_new_branch) or (None, False) if cancelled
    """
    app = SwitchTUI(worktrees, all_branches)
    app.run()
    return app.selected_branch, app.is_new_branch
