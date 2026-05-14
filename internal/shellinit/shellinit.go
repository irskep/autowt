// Package shellinit generates shell integration scripts for bash, zsh, and fish.
package shellinit

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const bashZshTemplate = `autowt() {
    local tmpfile=$(mktemp)
    trap 'rm -f "$tmpfile"' RETURN
    AUTOWT_SHELL_INTEGRATION_FILE="$tmpfile" command autowt "$@"
    local exit_code=$?
    if [ -s "$tmpfile" ]; then
        local eval_cmd=$(cat "$tmpfile")
        %s
    fi
    return $exit_code
}
alias awt=autowt
%s
`

const fishTemplate = `# Usage: autowt shell-init fish | source
# Note: eval (...) does not work in fish for multiline functions.

function autowt
    set -l tmpfile (mktemp)
    set -lx AUTOWT_SHELL_INTEGRATION_FILE $tmpfile
    command autowt $argv
    set -l exit_code $status
    if test -s $tmpfile
        set -l eval_cmd (cat $tmpfile)
        %s
    end
    rm -f $tmpfile
    return $exit_code
end

function awt --wraps=autowt
    autowt $argv
end
`

// SupportedShells lists the shells with integration support.
var SupportedShells = []string{"bash", "zsh", "fish"}

// DetectShell returns the current shell name from $SHELL, or empty string.
func DetectShell() string {
	shell := os.Getenv("SHELL")
	if shell == "" {
		return ""
	}
	name := filepath.Base(shell)
	for _, s := range SupportedShells {
		if name == s {
			return name
		}
	}
	return ""
}

// Generate produces the shell integration script for the given shell.
func Generate(shell string, dryRun bool) (string, error) {
	switch shell {
	case "bash", "zsh":
		return generateBashZsh(shell, dryRun), nil
	case "fish":
		return generateFish(dryRun), nil
	default:
		return "", fmt.Errorf("unsupported shell: %s", shell)
	}
}

func generateBashZsh(shell string, dryRun bool) string {
	var evalLine string
	if dryRun {
		evalLine = `echo "[autowt dry-run] would eval: $eval_cmd" >&2`
	} else {
		evalLine = "echo \"[autowt: eval] $eval_cmd\" >&2\n        eval \"$eval_cmd\""
	}

	var completionLines []string
	for _, cmd := range []string{"autowt", "awt"} {
		envVar := strings.ToUpper(fmt.Sprintf("_%s_COMPLETE", cmd))
		completionLines = append(completionLines,
			fmt.Sprintf(`eval "$(%s=%s_source command %s)"`, envVar, shell, cmd))
	}
	completions := strings.Join(completionLines, "\n")

	return fmt.Sprintf(bashZshTemplate, evalLine, completions)
}

func generateFish(dryRun bool) string {
	var evalLine string
	if dryRun {
		evalLine = `echo "[autowt dry-run] would eval: $eval_cmd" >&2`
	} else {
		evalLine = "echo \"[autowt: eval] $eval_cmd\" >&2\n        eval $eval_cmd"
	}
	return fmt.Sprintf(fishTemplate, evalLine)
}
