"""Main CLI entry point for autowt."""

import logging
import os
from importlib.metadata import version
from pathlib import Path

import click
from click_aliases import ClickAliasedGroup

from autowt.cli_config import create_cli_config_overrides, initialize_config
from autowt.commands.checkout import checkout_branch
from autowt.commands.cleanup import cleanup_worktrees
from autowt.commands.config import configure_settings, show_config
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
from autowt.prompts import prompt_cleanup_mode_selection
from autowt.tui.switch import run_switch_tui
from autowt.utils import (
    is_interactive_terminal,
    run_command_quiet_on_failure,
    setup_command_logging,
)


def setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Setup command logging to show subprocess execution
    setup_command_logging(debug)


def create_services() -> Services:
    return Services.create()


def check_for_version_updates(services: Services) -> None:
    """Check for version updates and show notification if available."""
    try:
        # Check for secret environment variable to force showing upgrade prompt
        force_upgrade_prompt = os.getenv("AUTOWT_FORCE_UPGRADE_PROMPT")
        if force_upgrade_prompt:
            # Force display of upgrade prompt for testing
            method = services.version_check._detect_installation_method()
            click.echo(
                "💡 Update available: autowt 0.99.0 (you have 0.4.2-dev) [FORCED]",
                err=True,
            )
            click.echo(f"   Run: {method.command}", err=True)
            click.echo(
                "   Release notes: https://github.com/irskep/autowt/releases", err=True
            )
            click.echo("", err=True)
            return

        version_info = services.version_check.check_for_updates()

        if version_info and version_info.update_available:
            click.echo(
                f"💡 Update available: autowt {version_info.latest} "
                f"(you have {version_info.current})",
                err=True,
            )
            if version_info.install_command:
                click.echo(f"   Run: {version_info.install_command}", err=True)
            if version_info.changelog_url:
                click.echo(f"   Release notes: {version_info.changelog_url}", err=True)
            click.echo("", err=True)  # Add blank line for spacing
    except Exception:
        # Silently fail - version checking should never break the main command
        pass


def _run_interactive_switch(services) -> tuple[str | None, bool]:
    """Run interactive switch TUI and return selected branch and if it's new."""
    # Find git repository
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print("Error: Not in a git repository")
        return None, False

    # Get worktrees
    worktrees = services.git.list_worktrees(repo_path)

    # Get all branches
    print("Fetching branches...")
    if not services.git.fetch_branches(repo_path):
        print("Warning: Failed to fetch latest branches")

    # Get all local branches
    all_branches = _get_all_local_branches(repo_path)

    return run_switch_tui(worktrees, all_branches)


def _get_all_local_branches(repo_path: Path) -> list[str]:
    """Get all local branch names."""
    result = run_command_quiet_on_failure(
        ["git", "branch", "--format=%(refname:short)"],
        cwd=repo_path,
        timeout=10,
        description="Get all local branches",
    )

    if result.returncode == 0 and result.stdout.strip():
        branches = [line.strip() for line in result.stdout.strip().split("\n")]
        return [branch for branch in branches if branch and not branch.startswith("*")]

    return []


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
            check_for_version_updates(services)

            # Create and execute SwitchCommand
            switch_cmd = SwitchCommand(
                branch=cmd_name,
                terminal_mode=terminal_mode,
                init_script=config.scripts.session_init,
                after_init=kwargs.get("after_init"),
                ignore_same_session=config.terminal.always_new
                or kwargs.get("ignore_same_session", False),
                auto_confirm=kwargs.get("auto_confirm", kwargs.get("yes", False)),
                debug=kwargs.get("debug", False),
                custom_script=kwargs.get("custom_script"),
                from_branch=kwargs.get("from_branch"),
                dir=kwargs.get("dir"),
                from_dynamic_command=True,
            )
            checkout_branch(switch_cmd, services)

        # Create a new command with the same options as switch
        branch_cmd = click.Command(
            name=cmd_name,
            callback=branch_command,
            params=[
                click.Option(
                    ["--terminal"],
                    type=click.Choice(
                        ["tab", "window", "inplace", "echo", "vscode", "cursor"]
                    ),
                    help="How to open the worktree terminal",
                ),
                click.Option(
                    ["-y", "--yes", "auto_confirm"],
                    is_flag=True,
                    help="Automatically confirm all prompts",
                ),
                click.Option(["--debug"], is_flag=True, help="Enable debug logging"),
                click.Option(
                    ["--after-init"],
                    help="Command to run after session_init script completes",
                ),
                click.Option(
                    ["--ignore-same-session"],
                    is_flag=True,
                    help="Always create new terminal, ignore existing sessions",
                ),
                click.Option(
                    ["--custom-script"],
                    help="Custom script to run with arguments (e.g., 'bugfix 123')",
                ),
                click.Option(
                    ["--from", "from_branch"],
                    help="Source branch/commit to create worktree from (any git rev: branch, tag, HEAD, etc.)",
                ),
                click.Option(
                    ["--dir"],
                    help="Directory path for the new worktree (overrides config pattern)",
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
        check_for_version_updates(services)
        list_worktrees(services)


@main.command(
    aliases=["list", "ll"], context_settings={"help_option_names": ["-h", "--help"]}
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def ls(debug: bool) -> None:
    """List all worktrees and their status."""
    setup_logging(debug)
    services = create_services()
    check_for_version_updates(services)
    list_worktrees(services, debug=debug)


@main.command(
    aliases=["cl", "clean", "prune", "rm", "remove", "del", "delete"],
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.argument("worktrees", nargs=-1, metavar="[WORKTREES...]")
@click.option(
    "--mode",
    type=click.Choice(["all", "remoteless", "merged", "interactive", "github"]),
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
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cleanup(
    worktrees: tuple[str, ...],
    mode: str | None,
    dry_run: bool,
    yes: bool,
    force: bool,
    debug: bool,
) -> None:
    """Clean up merged or remoteless worktrees.

    Can optionally specify worktrees (by branch name or path) to remove.
    If no worktrees are specified, uses mode-based selection.
    """
    setup_logging(debug)

    # Create CLI overrides for cleanup command
    cli_overrides = create_cli_config_overrides(
        mode=mode,
    )

    # Initialize configuration with CLI overrides
    initialize_config(cli_overrides)

    # Get configuration values
    config = get_config()

    # Create services (includes ConfigLoader)
    services = create_services()

    # Use configured mode if not specified
    if mode is None:
        if is_interactive_terminal():
            # Check if user has ever configured a cleanup mode preference
            if not services.config_loader.has_user_configured_cleanup_mode():
                # First run - prompt for preference
                selected_mode = prompt_cleanup_mode_selection()
                mode = selected_mode.value

                # Save preference for future use
                print(f"\nSaving '{mode}' as your default cleanup mode...")
                services.config_loader.save_cleanup_mode(selected_mode)
                print(
                    "You can change this later using 'autowt config' or by editing config.toml\n"
                )
            else:
                # User has configured preference - use it
                mode = config.cleanup.default_mode.value
        else:
            # Non-interactive environment (script, CI, etc.) - require explicit mode
            raise click.UsageError(
                "No TTY detected. Please specify --mode explicitly when running in scripts or CI. "
                "Available modes: all, remoteless, merged, interactive, github"
            )
    check_for_version_updates(services)

    cleanup_cmd = CleanupCommand(
        mode=CleanupMode(mode),
        dry_run=dry_run,
        auto_confirm=yes,
        force=force,
        debug=debug,
        worktrees=list(worktrees) if worktrees else None,
    )
    cleanup_worktrees(cleanup_cmd, services)


@main.command(
    aliases=["configure", "settings", "cfg", "conf"],
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--show", is_flag=True, help="Show current configuration values")
def config(debug: bool, show: bool) -> None:
    """Configure autowt settings using interactive TUI."""
    setup_logging(debug)
    services = create_services()

    if show:
        show_config(services)
    else:
        configure_settings(services)


@main.command(
    aliases=["sw", "checkout", "co", "goto", "go"],
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.argument("branch", required=False, metavar="BRANCH_OR_PATH")
@click.option(
    "--terminal",
    type=click.Choice(["tab", "window", "inplace", "echo", "vscode", "cursor"]),
    help="How to open the worktree terminal",
)
@click.option(
    "--after-init",
    help="Command to run after session_init script completes",
)
@click.option(
    "--ignore-same-session",
    is_flag=True,
    help="Always create new terminal, ignore existing sessions",
)
@click.option(
    "-y", "--yes", "auto_confirm", is_flag=True, help="Auto-confirm all prompts"
)
@click.option(
    "--from",
    "from_branch",
    help="Source branch/commit to create worktree from (any git rev: branch, tag, HEAD, etc.)",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--custom-script",
    help="Custom script to run with arguments (e.g., 'bugfix 123')",
)
@click.option(
    "--dir",
    help="Directory path for the new worktree (overrides config pattern)",
)
def switch(
    branch: str | None,
    terminal: str | None,
    after_init: str | None,
    ignore_same_session: bool,
    auto_confirm: bool,
    from_branch: str | None,
    debug: bool,
    custom_script: str | None,
    dir: str | None,
) -> None:
    """Switch to or create a worktree for the specified branch or path.

    BRANCH_OR_PATH can be either a branch name (e.g., 'my-feature') or
    a path to an existing worktree (e.g., '../myproject-worktrees/feature').
    """
    setup_logging(debug)

    # If no branch provided, show interactive TUI
    if not branch:
        services = create_services()
        check_for_version_updates(services)

        selected_branch, is_new = _run_interactive_switch(services)
        if not selected_branch:
            return  # User cancelled

        # Use the selected branch
        target_branch = selected_branch
    else:
        # Branch was provided as argument
        target_branch = branch

    # Create services if not already created
    if not branch:
        # services was already created above for interactive mode
        pass
    else:
        services = create_services()
        check_for_version_updates(services)

    # Create CLI overrides for switch command (now includes all options)
    cli_overrides = create_cli_config_overrides(
        terminal=terminal,
        after_init=after_init,
        ignore_same_session=ignore_same_session,
        custom_script=custom_script,
    )

    # Initialize configuration with CLI overrides
    initialize_config(cli_overrides)

    # Get configuration values
    config = get_config()
    terminal_mode = config.terminal.mode if not terminal else TerminalMode(terminal)

    # Create and execute SwitchCommand with full option support
    switch_cmd = SwitchCommand(
        branch=target_branch,
        terminal_mode=terminal_mode,
        init_script=config.scripts.session_init,
        after_init=after_init,
        ignore_same_session=config.terminal.always_new or ignore_same_session,
        auto_confirm=auto_confirm,
        debug=debug,
        custom_script=custom_script,
        from_branch=from_branch,
        dir=dir,
    )
    checkout_branch(switch_cmd, services)


if __name__ == "__main__":
    main()
