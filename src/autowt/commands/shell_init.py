"""Shell integration script generation."""

from autowt.services.terminal import SHELL_INTEGRATION_SENTINEL

_BASH_ZSH_TEMPLATE = """\
autowt() {{
    local line eval_cmd=""
    command autowt --_shell-integration "$@" | while IFS= read -r line; do
        if [[ "$line" == {sentinel}* ]]; then
            eval_cmd="${{line#{sentinel}}}"
        else
            printf '%s\\n' "$line"
        fi
    done
    local exit_code=${{PIPESTATUS[0]}}
    if [ -n "$eval_cmd" ]; then
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
    set -l eval_cmd ""
    command autowt --_shell-integration $argv | while read -l line
        if string match -q '{sentinel}*' -- $line
            set eval_cmd (string replace '{sentinel}' '' -- $line)
        else
            printf '%s\\n' $line
        end
    end
    set -l exit_code $pipestatus[1]
    if test -n "$eval_cmd"
        {eval_line}
    end
    return $exit_code
end

function awt --wraps=autowt
    autowt $argv
end
"""


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
            eval_line = 'echo "[autowt dry-run] would eval: $eval_cmd"'
        else:
            eval_line = 'eval "$eval_cmd"'
        return _BASH_ZSH_TEMPLATE.format(
            sentinel=SHELL_INTEGRATION_SENTINEL,
            eval_line=eval_line,
        )
    elif shell == "fish":
        if dry_run:
            eval_line = 'echo "[autowt dry-run] would eval: $eval_cmd"'
        else:
            eval_line = "eval $eval_cmd"
        return _FISH_TEMPLATE.format(
            sentinel=SHELL_INTEGRATION_SENTINEL,
            eval_line=eval_line,
        )
    else:
        msg = f"Unsupported shell: {shell}"
        raise ValueError(msg)
