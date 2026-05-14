package git

import (
	"strings"

	"github.com/irskep/autowt/internal/model"
)

// parseWorktreeList parses the output of `git worktree list --porcelain`.
func parseWorktreeList(porcelain string) []model.WorktreeInfo {
	var worktrees []model.WorktreeInfo
	var current model.WorktreeInfo
	isFirst := true

	for _, line := range strings.Split(porcelain, "\n") {
		line = strings.TrimSpace(line)

		switch {
		case strings.HasPrefix(line, "worktree "):
			if current.Path != "" {
				worktrees = append(worktrees, current)
			}
			current = model.WorktreeInfo{
				Path:      strings.TrimPrefix(line, "worktree "),
				IsPrimary: isFirst,
			}
			isFirst = false

		case strings.HasPrefix(line, "branch "):
			ref := strings.TrimPrefix(line, "branch ")
			// refs/heads/main -> main
			current.Branch = strings.TrimPrefix(ref, "refs/heads/")

		case line == "bare":
			// Bare repo entry; branch may be empty.

		case line == "detached":
			// Detached HEAD; branch stays empty.
		}
	}

	// Flush last entry.
	if current.Path != "" {
		worktrees = append(worktrees, current)
	}

	return worktrees
}
