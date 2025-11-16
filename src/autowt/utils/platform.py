"""Platform-specific utilities for determining default directories."""

import os
import platform
from pathlib import Path


def get_default_config_dir() -> Path:
    """Get the default configuration directory based on platform.

    Returns:
        Path to the configuration directory:
        - macOS: ~/Library/Application Support/autowt
        - Linux: $XDG_CONFIG_HOME/autowt (default: ~/.config/autowt)
        - Windows/Other: ~/.autowt
    """
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "autowt"
    elif system == "Linux":
        # Follow XDG Base Directory Specification
        xdg_config = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
        return xdg_config / "autowt"
    else:
        # Windows or other
        return Path.home() / ".autowt"


def get_default_state_dir() -> Path:
    """Get the default state/data directory based on platform.

    Returns:
        Path to the state/data directory:
        - macOS: ~/Library/Application Support/autowt
        - Linux: $XDG_DATA_HOME/autowt (default: ~/.local/share/autowt)
        - Windows/Other: ~/.autowt
    """
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "autowt"
    elif system == "Linux":
        # Follow XDG Base Directory Specification
        xdg_data = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return xdg_data / "autowt"
    else:
        # Windows or other
        return Path.home() / ".autowt"
