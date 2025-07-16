"""Global application configuration and options."""

from dataclasses import dataclass


@dataclass
class GlobalOptions:
    """Global options that affect application behavior."""
    
    auto_confirm: bool = False  # -y flag: automatically confirm all prompts
    debug: bool = False  # --debug flag


# Global instance that gets set by CLI
options = GlobalOptions()