package git

import (
	"testing"

	"github.com/irskep/autowt/internal/model"
)

func TestParseWorktreeList(t *testing.T) {
	porcelain := `worktree /home/user/repo
HEAD abc1234
branch refs/heads/main
bare

worktree /home/user/repo-worktrees/feature-x
HEAD def5678
branch refs/heads/feature/x

worktree /home/user/repo-worktrees/detached
HEAD 9999999
detached

`

	wts := parseWorktreeList(porcelain)

	if len(wts) != 3 {
		t.Fatalf("expected 3 worktrees, got %d", len(wts))
	}

	// First entry is primary.
	if !wts[0].IsPrimary {
		t.Error("first worktree should be primary")
	}
	if wts[0].Path != "/home/user/repo" {
		t.Errorf("wts[0].Path = %q, want /home/user/repo", wts[0].Path)
	}
	if wts[0].Branch != "main" {
		t.Errorf("wts[0].Branch = %q, want main", wts[0].Branch)
	}

	// Second entry.
	if wts[1].IsPrimary {
		t.Error("second worktree should not be primary")
	}
	if wts[1].Branch != "feature/x" {
		t.Errorf("wts[1].Branch = %q, want feature/x", wts[1].Branch)
	}

	// Detached HEAD entry has empty branch.
	if wts[2].Branch != "" {
		t.Errorf("wts[2].Branch = %q, want empty", wts[2].Branch)
	}
}

func TestParseWorktreeListEmpty(t *testing.T) {
	wts := parseWorktreeList("")
	if len(wts) != 0 {
		t.Fatalf("expected 0 worktrees, got %d", len(wts))
	}
}

func TestGetCurrentWorktreeRequiresPathBoundary(t *testing.T) {
	svc := NewService()
	worktrees := []model.WorktreeInfo{
		{Branch: "main", Path: "/home/user/repo"},
		{Branch: "feature", Path: "/home/user/repo-worktrees/feature"},
	}

	if got := svc.GetCurrentWorktree("/home/user/repo-extra", worktrees); got != nil {
		t.Fatalf("GetCurrentWorktree matched %q, want nil", got.Path)
	}

	got := svc.GetCurrentWorktree("/home/user/repo/subdir", worktrees)
	if got == nil || got.Branch != "main" {
		t.Fatalf("GetCurrentWorktree nested = %+v, want main", got)
	}
}
