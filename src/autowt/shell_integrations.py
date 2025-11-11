import os

SHELL_INTEGRATION_FISH = """
# Add to ~/.config/fish/config.fish:
# Example usage: autowt_cd feature-branch
function autowt_cd
    eval (autowt $argv --terminal=echo)
end
""".strip()

SHELL_INTEGRATION_BASH = """
# Add to ~/.bashrc:
# Example usage: autowt_cd feature-branch
autowt_cd() { eval "$(autowt "$@" --terminal=echo)"; }
""".strip()

SHELL_INTEGRATION_ZSH = SHELL_INTEGRATION_BASH.replace(".bashrc", ".zshrc")

SHELL_INTEGRATION_TCSH = """
# Add to ~/.tcshrc:
# Example usage: autowt_cd feature-branch
alias autowt_cd 'eval `autowt \\!* --terminal=echo`'
""".strip()
SHELL_INTEGRATION_CSH = SHELL_INTEGRATION_TCSH.replace(".tcshrc", ".cshrc")

SHELL_INTEGRATION_OIL = """
# Add to ~/.config/oil/oshrc:
# Example usage: autowt_cd feature-branch
autowt_cd() { eval "$(autowt "$@" --terminal=echo)"; }
""".strip()

SHELL_INTEGRATION_NU = """
# Add to ~/.config/nushell/config.nu:
# Example usage: autowt_cd feature-branch
def autowt_cd [...args] {
    load-env (autowt ...$args --terminal=echo | parse 'export {name}={value}' | transpose -r)
}

# Note: nushell requires different syntax. You may need to adjust based on output format.
""".strip()

SHELL_INTEGRATION_ELVISH = """
# Add to ~/.config/elvish/rc.elv:
# Example usage: autowt_cd feature-branch
fn autowt_cd {|@args|
    eval (autowt $@args --terminal=echo)
}
""".strip()

SHELL_INTEGRATION_FALLBACK = """
Your shell is not specifically supported. Open an issue on GitHub:
https://github.com/irskep/autowt/issues/new
""".strip()


def show_shell_config(shell_override: str | None = None) -> None:
    """Show shell integration instructions for the current shell.

    Args:
        shell_override: Optional shell name to show config for. If None, detects from $SHELL.
    """
    shell = shell_override or os.getenv("SHELL", "").split("/")[-1]

    print("# Shell Integration for autowt")
    print(
        "# Add this function to your shell configuration for convenient worktree switching:"
    )
    print()

    # Map shell names to their integration strings
    shell_map = {
        "fish": SHELL_INTEGRATION_FISH,
        "bash": SHELL_INTEGRATION_BASH,
        "zsh": SHELL_INTEGRATION_ZSH,
        "tcsh": SHELL_INTEGRATION_TCSH,
        "csh": SHELL_INTEGRATION_CSH,
        "nu": SHELL_INTEGRATION_NU,
        "oil": SHELL_INTEGRATION_OIL,
        "osh": SHELL_INTEGRATION_OIL,
        "elvish": SHELL_INTEGRATION_ELVISH,
    }

    # Get the appropriate integration string
    integration = shell_map.get(shell, SHELL_INTEGRATION_FALLBACK)
    print(integration)
