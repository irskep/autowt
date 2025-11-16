"""CLI configuration integration for autowt.

This module handles the integration between Click CLI arguments and the configuration system.
It provides utilities to convert CLI options to config overrides and initialize the global config.
"""

import logging
import shlex
from pathlib import Path
from typing import Any

from autowt.config import get_config, load_config

logger = logging.getLogger(__name__)


def create_cli_config_overrides(
    terminal: str | None = None,
    after_init: str | None = None,
    ignore_same_session: bool | None = None,
    mode: str | None = None,
    custom_script: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create configuration overrides from CLI arguments.

    Args:
        terminal: Terminal mode override
        after_init: After-init script override
        ignore_same_session: Always new terminal override
        mode: Cleanup mode override
        custom_script: Custom script name override
        **kwargs: Additional CLI arguments to ignore

    Returns:
        Dictionary of configuration overrides
    """
    overrides: dict[str, Any] = {}

    # Terminal configuration overrides
    if terminal is not None:
        overrides.setdefault("terminal", {})["mode"] = terminal

    if ignore_same_session is not None:
        overrides.setdefault("terminal", {})["always_new"] = ignore_same_session

    # Handle custom scripts
    if custom_script is not None:
        # This would be used in commands that support --custom-script
        overrides.setdefault("scripts", {}).setdefault(
            "_selected_custom", custom_script
        )

    # Cleanup configuration overrides
    if mode is not None:
        overrides.setdefault("cleanup", {})["default_mode"] = mode

    return overrides


def initialize_config(cli_overrides: dict[str, Any] | None = None) -> None:
    """Initialize global configuration with CLI overrides.

    This should be called early in the CLI lifecycle to set up configuration
    before any commands run.

    Args:
        cli_overrides: Optional dictionary of CLI argument overrides
    """
    try:
        # Find project directory (current working directory)
        project_dir = Path.cwd()

        # Load configuration with all sources and CLI overrides
        load_config(project_dir=project_dir, cli_overrides=cli_overrides)

        logger.debug("Configuration initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize configuration: {e}")
        # Fall back to loading without project dir
        load_config(cli_overrides=cli_overrides)


def resolve_custom_script_with_interpolation(script_spec: str) -> str | None:
    """Resolve a custom script specification with argument interpolation.

    Args:
        script_spec: Space-separated script specification like "bugfix 123"
                    where first part is script name, rest are arguments

    Returns:
        The resolved script command with arguments interpolated, or None if script not found

    Example:
        script_spec = "bugfix 123"
        config has: bugfix = 'claude "Fix bug described in issue $1"'
        returns: 'claude "Fix bug described in issue 123"'

    Note:
        Arguments are inserted directly without shell escaping to preserve shell features.
    """
    if not script_spec:
        return None

    # Parse script name and arguments using shell-aware splitting
    try:
        parts = shlex.split(script_spec)
    except ValueError as e:
        logger.warning(
            f"Invalid shell syntax in custom script spec '{script_spec}': {e}"
        )
        return None

    if not parts:
        return None

    script_name = parts[0]
    args = parts[1:]

    # Get the script template from config
    script_template = get_config().scripts.custom.get(script_name)
    if not script_template:
        logger.warning(f"Custom script '{script_name}' not found in configuration")
        return None

    # Perform argument interpolation
    resolved_script = script_template
    for i, arg in enumerate(args, 1):
        placeholder = f"${i}"
        resolved_script = resolved_script.replace(placeholder, arg)

    return resolved_script
