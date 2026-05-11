"""Configuration command."""

import logging

from autowt.models import Services

logger = logging.getLogger(__name__)


def show_config(services: Services) -> None:
    """Show current configuration values."""
    config = services.state.load_config()

    print("Current Configuration:")
    print("=" * 50)
    print()

    print("Terminal:")
    print(f"  mode: {config.terminal.mode.value}")
    print(f"  always_new: {config.terminal.always_new}")
    print(f"  program: {config.terminal.program}")
    print()

    print("Worktree:")
    print(f"  directory_pattern: {config.worktree.directory_pattern}")
    print(f"  auto_fetch: {config.worktree.auto_fetch}")
    print(f"  branch_prefix: {config.worktree.branch_prefix}")
    print()

    print("Cleanup:")
    print(f"  default_mode: {config.cleanup.default_mode.value}")
    print()

    print("Scripts:")
    print(f"  session_init: {config.scripts.session_init}")
    if config.scripts.custom:
        print("  custom:")
        for name, script in config.scripts.custom.items():
            print(f"    {name}: {script}")
    else:
        print("  custom: {}")
    print()

    print("Confirmations:")
    print(f"  cleanup_multiple: {config.confirmations.cleanup_multiple}")
    print(f"  force_operations: {config.confirmations.force_operations}")
    print()

    print("Config Files:")
    print(f"  Global: {services.config_loader.global_config_file}")
    print("  Project: autowt.toml or .autowt.toml in repository root")


def configure_settings(services: Services) -> None:
    """Configure autowt settings interactively."""
    from autowt.tui.config import ConfigApp  # noqa: PLC0415

    logger.debug("Configuring settings")

    app = ConfigApp(services)
    app.run()
