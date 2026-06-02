package ui

import (
	"strings"
	"testing"

	"github.com/irskep/autowt/internal/model"
)

func TestSwitchItemsForWorktreesOnlyIncludesWorktrees(t *testing.T) {
	worktrees := []model.WorktreeInfo{
		{Branch: "main", Path: "/repo"},
		{Branch: "feature/example", Path: "/repo-feature-example"},
	}

	items := switchItemsForWorktrees(worktrees)

	if len(items) != len(worktrees) {
		t.Fatalf("got %d items, want %d", len(items), len(worktrees))
	}
	for i, item := range items {
		if !item.isWorktree {
			t.Fatalf("item %d is not marked as a worktree", i)
		}
		if item.label != worktrees[i].Branch {
			t.Fatalf("item %d label = %q, want %q", i, item.label, worktrees[i].Branch)
		}
	}
}

func TestSwitchViewDoesNotAdvertiseNewWorktrees(t *testing.T) {
	m := switchModel{
		items: switchItemsForWorktrees([]model.WorktreeInfo{
			{Branch: "feature/example", Path: "/repo-feature-example"},
		}),
	}

	view := m.View()

	if strings.Contains(view, "(new worktree)") {
		t.Fatalf("view contains new-worktree marker: %q", view)
	}
	if strings.Contains(view, "branch") {
		t.Fatalf("view still advertises branch selection: %q", view)
	}
}
