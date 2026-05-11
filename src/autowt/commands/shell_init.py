"""Shell integration script generation."""

import os
from pathlib import Path

_BASH_ZSH_TEMPLATE = """\
autowt() {{
    local tmpfile=$(mktemp)
    trap 'rm -f "$tmpfile"' RETURN
    AUTOWT_SHELL_INTEGRATION_FILE="$tmpfile" command autowt "$@"
    local exit_code=$?
    if [ -s "$tmpfile" ]; then
        local eval_cmd=$(cat "$tmpfile")
        {eval_line}
    fi
    return $exit_code
}}
alias awt=autowt
"""

_FISH_TEMPLATE = """\
# Usage: autowt shell-init fish | source
# Note: eval (...) does not work in fish for multiline functions.

function autowt
    set -l tmpfile (mktemp)
    set -lx AUTOWT_SHELL_INTEGRATION_FILE $tmpfile
    command autowt $argv
    set -l exit_code $status
    if test -s $tmpfile
        set -l eval_cmd (cat $tmpfile)
        {eval_line}
    end
    rm -f $tmpfile
    return $exit_code
end

function awt --wraps=autowt
    autowt $argv
end
"""

SUPPORTED_SHELLS = ("bash", "zsh", "fish")


def detect_shell() -> str | None:
    """Detect the current shell from the SHELL environment variable."""
    shell_env = os.environ.get("SHELL", "")
    if shell_env:
        name = Path(shell_env).name
        if name in SUPPORTED_SHELLS:
            return name
    return None


def get_shell_init_script(shell: str, *, dry_run: bool = False) -> str:
    """Generate shell integration code for the given shell.

    Args:
        shell: One of "bash", "zsh", "fish".
        dry_run: If True, generate a variant that prints commands
                 instead of eval'ing them.

    Returns:
        Shell function definition as a string.
    """
    if shell in ("bash", "zsh"):
        if dry_run:
            eval_line = 'echo "[autowt dry-run] would eval: $eval_cmd" >&2'
        else:
            eval_line = 'echo "[autowt: eval] $eval_cmd" >&2\n        eval "$eval_cmd"'
        return _BASH_ZSH_TEMPLATE.format(eval_line=eval_line)
    elif shell == "fish":
        if dry_run:
            eval_line = 'echo "[autowt dry-run] would eval: $eval_cmd" >&2'
        else:
            eval_line = 'echo "[autowt: eval] $eval_cmd" >&2\n        eval $eval_cmd'
        return _FISH_TEMPLATE.format(eval_line=eval_line)
    else:
        msg = f"Unsupported shell: {shell}"
        raise ValueError(msg)
