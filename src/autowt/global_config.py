"""Global application configuration and options."""

from dataclasses import dataclass


@dataclass
class GlobalOptions:
    """Global options that affect application behavior."""

    auto_confirm: bool = False  # -y flag: automatically confirm all prompts
    debug: bool = False  # --debug flag
    suppress_rich_output: bool = False  # Suppress all rich output for echo mode
    shell_integration: bool = (
        False  # Set by shell wrapper function via --_shell-integration
    )


# Global instance that gets set by CLI
options = GlobalOptions()
