"""Claude Code hooks installation command."""

import json
import logging
from pathlib import Path

import click

from autowt.console import print_error, print_info, print_success
from autowt.models import Services

logger = logging.getLogger(__name__)

HOOKS_CONFIG = {
    "hooks": {
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": 'ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd) && mkdir -p "$ROOT/.claude/autowt" && echo "{\\"status\\":\\"waiting\\",\\"last_activity\\":\\"$(date -Iseconds)\\"}" > "$ROOT/.claude/autowt/status"',
                    }
                ],
                "autowt_hook_id": "agent_status_stop",
            }
        ],
        "PreToolUse": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": 'ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd) && mkdir -p "$ROOT/.claude/autowt" && echo "{\\"status\\":\\"working\\",\\"last_activity\\":\\"$(date -Iseconds)\\"}" > "$ROOT/.claude/autowt/status"',
                    }
                ],
                "autowt_hook_id": "agent_status_pretooluse",
            }
        ],
        "PostToolUse": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": 'ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd) && mkdir -p "$ROOT/.claude/autowt" && echo "{\\"status\\":\\"idle\\",\\"last_activity\\":\\"$(date -Iseconds)\\"}" > "$ROOT/.claude/autowt/status"',
                    }
                ],
                "autowt_hook_id": "agent_status_posttooluse",
            }
        ],
        "Notification": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": 'ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd) && mkdir -p "$ROOT/.claude/autowt" && echo "{\\"status\\":\\"notification\\",\\"last_activity\\":\\"$(date -Iseconds)\\"}" > "$ROOT/.claude/autowt/status"',
                    }
                ],
                "autowt_hook_id": "agent_status_notification",
            }
        ],
        "SubagentStop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": 'ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd) && mkdir -p "$ROOT/.claude/autowt" && echo "{\\"status\\":\\"subagent_complete\\",\\"last_activity\\":\\"$(date -Iseconds)\\"}" > "$ROOT/.claude/autowt/status"',
                    }
                ],
                "autowt_hook_id": "agent_status_subagent_stop",
            }
        ],
    }
}


def install_hooks_command(
    level: str | None, services: Services, dry_run: bool = False
) -> None:
    """Install Claude Code hooks for agent monitoring."""

    if level is None:
        # Interactive prompt
        click.echo("Choose hook installation level:")
        click.echo("1. User level (affects all projects)")
        click.echo("2. Project level (this project only)")
        click.echo("3. Print to console (manual installation)")

        choice = click.prompt("Enter choice", type=click.Choice(["1", "2", "3"]))
        level = {"1": "user", "2": "project", "3": "console"}[choice]

    if level == "console":
        print_info("Add this to your Claude Code settings:")
        print(json.dumps(HOOKS_CONFIG, indent=2))
        return

    if level == "user":
        settings_path = Path.home() / ".claude" / "settings.json"
        if dry_run:
            print_info(f"Would install hooks to user settings: {settings_path}")
        else:
            print_info(f"Installing hooks to user settings: {settings_path}")
    else:  # project
        settings_path = Path.cwd() / ".claude" / "settings.json"
        if dry_run:
            print_info(f"Would install hooks to project settings: {settings_path}")
        else:
            print_info(f"Installing hooks to project settings: {settings_path}")

    # Ensure directory exists (unless dry-run)
    if not dry_run:
        settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing settings
    existing_settings = {}
    if settings_path.exists():
        try:
            existing_settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            print_error(f"Error: Invalid JSON in {settings_path}")
            return

    # Merge hooks
    if "hooks" not in existing_settings:
        existing_settings["hooks"] = {}

    # Check if autowt hooks need updating
    hooks_need_update = False
    hooks_added = 0
    hooks_removed = 0

    # Check if current autowt hooks match what we want to install
    for hook_type, hook_configs in HOOKS_CONFIG["hooks"].items():
        if hook_type not in existing_settings["hooks"]:
            hooks_need_update = True
            break

        # Get existing autowt hooks for this type
        existing_autowt_hooks = [
            hook
            for hook in existing_settings["hooks"][hook_type]
            if hook.get("autowt_hook_id", "").startswith("agent_status_")
        ]

        # Compare with desired hooks
        desired_hook_ids = {hook["autowt_hook_id"] for hook in hook_configs}
        existing_hook_ids = {
            hook.get("autowt_hook_id") for hook in existing_autowt_hooks
        }

        if desired_hook_ids != existing_hook_ids:
            hooks_need_update = True
            break

        # Also check if hook content changed
        for desired_hook in hook_configs:
            matching_hook = next(
                (
                    h
                    for h in existing_autowt_hooks
                    if h.get("autowt_hook_id") == desired_hook["autowt_hook_id"]
                ),
                None,
            )
            if not matching_hook:
                hooks_need_update = True
                break

            # Compare the nested hooks content
            desired_commands = [h.get("command") for h in desired_hook.get("hooks", [])]
            existing_commands = [
                h.get("command") for h in matching_hook.get("hooks", [])
            ]

            if desired_commands != existing_commands:
                hooks_need_update = True
                break

        if hooks_need_update:
            break

    # Only update if needed
    if hooks_need_update:
        # Remove existing autowt hooks
        for hook_type in existing_settings["hooks"]:
            original_count = len(existing_settings["hooks"][hook_type])
            existing_settings["hooks"][hook_type] = [
                hook
                for hook in existing_settings["hooks"][hook_type]
                if not hook.get("autowt_hook_id", "").startswith("agent_status_")
            ]
            hooks_removed += original_count - len(existing_settings["hooks"][hook_type])

        # Add current autowt hooks
        for hook_type, hook_configs in HOOKS_CONFIG["hooks"].items():
            if hook_type not in existing_settings["hooks"]:
                existing_settings["hooks"][hook_type] = []

            for new_hook in hook_configs:
                existing_settings["hooks"][hook_type].append(new_hook)
                hooks_added += 1

    # Write updated settings (unless dry-run)
    if dry_run:
        if hooks_need_update:
            if hooks_removed > 0 and hooks_added > 0:
                print_info(
                    f"Would update autowt hooks: remove {hooks_removed}, add {hooks_added}"
                )
            elif hooks_added > 0:
                print_info(f"Would add {hooks_added} new hooks")
        else:
            print_info("All autowt hooks are already up to date")
        print_info(f"[DRY RUN] No changes made to {settings_path}")
    else:
        if hooks_need_update:
            if hooks_removed > 0 and hooks_added > 0:
                try:
                    settings_path.write_text(json.dumps(existing_settings, indent=2))
                    print_success(
                        f"Updated autowt hooks in {settings_path} (removed {hooks_removed}, added {hooks_added})"
                    )
                except Exception as e:
                    print_error(f"Error writing settings: {e}")
            elif hooks_added > 0:
                try:
                    settings_path.write_text(json.dumps(existing_settings, indent=2))
                    print_success(
                        f"Added {hooks_added} autowt hooks to {settings_path}"
                    )
                except Exception as e:
                    print_error(f"Error writing settings: {e}")
        else:
            print_info(f"All autowt hooks are already up to date in {settings_path}")


def show_installed_hooks(services: Services) -> None:
    """Show currently installed autowt hooks at user and project levels."""

    user_settings_path = Path.home() / ".claude" / "settings.json"
    project_settings_path = Path.cwd() / ".claude" / "settings.json"

    click.echo("Autowt Hooks Status:")
    click.echo("=" * 40)

    # Check user level
    click.echo("\nUser Level (~/.claude/settings.json):")
    _show_hooks_for_level(user_settings_path)

    # Check project level
    click.echo("\nProject Level (./.claude/settings.json):")
    _show_hooks_for_level(project_settings_path)


def _show_hooks_for_level(settings_path: Path) -> None:
    """Show hook status for a specific settings file."""
    if settings_path.exists():
        try:
            existing_settings = json.loads(settings_path.read_text())
            installed_hooks = _extract_autowt_hooks(existing_settings)

            if installed_hooks:
                # Check if hooks match expected configuration
                hooks_up_to_date = _check_hooks_current(existing_settings)
                status_indicator = "✓" if hooks_up_to_date else "⚠"
                status_text = "up to date" if hooks_up_to_date else "needs update"

                click.echo(f"  {status_indicator} Hooks installed ({status_text}):")
                for hook_type, hooks in installed_hooks.items():
                    click.echo(f"    {hook_type}: {len(hooks)} autowt hook(s)")

                if not hooks_up_to_date:
                    click.echo("    Run 'autowt hooks-install' to update hooks")
            else:
                click.echo("  No autowt hooks installed")
        except json.JSONDecodeError:
            print_error(f"  Error: Invalid JSON in {settings_path}")
        except Exception as e:
            print_error(f"  Error reading file: {e}")
    else:
        click.echo("  No settings file found")


def _check_hooks_current(existing_settings: dict) -> bool:
    """Check if existing autowt hooks match current expected configuration."""
    if "hooks" not in existing_settings:
        return False

    # Check if current autowt hooks match what we want to install
    for hook_type, hook_configs in HOOKS_CONFIG["hooks"].items():
        if hook_type not in existing_settings["hooks"]:
            return False

        # Get existing autowt hooks for this type
        existing_autowt_hooks = [
            hook
            for hook in existing_settings["hooks"][hook_type]
            if hook.get("autowt_hook_id", "").startswith("agent_status_")
        ]

        # Compare with desired hooks
        desired_hook_ids = {hook["autowt_hook_id"] for hook in hook_configs}
        existing_hook_ids = {
            hook.get("autowt_hook_id") for hook in existing_autowt_hooks
        }

        if desired_hook_ids != existing_hook_ids:
            return False

        # Also check if hook content changed
        for desired_hook in hook_configs:
            matching_hook = next(
                (
                    h
                    for h in existing_autowt_hooks
                    if h.get("autowt_hook_id") == desired_hook["autowt_hook_id"]
                ),
                None,
            )
            if (
                not matching_hook
                or matching_hook.get("command") != desired_hook["command"]
            ):
                return False

    return True


def _extract_autowt_hooks(settings: dict) -> dict:
    """Extract autowt hooks from settings, grouped by hook type."""
    autowt_hooks = {}

    if "hooks" not in settings:
        return autowt_hooks

    for hook_type, hooks in settings["hooks"].items():
        autowt_hooks_for_type = [
            hook
            for hook in hooks
            if hook.get("autowt_hook_id", "").startswith("agent_status_")
        ]
        if autowt_hooks_for_type:
            autowt_hooks[hook_type] = autowt_hooks_for_type

    return autowt_hooks
