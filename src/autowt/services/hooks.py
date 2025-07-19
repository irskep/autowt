"""Hook detection and management utilities."""

import json
import logging
import shutil
import subprocess
from pathlib import Path

import click

from autowt.commands.hooks import install_hooks_command
from autowt.console import print_info
from autowt.models import Services

logger = logging.getLogger(__name__)


def has_autowt_hooks_installed() -> bool:
    """Check if autowt hooks are installed at user or project level."""
    user_settings_path = Path.home() / ".claude" / "settings.json"
    project_settings_path = Path.cwd() / ".claude" / "settings.json"
    project_local_settings_path = Path.cwd() / ".claude" / "settings.local.json"

    settings_paths = [
        user_settings_path,
        project_settings_path,
        project_local_settings_path,
    ]

    for settings_path in settings_paths:
        if _has_autowt_hooks_in_file(settings_path):
            logger.debug(f"Found autowt hooks in {settings_path}")
            return True

    logger.debug("No autowt hooks found in any settings file")
    return False


def _has_autowt_hooks_in_file(settings_path: Path) -> bool:
    """Check if a specific settings file contains autowt hooks."""
    if not settings_path.exists():
        return False

    try:
        with open(settings_path) as f:
            settings = json.load(f)

        autowt_hooks = _extract_autowt_hooks(settings)
        return len(autowt_hooks) > 0

    except (json.JSONDecodeError, Exception) as e:
        logger.debug(f"Error reading {settings_path}: {e}")
        return False


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


def _is_claude_cli_available() -> bool:
    """Check if Claude CLI is available in PATH or at common installation locations."""
    # First try direct executable lookup
    if shutil.which("claude") is not None:
        return True

    # Check common Claude CLI installation locations
    common_locations = [
        Path.home() / ".claude" / "local" / "claude",
        Path.home() / ".local" / "bin" / "claude",
        Path("/usr/local/bin/claude"),
        Path("/opt/homebrew/bin/claude"),
    ]

    for claude_path in common_locations:
        if claude_path.exists() and claude_path.is_file():
            try:
                # Test if the file is executable
                result = subprocess.run(
                    [str(claude_path), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                logger.debug(
                    f"Found claude at {claude_path}, version test: returncode={result.returncode}"
                )
                # If it runs without error (even if it shows usage), Claude CLI is available
                return result.returncode in [
                    0,
                    1,
                    2,
                ]  # 0=success, 1/2=usage error is fine
            except (
                subprocess.TimeoutExpired,
                subprocess.SubprocessError,
                PermissionError,
            ):
                continue

    logger.debug("Claude CLI not found in PATH or common locations")
    return False


def check_and_prompt_hooks_installation(services: Services) -> None:
    """Check if we should prompt for hooks installation and show prompt if needed."""
    logger.debug("check_and_prompt_hooks_installation() called")

    # Only check in git repositories
    repo_path = services.git.find_repo_root()
    if not repo_path:
        logger.debug("Not in git repository, skipping hooks prompt")
        return

    # Only offer hooks if Claude CLI is available
    if not _is_claude_cli_available():
        logger.debug("Claude CLI not found in PATH, skipping hooks prompt")
        return

    # Don't prompt if we've already asked
    if services.state.has_shown_hooks_prompt():
        logger.debug("Already shown hooks prompt, skipping")
        return

    # Don't prompt if hooks are already installed
    if has_autowt_hooks_installed():
        logger.debug("Hooks already installed, skipping prompt")
        return

    # Show the first-run hooks prompt
    _show_hooks_prompt(services)


def _show_hooks_prompt(services: Services) -> None:
    """Show the first-run hooks installation prompt."""

    # Show Y/n prompt with Y as default
    if click.confirm(
        "Would you like to install Claude Code hooks for enhanced monitoring?\nYou'll be able to choose how and confirm before changes are made.",
        default=True,
    ):
        # Launch the interactive hooks installation TUI
        click.echo("\nLaunching hooks installation...")
        try:
            install_hooks_command(level=None, services=services, dry_run=False)
        except Exception as e:
            click.echo(f"Error during installation: {e}")
            _show_manual_instructions()
    else:
        # User declined - show manual instructions
        _show_manual_instructions()

    # Mark that we've shown the prompt regardless of user choice
    services.state.mark_hooks_prompt_shown()


def _show_manual_instructions() -> None:
    """Show instructions for manual hook installation."""
    click.echo("")
    print_info("To install hooks later, run:")
    click.echo("  autowt hooks-install")
    click.echo("")
    click.echo("For more information about agent monitoring, see:")
    click.echo("  https://github.com/sswam/autowt/blob/main/docs/agents.md")
    click.echo("")
