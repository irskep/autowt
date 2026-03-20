"""Install shell completion for autowt."""

import os
import sys
from pathlib import Path

import click

# Shell-specific setup instructions
_BASH_SNIPPET = 'eval "$(_AUTOWT_COMPLETE=bash_source autowt)"'
_ZSH_SNIPPET = 'eval "$(_AUTOWT_COMPLETE=zsh_source autowt)"'
_FISH_SNIPPET = "_AUTOWT_COMPLETE=fish_source autowt | source"

_FISH_COMPLETIONS_DIR = Path.home() / ".config" / "fish" / "completions"
_FISH_COMPLETION_FILE = _FISH_COMPLETIONS_DIR / "autowt.fish"


def _detect_shell() -> str | None:
    """Detect the current shell from the SHELL environment variable."""
    shell_path = os.environ.get("SHELL", "")
    shell_name = Path(shell_path).name.lower()
    if shell_name in ("bash", "zsh", "fish"):
        return shell_name
    return None


def install_completion(shell: str | None) -> None:
    """Print tab completion setup instructions for the given shell.

    Args:
        shell: Shell name ('bash', 'zsh', or 'fish'). Auto-detected if None.
    """
    detected = shell or _detect_shell()

    if detected is None:
        click.echo(
            "Could not detect your shell. "
            "Use --shell bash, --shell zsh, or --shell fish.",
            err=True,
        )
        sys.exit(1)

    if detected == "bash":
        _install_bash()
    elif detected == "zsh":
        _install_zsh()
    elif detected == "fish":
        _install_fish()
    else:
        click.echo(
            f"Shell '{detected}' is not supported. Supported shells: bash, zsh, fish.",
            err=True,
        )
        sys.exit(1)


def _install_bash() -> None:
    click.echo("Add the following line to your ~/.bashrc:\n")
    click.echo(f"    {_BASH_SNIPPET}\n")
    click.echo("Then restart your shell or run:  source ~/.bashrc")


def _install_zsh() -> None:
    click.echo("Add the following line to your ~/.zshrc:\n")
    click.echo(f"    {_ZSH_SNIPPET}\n")
    click.echo("Then restart your shell or run:  source ~/.zshrc")


def _install_fish() -> None:
    click.echo(f"Add the following line to {_FISH_COMPLETION_FILE}:\n")
    click.echo(f"    {_FISH_SNIPPET}\n")
    click.echo("Or run:")
    click.echo(
        f"    mkdir -p ~/.config/fish/completions && "
        f"echo '{_FISH_SNIPPET}' > {_FISH_COMPLETION_FILE}"
    )
