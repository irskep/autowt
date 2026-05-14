// Package github provides integration with the GitHub CLI (gh).
package github

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"os/exec"
	"strings"

	"github.com/irskep/autowt/internal/model"
)

// Service handles GitHub-specific operations via the gh CLI.
type Service struct{}

// NewService creates a new GitHub Service.
func NewService() *Service {
	return &Service{}
}

// IsAvailable reports whether the gh CLI is on PATH.
func (s *Service) IsAvailable() bool {
	_, err := exec.LookPath("gh")
	return err == nil
}

// GetUsername returns the authenticated GitHub username, or empty string.
func (s *Service) GetUsername() string {
	out, err := exec.Command("gh", "api", "user", "--jq", ".login").Output()
	if err != nil {
		slog.Debug("Failed to get GitHub username", "error", err)
		return ""
	}
	return strings.TrimSpace(string(out))
}

// IsGitHubRepo checks whether the origin remote points to github.com.
func (s *Service) IsGitHubRepo(repoPath string) bool {
	out, err := exec.Command("git", "-C", repoPath, "remote", "get-url", "origin").Output()
	if err != nil {
		return false
	}
	return strings.Contains(string(out), "github.com")
}

type prInfo struct {
	State       string `json:"state"`
	Number      int    `json:"number"`
	HeadRefName string `json:"headRefName"`
}

// PRStatus returns the status of the PR for a branch: "merged", "closed", "open", or "".
func (s *Service) PRStatus(repoPath, branch string) string {
	out, err := exec.Command(
		"gh", "pr", "list",
		"--repo", ".",
		"--head", branch,
		"--state", "all",
		"--json", "state,number,headRefName",
	).Output()
	if err != nil {
		slog.Debug("Failed to get PR status", "branch", branch, "error", err)
		return ""
	}

	var prs []prInfo
	if err := json.Unmarshal(out, &prs); err != nil {
		return ""
	}
	if len(prs) == 0 {
		return ""
	}

	// Priority: merged > closed > open.
	for _, pr := range prs {
		if strings.EqualFold(pr.State, "merged") {
			return "merged"
		}
	}
	for _, pr := range prs {
		if strings.EqualFold(pr.State, "closed") {
			return "closed"
		}
	}
	for _, pr := range prs {
		if strings.EqualFold(pr.State, "open") {
			return "open"
		}
	}
	return ""
}

// AnalyzeBranchesForCleanup returns BranchStatus for worktrees based on PR state.
func (s *Service) AnalyzeBranchesForCleanup(repoPath string, worktrees []model.WorktreeInfo, hasUncommittedFn func(string) bool) ([]model.BranchStatus, error) {
	if !s.IsAvailable() {
		return nil, fmt.Errorf("GitHub cleanup requires the 'gh' CLI tool. Install it from: https://cli.github.com/")
	}

	var statuses []model.BranchStatus
	for _, wt := range worktrees {
		prState := s.PRStatus(repoPath, wt.Branch)
		isMerged := prState == "merged" || prState == "closed"
		statuses = append(statuses, model.BranchStatus{
			Branch:                wt.Branch,
			HasRemote:             true,
			IsMerged:              isMerged,
			IsIdentical:           false,
			Path:                  wt.Path,
			HasUncommittedChanges: hasUncommittedFn(wt.Path),
		})
	}
	return statuses, nil
}
