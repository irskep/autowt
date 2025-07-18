"""Main CLI entry point for autowt."""

import logging
import os
import sys
from importlib.metadata import version
from pathlib import Path

import click
from click_aliases import ClickAliasedGroup

from autowt.cli_config import create_cli_config_overrides, initialize_config
from autowt.commands.checkout import checkout_branch
from autowt.commands.cleanup import cleanup_worktrees
from autowt.commands.config import configure_settings
from autowt.commands.ls import list_worktrees
from autowt.config import get_config
from autowt.global_config import options
from autowt.models import (
    CleanupCommand,
    CleanupMode,
    Services,
    SwitchCommand,
    TerminalMode,
)
from autowt.utils import setup_command_logging


def setup_logging(debug: bool) -> None:
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Setup command logging to show subprocess execution
    setup_command_logging(debug)


def create_services() -> Services:
    """Create and return a Services container with all service instances."""
    return Services.create()


def auto_register_session(services: Services) -> None:
    """Automatically register the current terminal session if possible."""
    try:
        # Only register if we're in a git repository
        repo_path = services.git.find_repo_root()
        if not repo_path:
            return

        # Get current session ID
        session_id = services.terminal.get_current_session_id()
        if not session_id:
            return

        # Extract branch name from current working directory
        worktree_path = Path(os.getcwd())
        branch_name = worktree_path.name

        # Load existing session IDs to check if already registered
        session_ids = services.state.load_session_ids()

        # Only register if not already registered for this branch
        if branch_name not in session_ids or session_ids[branch_name] != session_id:
            session_ids[branch_name] = session_id
            services.state.save_session_ids(session_ids)

    except Exception:
        # Silently fail - session registration should never break the main command
        pass


def is_interactive_terminal() -> bool:
    """Check if running in an interactive terminal.

    Uses the same approach as Click's internal TTY detection.
    This function can be easily mocked in tests for consistent behavior.
    """
    return sys.stdin.isatty()


def _show_shell_config(shell_override: str | None = None) -> None:
    """Show shell integration instructions for the current shell."""
    shell = shell_override or os.getenv("SHELL", "").split("/")[-1]

    print("# Shell Integration for autowt")
    print(
        "# Add this function to your shell configuration for convenient worktree switching:"
    )
    print()

    if shell == "fish":
        print("# Add to ~/.config/fish/config.fish:")
        print("# Example usage: autowt_cd feature-branch")
        print("function autowt_cd")
        print("    eval (autowt $argv --terminal=echo)")
        print("end")
    elif shell in ["bash", "zsh"]:
        config_file = "~/.bashrc" if shell == "bash" else "~/.zshrc"
        print(f"# Add to {config_file}:")
        print("# Example usage: autowt_cd feature-branch")
        print('autowt_cd() { eval "$(autowt "$@" --terminal=echo)"; }')
    elif shell in ["tcsh", "csh"]:
        config_file = "~/.tcshrc" if shell == "tcsh" else "~/.cshrc"
        print(f"# Add to {config_file}:")
        print("# Example usage: autowt_cd feature-branch")
        print("alias autowt_cd 'eval `autowt \\!* --terminal=echo`'")
    elif shell == "nu":
        print("# Add to ~/.config/nushell/config.nu:")
        print("# Example usage: autowt_cd feature-branch")
        print("def autowt_cd [...args] {")
        print(
            "    load-env (autowt ...$args --terminal=echo | parse 'export {name}={value}' | transpose -r)"
        )
        print("}")
        print()
        print(
            "# Note: nushell requires different syntax. You may need to adjust based on output format."
        )
    elif shell in ["oil", "osh"]:
        print("# Add to ~/.config/oil/oshrc:")
        print("# Example usage: autowt_cd feature-branch")
        print('autowt_cd() { eval "$(autowt "$@" --terminal=echo)"; }')
    elif shell == "elvish":
        print("# Add to ~/.config/elvish/rc.elv:")
        print("# Example usage: autowt_cd feature-branch")
        print("fn autowt_cd {|@args|")
        print("    eval (autowt $@args --terminal=echo)")
        print("}")
    else:
        # Comprehensive fallback for unknown shells
        print(
            f"# Shell '{shell}' not specifically supported. Here are options for common shells:"
        )
        print()
        print("# POSIX-compatible shells (bash, zsh, dash, ash, etc.):")
        print("# Add to your shell's config file (e.g., ~/.bashrc, ~/.zshrc):")
        print("# Example usage: autowt_cd feature-branch")
        print('autowt_cd() { eval "$(autowt "$@" --terminal=echo)"; }')
        print()
        print("# Fish shell - add to ~/.config/fish/config.fish:")
        print("# Example usage: autowt_cd feature-branch")
        print("function autowt_cd")
        print("    eval (autowt $argv --terminal=echo)")
        print("end")
        print()
        print("# C shell variants (csh, tcsh) - add to ~/.cshrc or ~/.tcshrc:")
        print("# Example usage: autowt_cd feature-branch")
        print("alias autowt_cd 'eval `autowt \\!* --terminal=echo`'")
        print()
        print("# For other shells, adapt the above patterns or use manual eval:")
        print('# eval "$(autowt branch-name --terminal=echo)"')


# Custom Group class that handles unknown commands as branch names and supports aliases
class AutowtGroup(ClickAliasedGroup):
    def get_command(self, ctx, cmd_name):
        # First, try to get the command normally
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv

        # If command not found, create a dynamic command that treats it as a branch name
        def branch_command(**kwargs):
            # Set global options for dynamic branch commands
            options.auto_confirm = kwargs.get("auto_confirm", kwargs.get("yes", False))
            options.debug = kwargs.get("debug", False)

            setup_logging(kwargs.get("debug", False))

            # Create CLI overrides for this specific command
            cli_overrides = create_cli_config_overrides(
                terminal=kwargs.get("terminal"),
                init=kwargs.get("init"),
                after_init=kwargs.get("after_init"),
                ignore_same_session=kwargs.get("ignore_same_session", False),
            )

            # Initialize configuration with CLI overrides
            initialize_config(cli_overrides)

            # Get terminal mode from configuration
            config = get_config()
            terminal_mode = (
                config.terminal.mode
                if not kwargs.get("terminal")
                else TerminalMode(kwargs["terminal"])
            )

            services = create_services()
            auto_register_session(services)

            # Create and execute SwitchCommand
            switch_cmd = SwitchCommand(
                branch=cmd_name,
                terminal_mode=terminal_mode,
                init_script=config.scripts.init,
                after_init=kwargs.get("after_init"),
                ignore_same_session=config.terminal.always_new
                or kwargs.get("ignore_same_session", False),
                auto_confirm=kwargs.get("auto_confirm", kwargs.get("yes", False)),
                debug=kwargs.get("debug", False),
            )
            checkout_branch(switch_cmd, services)

        # Create a new command with the same options as switch
        branch_cmd = click.Command(
            name=cmd_name,
            callback=branch_command,
            params=[
                click.Option(
                    ["--terminal"],
                    type=click.Choice(["tab", "window", "inplace", "echo"]),
                    help="How to open the worktree terminal",
                ),
                click.Option(
                    ["-y", "--yes"],
                    "auto_confirm",
                    is_flag=True,
                    help="Automatically confirm all prompts",
                ),
                click.Option(["--debug"], is_flag=True, help="Enable debug logging"),
                click.Option(
                    ["--init"],
                    help="Init script to run in the new terminal",
                ),
                click.Option(
                    ["--after-init"],
                    help="Command to run after init script completes",
                ),
                click.Option(
                    ["--ignore-same-session"],
                    is_flag=True,
                    help="Always create new terminal, ignore existing sessions",
                ),
            ],
            help=f"Switch to or create a worktree for branch '{cmd_name}'",
        )
        return branch_cmd


@click.group(
    cls=AutowtGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "-y",
    "--yes",
    "auto_confirm",
    is_flag=True,
    help="Automatically confirm all prompts",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--version",
    is_flag=True,
    expose_value=False,
    is_eager=True,
    callback=lambda ctx, param, value: (
        click.echo(version("autowt")) if value else None,
        ctx.exit() if value else None,
    ),
    help="Show version and exit",
)
@click.pass_context
def main(ctx: click.Context, auto_confirm: bool, debug: bool) -> None:
    """Git worktree manager.

    Use subcommands like 'ls', 'cleanup', 'config', or 'switch'.
    Or simply run 'autowt <branch>' to switch to a branch.
    """
    # Set global options
    options.auto_confirm = auto_confirm
    options.debug = debug

    setup_logging(debug)

    # Initialize configuration system early
    initialize_config()

    # If no subcommand was invoked, show list
    if ctx.invoked_subcommand is None:
        services = create_services()
        auto_register_session(services)
        list_worktrees(services)


@main.command(
    "register-session-for-path",
    hidden=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def register_session_for_path(debug: bool) -> None:
    """Register the current terminal session for the current working directory."""
    setup_logging(debug)
    services = create_services()

    # Get current session ID
    session_id = services.terminal.get_current_session_id()
    if session_id:
        # Extract branch name from current working directory
        worktree_path = Path(os.getcwd())
        branch_name = worktree_path.name

        # Load and update session IDs
        session_ids = services.state.load_session_ids()
        session_ids[branch_name] = session_id
        services.state.save_session_ids(session_ids)
        print(
            f"Registered session {session_id} for branch {branch_name} (path: {worktree_path})"
        )
    else:
        print("Could not detect current session ID")


@main.command(
    aliases=["list"], context_settings={"help_option_names": ["-h", "--help"]}
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def ls(debug: bool) -> None:
    """List all worktrees and their status."""
    setup_logging(debug)
    services = create_services()
    auto_register_session(services)
    list_worktrees(services, debug=debug)


@main.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--mode",
    type=click.Choice(["all", "remoteless", "merged", "interactive"]),
    default=None,
    help="Cleanup mode (default: interactive in TTY, required otherwise)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without actually removing",
)
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm all prompts")
@click.option(
    "--force", is_flag=True, help="Force remove worktrees with modified files"
)
@click.option(
    "--kill", is_flag=True, help="Force kill processes in worktrees (override config)"
)
@click.option(
    "--no-kill",
    is_flag=True,
    help="Skip killing processes in worktrees (override config)",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cleanup(
    mode: str | None,
    dry_run: bool,
    yes: bool,
    force: bool,
    kill: bool,
    no_kill: bool,
    debug: bool,
) -> None:
    """Clean up merged or remoteless worktrees."""
    # Validate mutually exclusive options
    if kill and no_kill:
        raise click.UsageError("Cannot specify both --kill and --no-kill")

    setup_logging(debug)

    # Create CLI overrides for cleanup command
    cli_overrides = create_cli_config_overrides(
        mode=mode,
        kill=kill,
        no_kill=no_kill,
    )

    # Initialize configuration with CLI overrides
    initialize_config(cli_overrides)

    # Get configuration values
    config = get_config()

    # Use configured mode if not specified
    if mode is None:
        if is_interactive_terminal():
            mode = config.cleanup.default_mode.value
        else:
            # Non-interactive environment (script, CI, etc.) - require explicit mode
            raise click.UsageError(
                "No TTY detected. Please specify --mode explicitly when running in scripts or CI. "
                "Available modes: all, remoteless, merged, interactive"
            )

    services = create_services()
    auto_register_session(services)

    # Determine kill_processes from configuration or override
    kill_processes = None
    if kill:
        kill_processes = True
    elif no_kill:
        kill_processes = False
    else:
        kill_processes = config.cleanup.kill_processes

    cleanup_cmd = CleanupCommand(
        mode=CleanupMode(mode),
        dry_run=dry_run,
        auto_confirm=yes,
        force=force,
        debug=debug,
        kill_processes=kill_processes,
    )
    cleanup_worktrees(cleanup_cmd, services)


@main.command(
    aliases=["configure", "settings"],
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def config(debug: bool) -> None:
    """Configure autowt settings using interactive TUI."""
    setup_logging(debug)
    services = create_services()
    auto_register_session(services)
    configure_settings(services)


@main.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish", "tcsh", "csh", "nu", "oil", "elvish"]),
    help="Override shell detection (useful for generating docs)",
)
def shellconfig(debug: bool, shell: str | None) -> None:
    """Show shell integration instructions for your current shell."""
    setup_logging(debug)
    _show_shell_config(shell)


@main.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("branch")
@click.option(
    "--terminal",
    type=click.Choice(["tab", "window", "inplace", "echo"]),
    help="How to open the worktree terminal",
)
@click.option(
    "--init",
    help="Init script to run in the new terminal",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def switch(branch: str, terminal: str | None, init: str | None, debug: bool) -> None:
    """Switch to or create a worktree for the specified branch."""
    setup_logging(debug)

    # Create CLI overrides for switch command
    cli_overrides = create_cli_config_overrides(
        terminal=terminal,
        init=init,
    )

    # Initialize configuration with CLI overrides
    initialize_config(cli_overrides)

    # Get configuration values
    config = get_config()
    terminal_mode = config.terminal.mode if not terminal else TerminalMode(terminal)

    services = create_services()
    auto_register_session(services)

    # Create and execute SwitchCommand
    switch_cmd = SwitchCommand(
        branch=branch,
        terminal_mode=terminal_mode,
        init_script=config.scripts.init,
        debug=debug,
    )
    checkout_branch(switch_cmd, services)


if __name__ == "__main__":
    main()
