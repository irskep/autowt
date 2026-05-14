// Package git provides git subprocess wrappers for worktree operations.
package git

import (
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/irskep/autowt/internal/model"
)

// Service orchestrates git operations for autowt.
type Service struct{}

// NewService creates a new git Service.
func NewService() *Service {
	return &Service{}
}

// FindRepoRoot walks up from startDir looking for a git repository.
// Returns the repo root path, or an error if not found.
func (s *Service) FindRepoRoot(startDir string) (string, error) {
	if startDir == "" {
		var err error
		startDir, err = os.Getwd()
		if err != nil {
			return "", err
		}
	}

	dir := startDir
	for {
		// Regular repo or worktree: .git exists.
		gitPath := filepath.Join(dir, ".git")
		if fi, err := os.Stat(gitPath); err == nil {
			if fi.IsDir() {
				// Regular repo root.
				return dir, nil
			}
			// .git is a file (worktree). Read it to find the main repo.
			return s.resolveWorktreeGitFile(dir, gitPath)
		}

		// Bare repo: directory has HEAD, objects, refs.
		if isBareRepo(dir) {
			return dir, nil
		}

		// Check for bare repos in subdirectories (*.git pattern).
		if bareDir, err := findBareRepoInDir(dir); err != nil {
			return "", err
		} else if bareDir != "" {
			return bareDir, nil
		}

		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}

	return "", fmt.Errorf("not in a git repository (searched from %s)", startDir)
}

func (s *Service) resolveWorktreeGitFile(worktreeDir, gitFilePath string) (string, error) {
	data, err := os.ReadFile(gitFilePath)
	if err != nil {
		return "", err
	}
	line := strings.TrimSpace(string(data))
	if !strings.HasPrefix(line, "gitdir: ") {
		return worktreeDir, nil
	}
	gitDir := strings.TrimPrefix(line, "gitdir: ")
	if !filepath.IsAbs(gitDir) {
		gitDir = filepath.Join(worktreeDir, gitDir)
	}
	gitDir = filepath.Clean(gitDir)

	// gitDir is something like /repo/.git/worktrees/name.
	// Walk up to find the actual .git directory, then its parent is the repo root.
	dir := gitDir
	for {
		if filepath.Base(dir) == ".git" {
			return filepath.Dir(dir), nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return worktreeDir, nil
}

func isBareRepo(dir string) bool {
	for _, name := range []string{"HEAD", "objects", "refs"} {
		if _, err := os.Stat(filepath.Join(dir, name)); err != nil {
			return false
		}
	}
	return true
}

// findBareRepoInDir looks for *.git subdirectories that are bare repos.
// Returns an error if multiple are found (ambiguous).
func findBareRepoInDir(dir string) (string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return "", nil
	}
	var found []string
	for _, e := range entries {
		if e.IsDir() && strings.HasSuffix(e.Name(), ".git") {
			sub := filepath.Join(dir, e.Name())
			if isBareRepo(sub) {
				found = append(found, sub)
			}
		}
	}
	switch len(found) {
	case 0:
		return "", nil
	case 1:
		return found[0], nil
	default:
		names := make([]string, len(found))
		for i, f := range found {
			names[i] = filepath.Base(f)
		}
		return "", fmt.Errorf("multiple bare git repositories found in %s: %s. Please run autowt from within one of the specific repository directories", dir, strings.Join(names, ", "))
	}
}

// GetCurrentBranch returns the current branch name for the repo at path.
func (s *Service) GetCurrentBranch(repoPath string) (string, error) {
	out, err := gitOutput(repoPath, "branch", "--show-current")
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(out), nil
}

// ListWorktrees returns all worktrees for the repo at path.
func (s *Service) ListWorktrees(repoPath string) ([]model.WorktreeInfo, error) {
	out, err := gitOutput(repoPath, "worktree", "list", "--porcelain")
	if err != nil {
		return nil, err
	}
	return parseWorktreeList(out), nil
}

// GetCurrentWorktree finds the worktree containing currentPath.
func (s *Service) GetCurrentWorktree(currentPath string, worktrees []model.WorktreeInfo) *model.WorktreeInfo {
	var best *model.WorktreeInfo
	bestLen := 0
	for i, wt := range worktrees {
		if strings.HasPrefix(currentPath, wt.Path) {
			if len(wt.Path) > bestLen {
				best = &worktrees[i]
				bestLen = len(wt.Path)
			}
		}
	}
	return best
}

// FetchBranches runs git fetch --prune with output visible.
func (s *Service) FetchBranches(repoPath string) error {
	cmd := exec.Command("git", "-C", repoPath, "fetch", "--prune")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// CreateWorktree creates a worktree using the branch resolver strategy.
func (s *Service) CreateWorktree(repoPath, branch, worktreePath, fromBranch string) error {
	if err := os.MkdirAll(filepath.Dir(worktreePath), 0o755); err != nil {
		return err
	}

	args, err := s.resolveWorktreeSource(repoPath, branch, fromBranch)
	if err != nil {
		return err
	}

	// Prepend: git -C repoPath worktree add worktreePath ...
	fullArgs := append([]string{"-C", repoPath, "worktree", "add", worktreePath}, args...)
	cmd := exec.Command("git", fullArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// RemoveWorktree removes a worktree. If force is true, uses --force.
func (s *Service) RemoveWorktree(repoPath, worktreePath string, force bool) error {
	args := []string{"-C", repoPath, "worktree", "remove", worktreePath}
	if force {
		args = append(args, "--force")
	}
	cmd := exec.Command("git", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// DeleteBranch deletes a local branch. Uses -D (force) by default.
func (s *Service) DeleteBranch(repoPath, branch string) error {
	return gitRun(repoPath, "branch", "-D", branch)
}

// HasUncommittedChanges reports whether the worktree has dirty files.
func (s *Service) HasUncommittedChanges(worktreePath string) bool {
	out, err := gitOutput(worktreePath, "status", "--porcelain")
	if err != nil {
		return false
	}
	return strings.TrimSpace(out) != ""
}

// AnalyzeBranchesForCleanup returns BranchStatus for each worktree.
func (s *Service) AnalyzeBranchesForCleanup(repoPath string, worktrees []model.WorktreeInfo) []model.BranchStatus {
	defaultBranch := s.getDefaultBranch(repoPath)
	var statuses []model.BranchStatus
	for _, wt := range worktrees {
		statuses = append(statuses, model.BranchStatus{
			Branch:                wt.Branch,
			HasRemote:             s.branchHasRemote(repoPath, wt.Branch),
			IsMerged:              s.branchIsMerged(repoPath, wt.Branch, defaultBranch),
			IsIdentical:           s.branchesAreIdentical(repoPath, wt.Branch, defaultBranch),
			Path:                  wt.Path,
			HasUncommittedChanges: s.HasUncommittedChanges(wt.Path),
		})
	}
	return statuses
}

// BranchExistsLocally checks if a branch exists as a local ref.
func (s *Service) BranchExistsLocally(repoPath, branch string) bool {
	return gitRun(repoPath, "show-ref", "--verify", "refs/heads/"+branch) == nil
}

// BranchExistsRemotely checks if a branch exists on a remote.
func (s *Service) BranchExistsRemotely(repoPath, branch string) bool {
	remotes := []string{"origin", "upstream"}
	for _, remote := range remotes {
		if gitRun(repoPath, "show-ref", "--verify", fmt.Sprintf("refs/remotes/%s/%s", remote, branch)) == nil {
			return true
		}
	}
	return false
}

// CheckRemoteBranchAvailability checks if a branch exists on a remote.
// Returns (exists, remoteName).
func (s *Service) CheckRemoteBranchAvailability(repoPath, branch string) (bool, string) {
	for _, remote := range []string{"origin", "upstream"} {
		ref := fmt.Sprintf("refs/remotes/%s/%s", remote, branch)
		if gitRun(repoPath, "show-ref", "--verify", ref) == nil {
			return true, remote
		}
		// Try fetching the specific branch.
		if gitRun(repoPath, "fetch", remote, branch) == nil {
			if gitRun(repoPath, "show-ref", "--verify", ref) == nil {
				return true, remote
			}
		}
	}
	return false, ""
}

// resolveWorktreeSource determines the git worktree add arguments.
func (s *Service) resolveWorktreeSource(repoPath, branch, fromBranch string) ([]string, error) {
	if fromBranch != "" {
		return []string{"-b", branch, fromBranch}, nil
	}

	if s.BranchExistsLocally(repoPath, branch) {
		return []string{branch}, nil
	}

	// Check remotes.
	for _, remote := range []string{"origin", "upstream"} {
		ref := fmt.Sprintf("refs/remotes/%s/%s", remote, branch)
		if gitRun(repoPath, "show-ref", "--verify", ref) == nil {
			return []string{"--track", "-b", branch, ref}, nil
		}
	}

	// New branch from best start point.
	startPoint := s.findBestStartPoint(repoPath)
	return []string{"--no-track", "-b", branch, startPoint}, nil
}

func (s *Service) findBestStartPoint(repoPath string) string {
	// Try remote HEAD.
	for _, remote := range []string{"origin", "upstream"} {
		out, err := gitOutput(repoPath, "symbolic-ref", fmt.Sprintf("refs/remotes/%s/HEAD", remote))
		if err == nil {
			ref := strings.TrimSpace(out)
			// refs/remotes/origin/main -> origin/main
			parts := strings.SplitN(ref, "/", 4)
			if len(parts) == 4 {
				return parts[2] + "/" + parts[3]
			}
		}
	}

	// Try common branch names.
	for _, name := range []string{"main", "master"} {
		if s.BranchExistsLocally(repoPath, name) {
			return name
		}
	}

	// Fall back to HEAD.
	return "HEAD"
}

func (s *Service) getDefaultBranch(repoPath string) string {
	for _, remote := range []string{"origin", "upstream"} {
		out, err := gitOutput(repoPath, "symbolic-ref", fmt.Sprintf("refs/remotes/%s/HEAD", remote))
		if err == nil {
			ref := strings.TrimSpace(out)
			parts := strings.SplitN(ref, "/", 4)
			if len(parts) == 4 {
				return parts[3]
			}
		}
	}
	for _, name := range []string{"main", "master"} {
		if s.BranchExistsLocally(repoPath, name) {
			return name
		}
	}
	branch, _ := s.GetCurrentBranch(repoPath)
	return branch
}

func (s *Service) branchHasRemote(repoPath, branch string) bool {
	out, err := gitOutput(repoPath, "config", fmt.Sprintf("branch.%s.remote", branch))
	return err == nil && strings.TrimSpace(out) != ""
}

func (s *Service) branchIsMerged(repoPath, branch, defaultBranch string) bool {
	return gitRun(repoPath, "merge-base", "--is-ancestor", branch, defaultBranch) == nil
}

func (s *Service) branchesAreIdentical(repoPath, branch, defaultBranch string) bool {
	outA, errA := gitOutput(repoPath, "rev-parse", branch)
	outB, errB := gitOutput(repoPath, "rev-parse", defaultBranch)
	if errA != nil || errB != nil {
		return false
	}
	return strings.TrimSpace(outA) == strings.TrimSpace(outB)
}

// gitOutput runs a git command and returns stdout.
func gitOutput(repoPath string, args ...string) (string, error) {
	fullArgs := append([]string{"-C", repoPath}, args...)
	cmd := exec.Command("git", fullArgs...)
	out, err := cmd.Output()
	if err != nil {
		slog.Debug("git command failed", "args", args, "error", err)
		return "", err
	}
	return string(out), nil
}

// gitRun runs a git command and returns the error (nil on success).
func gitRun(repoPath string, args ...string) error {
	fullArgs := append([]string{"-C", repoPath}, args...)
	cmd := exec.Command("git", fullArgs...)
	return cmd.Run()
}
