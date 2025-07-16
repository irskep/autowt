"""Main CLI entry point for autowt."""

import logging

import click

from autowt.commands.checkout import checkout_branch
from autowt.commands.cleanup import cleanup_worktrees
from autowt.commands.config import configure_settings
from autowt.commands.init import init_autowt
from autowt.commands.ls import list_worktrees
from autowt.global_config import options
from autowt.models import CleanupMode, TerminalMode
from autowt.services.git import GitService
from autowt.services.process import ProcessService
from autowt.services.state import StateService
from autowt.services.terminal import TerminalService
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


def create_services() -> tuple[
    StateService, GitService, TerminalService, ProcessService
]:
    """Create and return service instances."""
    state_service = StateService()
    git_service = GitService()
    terminal_service = TerminalService()
    process_service = ProcessService()
    return state_service, git_service, terminal_service, process_service


# Custom Group class that handles unknown commands as branch names
class AutowtGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        # First, try to get the command normally
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv

        # If command not found, create a dynamic command that treats it as a branch name
        def branch_command(**kwargs):
            # Set global options for dynamic branch commands
            options.auto_confirm = kwargs.get("auto_confirm", False)
            options.debug = kwargs.get("debug", False)

            setup_logging(kwargs.get("debug", False))
            terminal_mode = (
                TerminalMode(kwargs["terminal"]) if kwargs.get("terminal") else None
            )
            state_service, git_service, terminal_service, process_service = (
                create_services()
            )

            # Get init_script and ignore_same_session from command line args
            init_script = kwargs.get("init")
            ignore_same_session = kwargs.get("ignore_same_session", False)

            checkout_branch(
                cmd_name,
                terminal_mode,
                state_service,
                git_service,
                terminal_service,
                process_service,
                init_script=init_script,
                ignore_same_session=ignore_same_session,
            )

        # Create a new command with the same options as switch
        branch_cmd = click.Command(
            name=cmd_name,
            callback=branch_command,
            params=[
                click.Option(
                    ["--terminal"],
                    type=click.Choice(["tab", "window", "inplace"]),
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
@click.pass_context
def main(ctx: click.Context, auto_confirm: bool, debug: bool) -> None:
    """Git worktree manager.

    Use subcommands like 'init', 'ls', 'cleanup', 'config', or 'switch'.
    Or simply run 'autowt <branch>' to switch to a branch.
    """
    # Set global options
    options.auto_confirm = auto_confirm
    options.debug = debug

    setup_logging(debug)

    # If no subcommand was invoked, show list
    if ctx.invoked_subcommand is None:
        state_service, git_service, terminal_service, process_service = (
            create_services()
        )
        list_worktrees(state_service, git_service, terminal_service, process_service)


@main.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--debug", is_flag=True, help="Enable debug logging")
def init(debug: bool) -> None:
    """Initialize autowt state management in the current repository."""
    setup_logging(debug)
    state_service, git_service, terminal_service, process_service = create_services()
    init_autowt(state_service, git_service, terminal_service, process_service)


@main.command(
    "register-session-for-path",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def register_session_for_path(debug: bool) -> None:
    """Register the current terminal session for the current working directory."""
    setup_logging(debug)
    state_service, git_service, terminal_service, process_service = create_services()

    # Get current session ID
    session_id = terminal_service.get_current_session_id()
    if session_id:
        # Extract branch name from current working directory
        import os
        from pathlib import Path

        worktree_path = Path(os.getcwd())
        branch_name = worktree_path.name

        # Load and update session IDs
        session_ids = state_service.load_session_ids()
        session_ids[branch_name] = session_id
        state_service.save_session_ids(session_ids)
        print(
            f"Registered session {session_id} for branch {branch_name} (path: {worktree_path})"
        )
    else:
        print("Could not detect current session ID")


@main.command(
    "list-sessions",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def list_sessions(debug: bool) -> None:
    """List all terminal sessions with their working directories."""
    setup_logging(debug)
    state_service, git_service, terminal_service, process_service = create_services()

    # Check if we have a terminal that supports session listing
    if hasattr(terminal_service.terminal, "list_sessions_with_directories"):
        sessions = terminal_service.terminal.list_sessions_with_directories()

        if not sessions:
            print("No sessions found or unable to retrieve session information.")
            return

        print("Terminal Sessions:")
        print("-" * 80)
        for session in sessions:
            session_id = session["session_id"]
            working_dir = session["working_directory"]
            print(f"Session ID: {session_id}")
            print(f"Working Directory: {working_dir}")
            print("-" * 80)
    else:
        print("Current terminal does not support session listing.")


@main.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--debug", is_flag=True, help="Enable debug logging")
def ls(debug: bool) -> None:
    """List all worktrees and their status."""
    setup_logging(debug)
    state_service, git_service, terminal_service, process_service = create_services()
    list_worktrees(state_service, git_service, terminal_service, process_service)


@main.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--mode",
    type=click.Choice(["all", "remoteless", "merged", "interactive"]),
    default="all",
    help="Cleanup mode",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without actually removing",
)
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm all prompts")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cleanup(mode: str, dry_run: bool, yes: bool, debug: bool) -> None:
    """Clean up merged or remoteless worktrees."""
    setup_logging(debug)
    state_service, git_service, terminal_service, process_service = create_services()
    cleanup_worktrees(
        CleanupMode(mode),
        state_service,
        git_service,
        terminal_service,
        process_service,
        dry_run,
        yes,
    )


@main.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--debug", is_flag=True, help="Enable debug logging")
def config(debug: bool) -> None:
    """Configure autowt settings using interactive TUI."""
    setup_logging(debug)
    state_service, git_service, terminal_service, process_service = create_services()
    configure_settings(state_service, git_service, terminal_service, process_service)


@main.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("branch")
@click.option(
    "--terminal",
    type=click.Choice(["tab", "window", "inplace"]),
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
    terminal_mode = TerminalMode(terminal) if terminal else None
    state_service, git_service, terminal_service, process_service = create_services()
    checkout_branch(
        branch,
        terminal_mode,
        state_service,
        git_service,
        terminal_service,
        process_service,
        init_script=init,
    )


if __name__ == "__main__":
    main()
