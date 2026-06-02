package cli

import (
	"path/filepath"
	"testing"

	"github.com/irskep/autowt/internal/config"
)

func TestGenerateWorktreePathDefaultFlattensBranchSlashes(t *testing.T) {
	repoPath := filepath.Join(t.TempDir(), "repo")
	cfg := config.DefaultConfig()

	got, err := generateWorktreePath(repoPath, "feature/my-branch", "", cfg, nil)
	if err != nil {
		t.Fatalf("generateWorktreePath() error: %v", err)
	}

	want := filepath.Clean(filepath.Join(repoPath, "..", "repo-worktrees", "feature-my-branch"))
	if got != want {
		t.Errorf("generateWorktreePath() = %q, want %q", got, want)
	}
}

func TestGenerateWorktreePathPreservesBranchSlashesWhenFlattenWorktreeDirectoriesIsFalse(t *testing.T) {
	repoPath := filepath.Join(t.TempDir(), "repo")
	cfg := config.DefaultConfig()
	cfg.Worktree.FlattenWorktreeDirectories = false

	got, err := generateWorktreePath(repoPath, "feature/my-branch", "", cfg, nil)
	if err != nil {
		t.Fatalf("generateWorktreePath() error: %v", err)
	}

	want := filepath.Clean(filepath.Join(repoPath, "..", "repo-worktrees", "feature", "my-branch"))
	if got != want {
		t.Errorf("generateWorktreePath() = %q, want %q", got, want)
	}
}

func TestGenerateWorktreePathCustomDirBypassesFlattenWorktreeDirectories(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.Worktree.FlattenWorktreeDirectories = false
	customDir := filepath.Join(t.TempDir(), "literal-feature-my-branch")

	got, err := generateWorktreePath("/repo", "feature/my-branch", customDir, cfg, nil)
	if err != nil {
		t.Fatalf("generateWorktreePath() error: %v", err)
	}
	if got != customDir {
		t.Errorf("generateWorktreePath() = %q, want custom dir %q", got, customDir)
	}
}
