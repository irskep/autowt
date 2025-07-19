"""Textual TUI for interactive hooks installation."""

import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, RadioButton, RadioSet, Static

from autowt.commands.hooks import HOOKS_CONFIG, _extract_autowt_hooks
from autowt.models import Services


class HooksApp(App):
    """Interactive hooks installation interface."""

    TITLE = "Autowt - Hook Installation"
    CSS_PATH = "hooks.css"
    BINDINGS = [
        Binding("ctrl+s", "install", "Continue & Exit"),
        Binding("enter", "confirm_install", "Continue & Exit"),
        Binding("escape", "cancel", "Cancel & Exit"),
        Binding("q", "cancel", "Quit"),
    ]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        with Vertical():
            yield Label("Hook Installation", classes="title")
            yield Label("")

            # Show current hook status
            yield Label("Current Hook Status:", classes="section-header")
            yield Static(
                self._get_current_status(), id="status-display", classes="status"
            )
            yield Label("")

            # Installation level selection
            yield Label("Installation Level:", classes="section-header")
            with RadioSet(id="installation-level"):
                yield RadioButton(
                    "User level (affects all projects)",
                    value=True,
                    id="level-user",
                )
                yield RadioButton(
                    "Project level (this project only)",
                    value=False,
                    id="level-project",
                )
                yield RadioButton(
                    "Print to console (manual installation)",
                    value=False,
                    id="level-console",
                )

            yield Label("")

            # Project settings file selection (initially hidden)
            with Vertical(id="project-settings", classes="hidden"):
                yield Label("Project Settings File:", classes="section-header")
                with RadioSet(id="project-file"):
                    yield RadioButton(
                        "settings.json (shared with team, tracked by git)",
                        value=True,
                        id="file-shared",
                    )
                    yield RadioButton(
                        "settings.local.json (local only, not tracked by git)",
                        value=False,
                        id="file-local",
                    )
                yield Label("")

            # Action buttons
            with Horizontal(classes="buttons"):
                yield Button("Continue", id="install", variant="primary")
                yield Button("Cancel", id="cancel")

            yield Label("")
            yield Label(
                "Navigation: Tab to move around • Space to select • Enter/Ctrl+S to continue • Esc/Q to cancel",
                classes="help",
            )

    def _get_current_status(self) -> str:
        """Get current hooks status as formatted text."""
        status_lines = []

        # User level
        user_path = Path.home() / ".claude" / "settings.json"
        user_hooks = self._get_hooks_for_path(user_path)
        status_lines.append("User Level (~/.claude/settings.json):")
        if user_hooks:
            for hook_type, hooks in user_hooks.items():
                status_lines.append(f"  ✓ {hook_type}: {len(hooks)} autowt hook(s)")
        else:
            status_lines.append("  No autowt hooks installed")

        status_lines.append("")

        # Project level
        project_path = Path.cwd() / ".claude" / "settings.json"
        project_hooks = self._get_hooks_for_path(project_path)
        status_lines.append("Project Level (./.claude/settings.json):")
        if project_hooks:
            for hook_type, hooks in project_hooks.items():
                status_lines.append(f"  ✓ {hook_type}: {len(hooks)} autowt hook(s)")
        else:
            status_lines.append("  No autowt hooks installed")

        status_lines.append("")

        # Project local level
        project_local_path = Path.cwd() / ".claude" / "settings.local.json"
        project_local_hooks = self._get_hooks_for_path(project_local_path)
        status_lines.append("Project Local Level (./.claude/settings.local.json):")
        if project_local_hooks:
            for hook_type, hooks in project_local_hooks.items():
                status_lines.append(f"  ✓ {hook_type}: {len(hooks)} autowt hook(s)")
        else:
            status_lines.append("  No autowt hooks installed")

        return "\n".join(status_lines)

    def _get_hooks_for_path(self, settings_path: Path) -> dict:
        """Get autowt hooks for a specific settings file."""
        if not settings_path.exists():
            return {}

        try:
            settings = json.loads(settings_path.read_text())
            return _extract_autowt_hooks(settings)
        except (json.JSONDecodeError, Exception):
            return {}

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio button changes."""
        if event.radio_set.id == "installation-level":
            # Show/hide project settings based on selection
            project_section = self.query_one("#project-settings")
            if event.pressed.id == "level-project":
                project_section.remove_class("hidden")
            else:
                project_section.add_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "install":
            self._confirm_selections()
        elif event.button.id == "cancel":
            self.exit()

    def action_install(self) -> None:
        """Confirm selections via keyboard shortcut."""
        self._confirm_selections()

    def action_cancel(self) -> None:
        """Cancel installation via keyboard shortcut."""
        self.exit()

    def action_confirm_install(self) -> None:
        """Confirm selections via Enter key."""
        self._confirm_selections()

    def _confirm_selections(self) -> None:
        """Return user selections to main command for final confirmation."""
        # Get installation level
        level_radio = self.query_one("#installation-level", RadioSet)
        level_button = level_radio.pressed_button

        if level_button.id == "level-console":
            # Exit with console instruction
            self.exit(result="console")
            return

        # Determine settings path and description
        if level_button.id == "level-user":
            settings_path = Path.home() / ".claude" / "settings.json"
            description = "User level (affects all projects)"
        else:  # project level
            project_radio = self.query_one("#project-file", RadioSet)
            project_button = project_radio.pressed_button
            filename = (
                "settings.json"
                if project_button.id == "file-shared"
                else "settings.local.json"
            )
            settings_path = Path.cwd() / ".claude" / filename

            if project_button.id == "file-shared":
                description = "Project level (shared with team, tracked by git)"
            else:
                description = "Project level (local only, not tracked by git)"

        # Exit with installation plan
        result = {
            "action": "install",
            "path": settings_path,
            "description": description,
        }
        self.exit(result=result)

    def _install_hooks(self) -> None:
        """Install hooks based on user selections."""
        # Get installation level
        level_radio = self.query_one("#installation-level", RadioSet)
        level_button = level_radio.pressed_button

        if level_button.id == "level-console":
            # Print to console
            self._print_hooks_config()
            return

        # Determine settings path
        if level_button.id == "level-user":
            settings_path = Path.home() / ".claude" / "settings.json"
        else:  # project level
            project_radio = self.query_one("#project-file", RadioSet)
            project_button = project_radio.pressed_button
            filename = (
                "settings.json"
                if project_button.id == "file-shared"
                else "settings.local.json"
            )
            settings_path = Path.cwd() / ".claude" / filename

        # Install hooks
        try:
            self._install_to_path(settings_path)
            self.exit(message=f"Hooks installed successfully to {settings_path}")
        except Exception as e:
            self.exit(message=f"Error installing hooks: {e}")

    def _print_hooks_config(self) -> None:
        """Print hooks configuration to console."""
        print("\nAdd this to your Claude Code settings:")
        print(json.dumps(HOOKS_CONFIG, indent=2))
        self.exit()

    def _install_to_path(self, settings_path: Path) -> None:
        """Install hooks to a specific settings file."""
        # Ensure directory exists
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing settings
        existing_settings = {}
        if settings_path.exists():
            try:
                existing_settings = json.loads(settings_path.read_text())
            except json.JSONDecodeError:
                pass

        # Initialize hooks section
        if "hooks" not in existing_settings:
            existing_settings["hooks"] = {}

        # Remove existing autowt hooks
        hooks_removed = 0
        for hook_type in existing_settings["hooks"]:
            original_count = len(existing_settings["hooks"][hook_type])
            existing_settings["hooks"][hook_type] = [
                hook
                for hook in existing_settings["hooks"][hook_type]
                if not hook.get("autowt_hook_id", "").startswith("agent_status_")
            ]
            hooks_removed += original_count - len(existing_settings["hooks"][hook_type])

        # Add current autowt hooks
        hooks_added = 0
        for hook_type, hook_configs in HOOKS_CONFIG["hooks"].items():
            if hook_type not in existing_settings["hooks"]:
                existing_settings["hooks"][hook_type] = []

            for new_hook in hook_configs:
                existing_settings["hooks"][hook_type].append(new_hook)
                hooks_added += 1

        # Write updated settings
        settings_path.write_text(json.dumps(existing_settings, indent=2))
