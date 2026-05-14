package git

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// ResolveWorktreeArgument interprets input as either a branch name or
// a path to an existing worktree. If it's a path, the branch name is
// extracted from the worktree's .git file.
//
// The promptFn callback is called when the input is ambiguous (exists
// as a local directory but contains no path separators). It should
// return true to treat the input as a branch name.
func (s *Service) ResolveWorktreeArgument(input string, promptFn func(name string) bool) (string, error) {
	expanded := input
	if strings.HasPrefix(expanded, "~") {
		home, _ := os.UserHomeDir()
		expanded = filepath.Join(home, expanded[1:])
	}

	fi, err := os.Stat(expanded)
	if err != nil {
		// Doesn't exist as a path; treat as branch name.
		return input, nil
	}
	if !fi.IsDir() {
		return input, nil
	}

	// Path exists as a directory. Check if it's ambiguous.
	hasPathSep := strings.ContainsAny(input, "/\\.~")
	if !hasPathSep && promptFn != nil {
		if promptFn(input) {
			return input, nil
		}
		// User chose to treat it as a directory.
		expanded, _ = filepath.Abs(filepath.Join(".", input))
	}

	// Resolve to absolute.
	abs, err := filepath.Abs(expanded)
	if err != nil {
		abs = expanded
	}

	// Check for .git file (worktree marker).
	gitPath := filepath.Join(abs, ".git")
	if _, err := os.Stat(gitPath); err != nil {
		return "", fmt.Errorf("not a git worktree: %s", abs)
	}

	branch, err := s.GetCurrentBranch(abs)
	if err != nil || branch == "" {
		return "", fmt.Errorf("could not determine branch for worktree: %s", abs)
	}
	return branch, nil
}
