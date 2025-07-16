"""Prompt utilities that respect global options."""

from autowt.global_config import options


def confirm(message: str, default: bool = False) -> bool:
    """
    Ask for user confirmation, respecting the global auto_confirm option.

    Args:
        message: The prompt message to display
        default: The default value if user just presses enter

    Returns:
        bool: True if confirmed, False otherwise
    """
    if options.auto_confirm:
        print(f"{message} [auto-confirmed]")
        return True

    # Format the prompt based on default
    if default:
        prompt = f"{message} (Y/n) "
        valid_yes = ["y", "yes", ""]  # Empty string defaults to yes
    else:
        prompt = f"{message} (y/N) "
        valid_yes = ["y", "yes"]

    response = input(prompt)
    return response.lower() in valid_yes


def confirm_default_yes(message: str) -> bool:
    """Ask for confirmation with default=True."""
    return confirm(message, default=True)


def confirm_default_no(message: str) -> bool:
    """Ask for confirmation with default=False."""
    return confirm(message, default=False)
