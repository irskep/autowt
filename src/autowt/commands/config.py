"""Configuration command."""

import logging

try:
    from autowt.tui.config import run_config_tui

    HAS_TUI = True
except ImportError:
    HAS_TUI = False

from autowt.models import TerminalMode
from autowt.services.git import GitService
from autowt.services.process import ProcessService
from autowt.services.state import StateService
from autowt.services.terminal import TerminalService

logger = logging.getLogger(__name__)


def configure_settings(
    state_service: StateService,
    git_service: GitService,
    terminal_service: TerminalService,
    process_service: ProcessService,
) -> None:
    """Configure autowt settings using interactive interface."""
    logger.debug("Configuring settings")

    # Try to use Textual TUI if available
    if HAS_TUI:
        run_config_tui(state_service)
    else:
        # Fall back to simple text interface
        _simple_config_interface(state_service)


def _simple_config_interface(state_service: StateService) -> None:
    """Simple text-based configuration interface."""
    print("Autowt Configuration")
    print("===================")
    print()

    # Load current configuration
    config = state_service.load_config()

    print("Current settings:")
    print(f"  Terminal mode: {config.terminal.value}")
    print(f"  Always create new terminal: {config.terminal_always_new}")
    print()

    # Configure terminal mode
    print("Terminal mode options:")
    print("  tab     - Switch to existing session or open new tab")
    print("  window  - Switch to existing session or open new window")
    print("  inplace - Change directory in current terminal")
    print()

    while True:
        terminal_input = input(f"Terminal mode [{config.terminal.value}]: ").strip()
        if not terminal_input:
            break

        try:
            config.terminal = TerminalMode(terminal_input)
            break
        except ValueError:
            print("Invalid terminal mode. Please choose: tab, window, or inplace")

    # Configure always new terminal
    while True:
        always_new_input = input(
            f"Always create new terminal (true/false) [{config.terminal_always_new}]: "
        ).strip()
        if not always_new_input:
            break

        if always_new_input.lower() in ["true", "t", "yes", "y", "1"]:
            config.terminal_always_new = True
            break
        elif always_new_input.lower() in ["false", "f", "no", "n", "0"]:
            config.terminal_always_new = False
            break
        else:
            print("Please enter 'true' or 'false'")

    # Save configuration
    try:
        state_service.save_config(config)
        print("\n✓ Configuration saved successfully")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        print("\n✗ Failed to save configuration")

    # Show final settings
    print("\nFinal settings:")
    print(f"  Terminal mode: {config.terminal.value}")
    print(f"  Always create new terminal: {config.terminal_always_new}")
