// Package shellcmd centralizes execution of user-provided shell snippets.
package shellcmd

import (
	"context"
	"io"
	"os/exec"
)

const (
	// Shell is the interpreter used for inline autowt scripts.
	Shell = "sh"
	// ShellFlag tells Shell to execute the following argument as a command string.
	ShellFlag = "-c"
)

// Run executes script with sh -c.
func Run(ctx context.Context, script, dir string, env []string, stdout, stderr io.Writer) error {
	cmd := exec.CommandContext(ctx, Shell, ShellFlag, script)
	cmd.Dir = dir
	cmd.Env = env
	cmd.Stdout = stdout
	cmd.Stderr = stderr
	return cmd.Run()
}

// Output executes script with sh -c and returns stdout.
func Output(ctx context.Context, script, dir string) ([]byte, error) {
	cmd := exec.CommandContext(ctx, Shell, ShellFlag, script)
	cmd.Dir = dir
	return cmd.Output()
}
