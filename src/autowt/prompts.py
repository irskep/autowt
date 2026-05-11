"""Prompt utilities that respect global options."""

import shutil
import sys

import click

from autowt.global_config import options
from autowt.models import CleanupMode


def confirm(message: str, default: bool = False) -> bool:
    """
    Ask for user confirmation, respecting the global auto_confirm option.

    When shell integration is active, prompts are written to stderr so they
    don't get captured by the shell wrapper function.

    Args:
        message: The prompt message to display
        default: The default value if user just presses enter

    Returns:
        bool: True if confirmed, False otherwise
    """
    if options.auto_confirm:
        out = sys.stderr if options.shell_integration else sys.stdout
        print(f"{message} [auto-confirmed]", file=out)
        return True

    # Format the prompt based on default
    if default:
        prompt = f"{message} (Y/n) "
        valid_yes = ["y", "yes", ""]  # Empty string defaults to yes
    else:
        prompt = f"{message} (y/N) "
        valid_yes = ["y", "yes"]

    if options.shell_integration:
        # input(prompt) writes prompt to stdout, which would be captured by
        # the shell wrapper. Write to stderr instead, then read without prompt.
        print(prompt, end="", file=sys.stderr, flush=True)
        response = input()
    else:
        response = input(prompt)
    return response.lower() in valid_yes


def confirm_default_yes(message: str) -> bool:
    """Ask for confirmation with default=True."""
    return confirm(message, default=True)


def confirm_default_no(message: str) -> bool:
    """Ask for confirmation with default=False."""
    return confirm(message, default=False)


def prompt_cleanup_mode_selection() -> CleanupMode:
    """Prompt user to select their preferred cleanup mode on first run."""
    gh_available = shutil.which("gh") is not None

    print("\nNo cleanup mode preference found. Please select your default mode:\n")

    # Build options list
    options_list = [
        (
            "1",
            "interactive",
            "Review and select branches manually (recommended for beginners)",
        ),
        ("2", "merged", "Automatically remove branches merged into main"),
        ("3", "remoteless", "Automatically remove branches without remote tracking"),
    ]

    if gh_available:
        options_list.append(
            ("4", "github", "Use GitHub CLI to remove branches with merged/closed PRs")
        )

    # Display options
    for num, mode, description in options_list:
        print(f"{num}. {mode} - {description}")

    if not gh_available:
        print(
            "\nNote: GitHub mode would also be available if you install the GitHub CLI (gh)."
        )
        print("Learn more at: https://cli.github.com/")

    # Get user choice
    valid_choices = [opt[0] for opt in options_list]
    prompt_text = f"\nSelect mode ({'-'.join(valid_choices)})"

    choice = click.prompt(prompt_text, type=click.Choice(valid_choices))

    # Map choice to mode
    mode_map = {opt[0]: opt[1] for opt in options_list}
    selected_mode = mode_map[choice]

    # Convert string to CleanupMode enum
    return CleanupMode(selected_mode)
