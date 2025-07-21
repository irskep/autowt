"""Textual TUI for agent monitoring dashboard."""

from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.timer import Timer
from textual.widgets import DataTable, Footer, Header, Static

from autowt.models import Services


class AgentDashboard(App):
    """Live agent monitoring dashboard."""

    TITLE = "Autowt - Agent Dashboard"
    CSS_PATH = "agents.css"
    BINDINGS = [
        Binding("q,escape", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("w", "switch_waiting", "Switch to Waiting"),
        Binding("enter", "switch_selected", "Switch to Selected"),
        Binding("j,down", "cursor_down", "Down"),
        Binding("k,up", "cursor_up", "Up"),
    ]

    def __init__(self, services: Services, repo_path: Path):
        super().__init__()
        self.services = services
        self.repo_path = repo_path
        self.refresh_timer: Timer | None = None
        self.table: DataTable | None = None

    def compose(self) -> ComposeResult:
        """Create dashboard layout."""
        yield Header()
        yield Container(
            Static(
                "Agent Status Dashboard - Auto-refresh every 3 seconds", id="status"
            ),
            DataTable(id="agents-table"),
            id="main-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Set up dashboard when mounted."""
        self.table = self.query_one("#agents-table", DataTable)
        self.table.add_columns("Branch", "Status", "Last Activity", "Session")
        self.table.cursor_type = "row"

        self.refresh_data()
        # Set up auto-refresh every 3 seconds
        self.refresh_timer = self.set_interval(3.0, self.refresh_data)

    def refresh_data(self) -> None:
        """Refresh agent data from worktrees."""
        # Get worktrees
        git_worktrees = self.services.git.list_worktrees(self.repo_path)

        # Enhance with agent status
        enhanced_worktrees = self.services.agent.enhance_worktrees_with_agent_status(
            git_worktrees, self.services.state, self.repo_path
        )

        # Clear and populate table
        self.table.clear()

        for worktree in enhanced_worktrees:
            status_display = "Idle"
            if worktree.agent_status:
                status_display = f"{worktree.agent_status.status_indicator} {worktree.agent_status.status.title()}"

            last_activity = "Never"
            if worktree.agent_status and worktree.agent_status.last_activity:
                try:
                    dt = datetime.fromisoformat(
                        worktree.agent_status.last_activity.replace("Z", "+00:00")
                    )
                    last_activity = dt.strftime("%H:%M:%S")
                except ValueError:
                    last_activity = "Unknown"

            session_display = "✓" if worktree.has_active_session else "✗"

            self.table.add_row(
                worktree.branch,
                status_display,
                last_activity,
                session_display,
                key=worktree.branch,
            )

    def action_refresh(self) -> None:
        """Manual refresh action."""
        self.refresh_data()

    def action_switch_waiting(self) -> None:
        """Switch to first agent waiting for input."""
        # Find waiting agents
        git_worktrees = self.services.git.list_worktrees(self.repo_path)
        enhanced_worktrees = self.services.agent.enhance_worktrees_with_agent_status(
            git_worktrees, self.services.state, self.repo_path
        )

        waiting_agents = self.services.agent.find_waiting_agents(enhanced_worktrees)
        if waiting_agents:
            self.exit(result={"action": "switch", "branch": waiting_agents[0].branch})
        else:
            self.notify("No agents waiting for input")

    def action_switch_selected(self) -> None:
        """Switch to selected worktree."""
        if self.table.cursor_row is not None:
            row_key = self.table.get_row_at(self.table.cursor_row)[0]  # Branch name
            self.exit(result={"action": "switch", "branch": row_key})

    def on_unmount(self) -> None:
        """Clean up when unmounting."""
        if self.refresh_timer:
            self.refresh_timer.stop()
