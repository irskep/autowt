"""Main CLI entry point for autowt."""

import logging

import click

from autowt.commands.checkout import checkout_branch
from autowt.commands.cleanup import cleanup_worktrees
from autowt.commands.config import configure_settings
from autowt.commands.init import init_autowt
from autowt.commands.ls import list_worktrees
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
            setup_logging(kwargs.get("debug", False))
            terminal_mode = (
                TerminalMode(kwargs["terminal"]) if kwargs.get("terminal") else None
            )
            state_service, git_service, terminal_service, process_service = (
                create_services()
            )
            checkout_branch(
                cmd_name,
                terminal_mode,
                state_service,
                git_service,
                terminal_service,
                process_service,
            )

        # Create a new command with the same options as switch
        branch_cmd = click.Command(
            name=cmd_name,
            callback=branch_command,
            params=[
                click.Option(
                    ["--terminal"],
                    type=click.Choice(["same", "tab", "window", "inplace"]),
                    help="How to open the worktree terminal",
                ),
                click.Option(["--debug"], is_flag=True, help="Enable debug logging"),
            ],
            help=f"Switch to or create a worktree for branch '{cmd_name}'",
        )
        return branch_cmd


@click.group(
    cls=AutowtGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def main(ctx: click.Context, debug: bool) -> None:
    """Git worktree manager.

    Use subcommands like 'init', 'ls', 'cleanup', 'config', or 'switch'.
    Or simply run 'autowt <branch>' to switch to a branch.
    """
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
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cleanup(mode: str, debug: bool) -> None:
    """Clean up merged or remoteless worktrees."""
    setup_logging(debug)
    state_service, git_service, terminal_service, process_service = create_services()
    cleanup_worktrees(
        CleanupMode(mode), state_service, git_service, terminal_service, process_service
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
    type=click.Choice(["same", "tab", "window", "inplace"]),
    help="How to open the worktree terminal",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def switch(branch: str, terminal: str | None, debug: bool) -> None:
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
    )


if __name__ == "__main__":
    main()
