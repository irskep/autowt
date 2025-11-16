"""Configuration-related test fixtures and data builders."""

from autowt.config import CleanupConfig, Config, TerminalConfig
from autowt.models import CleanupMode, TerminalMode


def build_sample_config() -> Config:
    """Build sample configuration for testing."""
    return Config()


def build_custom_config(
    terminal_mode: TerminalMode = TerminalMode.TAB,
    cleanup_mode: CleanupMode = CleanupMode.INTERACTIVE,
    always_new: bool = False,
) -> Config:
    """Build custom configuration with specific settings."""
    return Config(
        terminal=TerminalConfig(
            mode=terminal_mode,
            always_new=always_new,
        ),
        cleanup=CleanupConfig(
            default_mode=cleanup_mode,
        ),
    )
