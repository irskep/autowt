package forge

import (
	"log/slog"
	"os/exec"
	"strings"
)

// gitOutput runs a git command in a repository and returns its stdout.
func gitOutput(repoPath string, args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = repoPath
	out, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

// cliOutput runs a forge CLI in a repository so it can resolve the remote,
// and returns its stdout. Any output on stderr is ignored; both gh and glab
// use it for warnings that don't affect the result.
func cliOutput(repoPath, name string, args ...string) ([]byte, error) {
	cmd := exec.Command(name, args...)
	cmd.Dir = repoPath
	out, err := cmd.Output()
	if err != nil {
		slog.Debug("Forge CLI call failed", "cli", name, "args", args, "error", err)
		return nil, err
	}
	return out, nil
}

// cliAvailable reports whether a CLI is on PATH.
func cliAvailable(name string) bool {
	_, err := exec.LookPath(name)
	return err == nil
}
