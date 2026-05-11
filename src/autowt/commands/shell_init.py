"""Shell integration script generation."""

from autowt.services.terminal import SHELL_INTEGRATION_SENTINEL

_BASH_ZSH_TEMPLATE = """\
autowt() {{
    local output exit_code
    output=$(command autowt --_shell-integration "$@")
    exit_code=$?
    if [[ "$output" == {sentinel}* ]]; then
        {eval_line}
    elif [ -n "$output" ]; then
        printf '%s\\n' "$output"
    fi
    return $exit_code
}}
alias awt=autowt
"""

_FISH_TEMPLATE = """\
function autowt
    set -l output (command autowt --_shell-integration $argv)
    set -l exit_code $status
    if string match -q '{sentinel}*' -- $output
        {eval_line}
    else if test -n "$output"
        printf '%s\\n' $output
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
            eval_line = (
                'echo "[autowt dry-run] would eval:'
                " ${output#" + SHELL_INTEGRATION_SENTINEL + '}"'
            )
        else:
            eval_line = 'eval "${output#' + SHELL_INTEGRATION_SENTINEL + '}"'
        return _BASH_ZSH_TEMPLATE.format(
            sentinel=SHELL_INTEGRATION_SENTINEL,
            eval_line=eval_line,
        )
    elif shell == "fish":
        if dry_run:
            eval_line = (
                'echo "[autowt dry-run] would eval:'
                " \"(string replace '" + SHELL_INTEGRATION_SENTINEL + "' '' -- $output)"
            )
        else:
            eval_line = (
                "eval (string replace '"
                + SHELL_INTEGRATION_SENTINEL
                + "' '' -- $output)"
            )
        return _FISH_TEMPLATE.format(
            sentinel=SHELL_INTEGRATION_SENTINEL,
            eval_line=eval_line,
        )
    else:
        msg = f"Unsupported shell: {shell}"
        raise ValueError(msg)
